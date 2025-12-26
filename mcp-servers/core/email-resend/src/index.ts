import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Resend } from "resend";

class EmailResendMCP {
  private server: Server;
  private resend: Resend | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "email-resend-mcp",
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

  private getResendClient(): Resend {
    if (!this.resend) {
      const apiKey = process.env.RESEND_API_KEY;
      if (!apiKey) {
        throw new Error("RESEND_API_KEY environment variable not set");
      }
      this.resend = new Resend(apiKey);
    }
    return this.resend;
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "send_email",
            description: "Send an email via Resend API",
            inputSchema: {
              type: "object",
              properties: {
                to: {
                  oneOf: [
                    { type: "string" },
                    { type: "array", items: { type: "string" } },
                  ],
                  description: "Recipient email address(es)",
                },
                from: {
                  type: "string",
                  description: "Sender email address (must be verified domain)",
                },
                subject: { type: "string", description: "Email subject" },
                html: { type: "string", description: "HTML content" },
                text: { type: "string", description: "Plain text content" },
                cc: {
                  oneOf: [
                    { type: "string" },
                    { type: "array", items: { type: "string" } },
                  ],
                  description: "CC recipients",
                },
                bcc: {
                  oneOf: [
                    { type: "string" },
                    { type: "array", items: { type: "string" } },
                  ],
                  description: "BCC recipients",
                },
                reply_to: { type: "string", description: "Reply-to address" },
                tags: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      name: { type: "string" },
                      value: { type: "string" },
                    },
                  },
                  description: "Email tags for tracking",
                },
              },
              required: ["to", "from", "subject"],
            },
          },
          {
            name: "send_batch",
            description: "Send multiple emails in a batch",
            inputSchema: {
              type: "object",
              properties: {
                emails: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      to: { type: "string" },
                      from: { type: "string" },
                      subject: { type: "string" },
                      html: { type: "string" },
                      text: { type: "string" },
                    },
                    required: ["to", "from", "subject"],
                  },
                  description: "Array of emails to send",
                },
              },
              required: ["emails"],
            },
          },
          {
            name: "get_email",
            description: "Get details of a sent email",
            inputSchema: {
              type: "object",
              properties: {
                email_id: { type: "string", description: "Email ID" },
              },
              required: ["email_id"],
            },
          },
          {
            name: "list_domains",
            description: "List verified domains",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      const resend = this.getResendClient();

      switch (name) {
        case "send_email": {
          const result = await resend.emails.send({
            to: args.to as string | string[],
            from: args.from as string,
            subject: args.subject as string,
            html: args.html as string | undefined,
            text: args.text as string | undefined,
            cc: args.cc as string | string[] | undefined,
            bcc: args.bcc as string | string[] | undefined,
            replyTo: args.reply_to as string | undefined,
            tags: args.tags as Array<{ name: string; value: string }> | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  id: result.data?.id,
                  message: "Email sent successfully",
                }),
              },
            ],
          };
        }

        case "send_batch": {
          const emails = args.emails as Array<{
            to: string;
            from: string;
            subject: string;
            html?: string;
            text?: string;
          }>;

          const result = await resend.batch.send(emails);

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  data: result.data,
                  message: `Batch of ${emails.length} emails sent`,
                }),
              },
            ],
          };
        }

        case "get_email": {
          const result = await resend.emails.get(args.email_id as string);

          return {
            content: [{ type: "text", text: JSON.stringify(result.data) }],
          };
        }

        case "list_domains": {
          const result = await resend.domains.list();

          return {
            content: [{ type: "text", text: JSON.stringify(result.data) }],
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
    console.error("Email Resend MCP server running");
  }
}

const server = new EmailResendMCP();
server.run().catch(console.error);
