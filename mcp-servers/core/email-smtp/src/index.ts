import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import nodemailer, { Transporter } from "nodemailer";

interface SMTPConfig {
  host: string;
  port: number;
  secure: boolean;
  auth: {
    user: string;
    pass: string;
  };
}

class EmailSMTPMCP {
  private server: Server;
  private transporter: Transporter | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "email-smtp-mcp",
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

  private getTransporter(): Transporter {
    if (!this.transporter) {
      const config: SMTPConfig = {
        host: process.env.SMTP_HOST || "localhost",
        port: parseInt(process.env.SMTP_PORT || "587"),
        secure: process.env.SMTP_SECURE === "true",
        auth: {
          user: process.env.SMTP_USER || "",
          pass: process.env.SMTP_PASS || "",
        },
      };

      this.transporter = nodemailer.createTransport(config);
    }
    return this.transporter;
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "send_email",
            description: "Send an email via SMTP",
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
                from: { type: "string", description: "Sender email address" },
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
              },
              required: ["to", "from", "subject"],
            },
          },
          {
            name: "send_with_attachment",
            description: "Send an email with attachments via SMTP",
            inputSchema: {
              type: "object",
              properties: {
                to: { type: "string", description: "Recipient email" },
                from: { type: "string", description: "Sender email" },
                subject: { type: "string", description: "Email subject" },
                html: { type: "string", description: "HTML content" },
                text: { type: "string", description: "Plain text content" },
                attachments: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      filename: { type: "string" },
                      path: { type: "string", description: "File path" },
                      content: { type: "string", description: "Base64 content" },
                      contentType: { type: "string" },
                    },
                    required: ["filename"],
                  },
                  description: "Attachments array",
                },
              },
              required: ["to", "from", "subject", "attachments"],
            },
          },
          {
            name: "verify_connection",
            description: "Verify SMTP connection is working",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "configure_smtp",
            description: "Configure SMTP settings (temporary, for current session)",
            inputSchema: {
              type: "object",
              properties: {
                host: { type: "string", description: "SMTP host" },
                port: { type: "number", description: "SMTP port" },
                secure: { type: "boolean", description: "Use TLS" },
                user: { type: "string", description: "SMTP username" },
                pass: { type: "string", description: "SMTP password" },
              },
              required: ["host", "port", "user", "pass"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "send_email": {
          const transporter = this.getTransporter();

          const result = await transporter.sendMail({
            to: args.to as string | string[],
            from: args.from as string,
            subject: args.subject as string,
            html: args.html as string | undefined,
            text: args.text as string | undefined,
            cc: args.cc as string | string[] | undefined,
            bcc: args.bcc as string | string[] | undefined,
            replyTo: args.reply_to as string | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  messageId: result.messageId,
                  accepted: result.accepted,
                  rejected: result.rejected,
                }),
              },
            ],
          };
        }

        case "send_with_attachment": {
          const transporter = this.getTransporter();

          const attachments = (args.attachments as Array<{
            filename: string;
            path?: string;
            content?: string;
            contentType?: string;
          }>).map((att) => ({
            filename: att.filename,
            path: att.path,
            content: att.content ? Buffer.from(att.content, "base64") : undefined,
            contentType: att.contentType,
          }));

          const result = await transporter.sendMail({
            to: args.to as string,
            from: args.from as string,
            subject: args.subject as string,
            html: args.html as string | undefined,
            text: args.text as string | undefined,
            attachments,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  messageId: result.messageId,
                  accepted: result.accepted,
                }),
              },
            ],
          };
        }

        case "verify_connection": {
          const transporter = this.getTransporter();

          try {
            await transporter.verify();
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify({
                    success: true,
                    message: "SMTP connection verified",
                  }),
                },
              ],
            };
          } catch (error) {
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify({
                    success: false,
                    error: error instanceof Error ? error.message : "Unknown error",
                  }),
                },
              ],
            };
          }
        }

        case "configure_smtp": {
          const config: SMTPConfig = {
            host: args.host as string,
            port: args.port as number,
            secure: (args.secure as boolean) || false,
            auth: {
              user: args.user as string,
              pass: args.pass as string,
            },
          };

          this.transporter = nodemailer.createTransport(config);

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: "SMTP configured",
                  host: config.host,
                  port: config.port,
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
    console.error("Email SMTP MCP server running");
  }
}

const server = new EmailSMTPMCP();
server.run().catch(console.error);
