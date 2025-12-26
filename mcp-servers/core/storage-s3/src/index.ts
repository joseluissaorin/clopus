import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
  ListObjectsV2Command,
  HeadObjectCommand,
  CopyObjectCommand,
  CreateBucketCommand,
  ListBucketsCommand,
  DeleteBucketCommand,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import * as fs from "fs/promises";

class StorageS3MCP {
  private server: Server;
  private s3: S3Client | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "storage-s3-mcp",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  private getS3Client(): S3Client {
    if (!this.s3) {
      this.s3 = new S3Client({
        endpoint: process.env.S3_ENDPOINT || "http://minio:9000",
        region: process.env.S3_REGION || "us-east-1",
        credentials: {
          accessKeyId: process.env.S3_ACCESS_KEY || process.env.MINIO_ROOT_USER || "clopus",
          secretAccessKey:
            process.env.S3_SECRET_KEY || process.env.MINIO_ROOT_PASSWORD || "clopuspassword",
        },
        forcePathStyle: true, // Required for MinIO
      });
    }
    return this.s3;
  }

  private async streamToString(stream: NodeJS.ReadableStream): Promise<string> {
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(Buffer.from(chunk));
    }
    return Buffer.concat(chunks).toString("utf-8");
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "upload",
            description: "Upload a file to S3/MinIO",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
                key: { type: "string", description: "Object key (path)" },
                file_path: { type: "string", description: "Local file path to upload" },
                content: { type: "string", description: "Content to upload (alternative to file_path)" },
                content_type: { type: "string", description: "MIME type" },
                metadata: {
                  type: "object",
                  additionalProperties: { type: "string" },
                  description: "Custom metadata",
                },
              },
              required: ["bucket", "key"],
            },
          },
          {
            name: "download",
            description: "Download a file from S3/MinIO",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
                key: { type: "string", description: "Object key" },
                file_path: { type: "string", description: "Local path to save (optional)" },
              },
              required: ["bucket", "key"],
            },
          },
          {
            name: "delete",
            description: "Delete an object from S3/MinIO",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
                key: { type: "string", description: "Object key" },
              },
              required: ["bucket", "key"],
            },
          },
          {
            name: "list",
            description: "List objects in a bucket",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
                prefix: { type: "string", description: "Key prefix filter" },
                max_keys: { type: "number", description: "Maximum objects to return" },
              },
              required: ["bucket"],
            },
          },
          {
            name: "get_info",
            description: "Get object metadata/info",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
                key: { type: "string", description: "Object key" },
              },
              required: ["bucket", "key"],
            },
          },
          {
            name: "copy",
            description: "Copy an object within S3/MinIO",
            inputSchema: {
              type: "object",
              properties: {
                source_bucket: { type: "string", description: "Source bucket" },
                source_key: { type: "string", description: "Source key" },
                dest_bucket: { type: "string", description: "Destination bucket" },
                dest_key: { type: "string", description: "Destination key" },
              },
              required: ["source_bucket", "source_key", "dest_bucket", "dest_key"],
            },
          },
          {
            name: "get_presigned_url",
            description: "Generate a presigned URL for temporary access",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
                key: { type: "string", description: "Object key" },
                operation: {
                  type: "string",
                  enum: ["get", "put"],
                  description: "Operation type",
                },
                expires_in: { type: "number", description: "URL expiration in seconds" },
              },
              required: ["bucket", "key"],
            },
          },
          {
            name: "create_bucket",
            description: "Create a new bucket",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
              },
              required: ["bucket"],
            },
          },
          {
            name: "list_buckets",
            description: "List all buckets",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "delete_bucket",
            description: "Delete an empty bucket",
            inputSchema: {
              type: "object",
              properties: {
                bucket: { type: "string", description: "Bucket name" },
              },
              required: ["bucket"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      const s3 = this.getS3Client();

      switch (name) {
        case "upload": {
          let body: Buffer | string;

          if (args.file_path) {
            body = await fs.readFile(args.file_path as string);
          } else if (args.content) {
            body = args.content as string;
          } else {
            throw new Error("Either file_path or content is required");
          }

          await s3.send(
            new PutObjectCommand({
              Bucket: args.bucket as string,
              Key: args.key as string,
              Body: body,
              ContentType: args.content_type as string | undefined,
              Metadata: args.metadata as Record<string, string> | undefined,
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  bucket: args.bucket,
                  key: args.key,
                  message: "File uploaded",
                }),
              },
            ],
          };
        }

        case "download": {
          const response = await s3.send(
            new GetObjectCommand({
              Bucket: args.bucket as string,
              Key: args.key as string,
            })
          );

          if (args.file_path) {
            const content = await response.Body?.transformToByteArray();
            if (content) {
              await fs.writeFile(args.file_path as string, content);
            }
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify({
                    success: true,
                    saved_to: args.file_path,
                    size: content?.length,
                  }),
                },
              ],
            };
          } else {
            const content = await this.streamToString(response.Body as NodeJS.ReadableStream);
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify({
                    success: true,
                    content,
                    content_type: response.ContentType,
                    size: response.ContentLength,
                  }),
                },
              ],
            };
          }
        }

        case "delete": {
          await s3.send(
            new DeleteObjectCommand({
              Bucket: args.bucket as string,
              Key: args.key as string,
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: "Object deleted",
                }),
              },
            ],
          };
        }

        case "list": {
          const response = await s3.send(
            new ListObjectsV2Command({
              Bucket: args.bucket as string,
              Prefix: args.prefix as string | undefined,
              MaxKeys: args.max_keys as number | undefined,
            })
          );

          const objects =
            response.Contents?.map((obj) => ({
              key: obj.Key,
              size: obj.Size,
              last_modified: obj.LastModified?.toISOString(),
              etag: obj.ETag,
            })) || [];

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  bucket: args.bucket,
                  objects,
                  count: objects.length,
                  is_truncated: response.IsTruncated,
                }),
              },
            ],
          };
        }

        case "get_info": {
          const response = await s3.send(
            new HeadObjectCommand({
              Bucket: args.bucket as string,
              Key: args.key as string,
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  bucket: args.bucket,
                  key: args.key,
                  size: response.ContentLength,
                  content_type: response.ContentType,
                  last_modified: response.LastModified?.toISOString(),
                  etag: response.ETag,
                  metadata: response.Metadata,
                }),
              },
            ],
          };
        }

        case "copy": {
          await s3.send(
            new CopyObjectCommand({
              Bucket: args.dest_bucket as string,
              Key: args.dest_key as string,
              CopySource: `${args.source_bucket}/${args.source_key}`,
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: "Object copied",
                  from: `${args.source_bucket}/${args.source_key}`,
                  to: `${args.dest_bucket}/${args.dest_key}`,
                }),
              },
            ],
          };
        }

        case "get_presigned_url": {
          const operation = (args.operation as string) || "get";
          const expiresIn = (args.expires_in as number) || 3600;

          const command =
            operation === "put"
              ? new PutObjectCommand({
                  Bucket: args.bucket as string,
                  Key: args.key as string,
                })
              : new GetObjectCommand({
                  Bucket: args.bucket as string,
                  Key: args.key as string,
                });

          const url = await getSignedUrl(s3, command, { expiresIn });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  url,
                  expires_in: expiresIn,
                  operation,
                }),
              },
            ],
          };
        }

        case "create_bucket": {
          await s3.send(
            new CreateBucketCommand({
              Bucket: args.bucket as string,
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: `Bucket "${args.bucket}" created`,
                }),
              },
            ],
          };
        }

        case "list_buckets": {
          const response = await s3.send(new ListBucketsCommand({}));

          const buckets =
            response.Buckets?.map((b) => ({
              name: b.Name,
              created: b.CreationDate?.toISOString(),
            })) || [];

          return {
            content: [
              { type: "text", text: JSON.stringify({ buckets }) },
            ],
          };
        }

        case "delete_bucket": {
          await s3.send(
            new DeleteBucketCommand({
              Bucket: args.bucket as string,
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: `Bucket "${args.bucket}" deleted`,
                }),
              },
            ],
          };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Storage S3 MCP server running");
  }
}

const server = new StorageS3MCP();
server.run().catch(console.error);
