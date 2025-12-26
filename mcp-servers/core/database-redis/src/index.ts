import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import Redis from "ioredis";

class RedisMCP {
  private server: Server;
  private redis: Redis | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "database-redis-mcp",
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

  private getRedis(): Redis {
    if (!this.redis) {
      this.redis = new Redis({
        host: process.env.REDIS_HOST || "redis",
        port: parseInt(process.env.REDIS_PORT || "6379"),
        password: process.env.REDIS_PASSWORD || undefined,
        db: parseInt(process.env.REDIS_DB || "0"),
      });
    }
    return this.redis;
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "get",
            description: "Get value by key",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Key to retrieve" },
              },
              required: ["key"],
            },
          },
          {
            name: "set",
            description: "Set a key-value pair",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Key" },
                value: { type: "string", description: "Value" },
                ttl: { type: "number", description: "TTL in seconds" },
              },
              required: ["key", "value"],
            },
          },
          {
            name: "delete",
            description: "Delete one or more keys",
            inputSchema: {
              type: "object",
              properties: {
                keys: {
                  type: "array",
                  items: { type: "string" },
                  description: "Keys to delete",
                },
              },
              required: ["keys"],
            },
          },
          {
            name: "exists",
            description: "Check if keys exist",
            inputSchema: {
              type: "object",
              properties: {
                keys: {
                  type: "array",
                  items: { type: "string" },
                  description: "Keys to check",
                },
              },
              required: ["keys"],
            },
          },
          {
            name: "keys",
            description: "Find keys matching a pattern",
            inputSchema: {
              type: "object",
              properties: {
                pattern: {
                  type: "string",
                  description: "Pattern (e.g., user:*)",
                },
              },
              required: ["pattern"],
            },
          },
          {
            name: "hget",
            description: "Get hash field value",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Hash key" },
                field: { type: "string", description: "Field name" },
              },
              required: ["key", "field"],
            },
          },
          {
            name: "hset",
            description: "Set hash field(s)",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Hash key" },
                fields: {
                  type: "object",
                  additionalProperties: { type: "string" },
                  description: "Field-value pairs",
                },
              },
              required: ["key", "fields"],
            },
          },
          {
            name: "hgetall",
            description: "Get all hash fields and values",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Hash key" },
              },
              required: ["key"],
            },
          },
          {
            name: "lpush",
            description: "Push to list (left)",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "List key" },
                values: {
                  type: "array",
                  items: { type: "string" },
                  description: "Values to push",
                },
              },
              required: ["key", "values"],
            },
          },
          {
            name: "lrange",
            description: "Get list range",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "List key" },
                start: { type: "number", description: "Start index" },
                stop: { type: "number", description: "Stop index" },
              },
              required: ["key", "start", "stop"],
            },
          },
          {
            name: "publish",
            description: "Publish message to channel",
            inputSchema: {
              type: "object",
              properties: {
                channel: { type: "string", description: "Channel name" },
                message: { type: "string", description: "Message to publish" },
              },
              required: ["channel", "message"],
            },
          },
          {
            name: "incr",
            description: "Increment a counter",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Counter key" },
                amount: { type: "number", description: "Increment amount" },
              },
              required: ["key"],
            },
          },
          {
            name: "expire",
            description: "Set key expiration",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Key" },
                seconds: { type: "number", description: "TTL in seconds" },
              },
              required: ["key", "seconds"],
            },
          },
          {
            name: "info",
            description: "Get Redis server info",
            inputSchema: {
              type: "object",
              properties: {
                section: {
                  type: "string",
                  description: "Info section (server, clients, memory, etc.)",
                },
              },
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      const redis = this.getRedis();

      switch (name) {
        case "get": {
          const value = await redis.get(args.key as string);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ key: args.key, value }),
              },
            ],
          };
        }

        case "set": {
          if (args.ttl) {
            await redis.setex(args.key as string, args.ttl as number, args.value as string);
          } else {
            await redis.set(args.key as string, args.value as string);
          }
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: true, key: args.key }),
              },
            ],
          };
        }

        case "delete": {
          const count = await redis.del(...(args.keys as string[]));
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: true, deleted: count }),
              },
            ],
          };
        }

        case "exists": {
          const count = await redis.exists(...(args.keys as string[]));
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ exists: count > 0, count }),
              },
            ],
          };
        }

        case "keys": {
          const keys = await redis.keys(args.pattern as string);
          return {
            content: [{ type: "text", text: JSON.stringify({ keys }) }],
          };
        }

        case "hget": {
          const value = await redis.hget(args.key as string, args.field as string);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ key: args.key, field: args.field, value }),
              },
            ],
          };
        }

        case "hset": {
          const fields = args.fields as Record<string, string>;
          await redis.hset(args.key as string, fields);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  key: args.key,
                  fields: Object.keys(fields).length,
                }),
              },
            ],
          };
        }

        case "hgetall": {
          const value = await redis.hgetall(args.key as string);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ key: args.key, value }),
              },
            ],
          };
        }

        case "lpush": {
          const length = await redis.lpush(args.key as string, ...(args.values as string[]));
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: true, key: args.key, length }),
              },
            ],
          };
        }

        case "lrange": {
          const values = await redis.lrange(
            args.key as string,
            args.start as number,
            args.stop as number
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ key: args.key, values }),
              },
            ],
          };
        }

        case "publish": {
          const receivers = await redis.publish(args.channel as string, args.message as string);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  channel: args.channel,
                  receivers,
                }),
              },
            ],
          };
        }

        case "incr": {
          const amount = (args.amount as number) || 1;
          const value =
            amount === 1
              ? await redis.incr(args.key as string)
              : await redis.incrby(args.key as string, amount);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ key: args.key, value }),
              },
            ],
          };
        }

        case "expire": {
          const result = await redis.expire(args.key as string, args.seconds as number);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: result === 1, key: args.key }),
              },
            ],
          };
        }

        case "info": {
          const info = args.section
            ? await redis.info(args.section as string)
            : await redis.info();
          return {
            content: [{ type: "text", text: info }],
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
    console.error("Redis MCP server running");
  }
}

const server = new RedisMCP();
server.run().catch(console.error);
