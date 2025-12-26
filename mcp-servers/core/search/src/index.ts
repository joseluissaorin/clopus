import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as cheerio from "cheerio";

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

class SearchMCP {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: "search-mcp",
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

  private async fetchWithTimeout(
    url: string,
    options: RequestInit = {},
    timeout = 30000
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async searchDuckDuckGo(query: string, maxResults = 10): Promise<SearchResult[]> {
    // DuckDuckGo HTML search (no API key required)
    const encodedQuery = encodeURIComponent(query);
    const url = `https://html.duckduckgo.com/html/?q=${encodedQuery}`;

    const response = await this.fetchWithTimeout(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      },
    });

    const html = await response.text();
    const $ = cheerio.load(html);

    const results: SearchResult[] = [];

    $(".result").each((i, elem) => {
      if (i >= maxResults) return false;

      const titleElem = $(elem).find(".result__a");
      const snippetElem = $(elem).find(".result__snippet");
      const urlElem = $(elem).find(".result__url");

      const title = titleElem.text().trim();
      const snippet = snippetElem.text().trim();
      let resultUrl = titleElem.attr("href") || "";

      // DuckDuckGo wraps URLs, extract actual URL
      if (resultUrl.includes("uddg=")) {
        const match = resultUrl.match(/uddg=([^&]+)/);
        if (match) {
          resultUrl = decodeURIComponent(match[1]);
        }
      }

      if (title && resultUrl) {
        results.push({ title, url: resultUrl, snippet });
      }
    });

    return results;
  }

  private async searchBrave(query: string, maxResults = 10): Promise<SearchResult[]> {
    const apiKey = process.env.BRAVE_SEARCH_API_KEY;
    if (!apiKey) {
      throw new Error("BRAVE_SEARCH_API_KEY not set, falling back to DuckDuckGo");
    }

    const encodedQuery = encodeURIComponent(query);
    const url = `https://api.search.brave.com/res/v1/web/search?q=${encodedQuery}&count=${maxResults}`;

    const response = await this.fetchWithTimeout(url, {
      headers: {
        Accept: "application/json",
        "X-Subscription-Token": apiKey,
      },
    });

    const data = await response.json();

    return (
      data.web?.results?.map((r: { title: string; url: string; description: string }) => ({
        title: r.title,
        url: r.url,
        snippet: r.description,
      })) || []
    );
  }

  private async fetchPage(url: string): Promise<{ title: string; content: string; links: string[] }> {
    const response = await this.fetchWithTimeout(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      },
    });

    const html = await response.text();
    const $ = cheerio.load(html);

    // Remove script and style elements
    $("script, style, nav, footer, header, aside").remove();

    const title = $("title").text().trim() || $("h1").first().text().trim();

    // Get main content
    const content =
      $("main, article, .content, #content, .post, .entry")
        .first()
        .text()
        .trim() || $("body").text().trim();

    // Clean up whitespace
    const cleanContent = content.replace(/\s+/g, " ").substring(0, 10000);

    // Extract links
    const links: string[] = [];
    $("a[href]").each((_, elem) => {
      const href = $(elem).attr("href");
      if (href && href.startsWith("http")) {
        links.push(href);
      }
    });

    return {
      title,
      content: cleanContent,
      links: links.slice(0, 20),
    };
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "search",
            description: "Search the web for information",
            inputSchema: {
              type: "object",
              properties: {
                query: { type: "string", description: "Search query" },
                max_results: {
                  type: "number",
                  description: "Maximum results (default: 10)",
                },
                engine: {
                  type: "string",
                  enum: ["duckduckgo", "brave"],
                  description: "Search engine to use",
                },
              },
              required: ["query"],
            },
          },
          {
            name: "fetch_page",
            description: "Fetch and extract content from a web page",
            inputSchema: {
              type: "object",
              properties: {
                url: { type: "string", description: "URL to fetch" },
                extract_links: {
                  type: "boolean",
                  description: "Include extracted links",
                },
              },
              required: ["url"],
            },
          },
          {
            name: "search_and_summarize",
            description: "Search and return summarized content from top results",
            inputSchema: {
              type: "object",
              properties: {
                query: { type: "string", description: "Search query" },
                num_pages: {
                  type: "number",
                  description: "Number of pages to fetch (default: 3)",
                },
              },
              required: ["query"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "search": {
          const query = args.query as string;
          const maxResults = (args.max_results as number) || 10;
          const engine = (args.engine as string) || "duckduckgo";

          let results: SearchResult[];

          try {
            if (engine === "brave") {
              results = await this.searchBrave(query, maxResults);
            } else {
              results = await this.searchDuckDuckGo(query, maxResults);
            }
          } catch (error) {
            // Fallback to DuckDuckGo if Brave fails
            if (engine === "brave") {
              results = await this.searchDuckDuckGo(query, maxResults);
            } else {
              throw error;
            }
          }

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  query,
                  engine,
                  results,
                  count: results.length,
                }),
              },
            ],
          };
        }

        case "fetch_page": {
          const url = args.url as string;
          const extractLinks = args.extract_links !== false;

          const pageData = await this.fetchPage(url);

          const result: {
            url: string;
            title: string;
            content: string;
            links?: string[];
          } = {
            url,
            title: pageData.title,
            content: pageData.content,
          };

          if (extractLinks) {
            result.links = pageData.links;
          }

          return {
            content: [{ type: "text", text: JSON.stringify(result) }],
          };
        }

        case "search_and_summarize": {
          const query = args.query as string;
          const numPages = (args.num_pages as number) || 3;

          // Search first
          const searchResults = await this.searchDuckDuckGo(query, numPages);

          // Fetch top pages
          const pageContents = await Promise.all(
            searchResults.slice(0, numPages).map(async (result) => {
              try {
                const page = await this.fetchPage(result.url);
                return {
                  url: result.url,
                  title: page.title,
                  content: page.content.substring(0, 2000),
                };
              } catch {
                return {
                  url: result.url,
                  title: result.title,
                  content: result.snippet,
                };
              }
            })
          );

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  query,
                  sources: pageContents,
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
    console.error("Search MCP server running");
  }
}

const server = new SearchMCP();
server.run().catch(console.error);
