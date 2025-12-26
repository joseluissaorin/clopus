import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { chromium, Browser, Page } from "playwright";

class BrowserMCP {
  private server: Server;
  private browser: Browser | null = null;
  private page: Page | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "browser-mcp",
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

  private setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "browser_navigate",
            description: "Navigate to a URL",
            inputSchema: {
              type: "object",
              properties: {
                url: { type: "string", description: "URL to navigate to" },
              },
              required: ["url"],
            },
          },
          {
            name: "browser_screenshot",
            description: "Take a screenshot of the current page",
            inputSchema: {
              type: "object",
              properties: {
                path: { type: "string", description: "Path to save screenshot" },
                fullPage: { type: "boolean", description: "Capture full page" },
              },
              required: ["path"],
            },
          },
          {
            name: "browser_click",
            description: "Click an element",
            inputSchema: {
              type: "object",
              properties: {
                selector: { type: "string", description: "CSS selector" },
              },
              required: ["selector"],
            },
          },
          {
            name: "browser_fill",
            description: "Fill a form field",
            inputSchema: {
              type: "object",
              properties: {
                selector: { type: "string", description: "CSS selector" },
                value: { type: "string", description: "Value to fill" },
              },
              required: ["selector", "value"],
            },
          },
          {
            name: "browser_get_text",
            description: "Get text content of an element",
            inputSchema: {
              type: "object",
              properties: {
                selector: { type: "string", description: "CSS selector" },
              },
              required: ["selector"],
            },
          },
          {
            name: "browser_get_html",
            description: "Get HTML content of the page",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "browser_close",
            description: "Close the browser",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      await this.ensureBrowser();

      switch (name) {
        case "browser_navigate": {
          await this.page!.goto(args.url as string);
          return {
            content: [{ type: "text", text: `Navigated to ${args.url}` }],
          };
        }

        case "browser_screenshot": {
          await this.page!.screenshot({
            path: args.path as string,
            fullPage: (args.fullPage as boolean) || false,
          });
          return {
            content: [{ type: "text", text: `Screenshot saved to ${args.path}` }],
          };
        }

        case "browser_click": {
          await this.page!.click(args.selector as string);
          return {
            content: [{ type: "text", text: `Clicked ${args.selector}` }],
          };
        }

        case "browser_fill": {
          await this.page!.fill(args.selector as string, args.value as string);
          return {
            content: [{ type: "text", text: `Filled ${args.selector}` }],
          };
        }

        case "browser_get_text": {
          const text = await this.page!.textContent(args.selector as string);
          return {
            content: [{ type: "text", text: text || "" }],
          };
        }

        case "browser_get_html": {
          const html = await this.page!.content();
          return {
            content: [{ type: "text", text: html }],
          };
        }

        case "browser_close": {
          await this.closeBrowser();
          return {
            content: [{ type: "text", text: "Browser closed" }],
          };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  private async ensureBrowser() {
    if (!this.browser) {
      this.browser = await chromium.launch({
        headless: true,
      });
      this.page = await this.browser.newPage();
    }
  }

  private async closeBrowser() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.page = null;
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Browser MCP server running");
  }
}

const server = new BrowserMCP();
server.run().catch(console.error);
