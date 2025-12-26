import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import Database from "better-sqlite3";
import { ChromaClient, Collection } from "chromadb";

interface MemoryEntry {
  id: string;
  type: string;
  content: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

class MemoryMCP {
  private server: Server;
  private db: Database.Database | null = null;
  private chromaClient: ChromaClient | null = null;
  private collection: Collection | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "memory-mcp",
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

  private async initializeConnections() {
    // SQLite connection
    const dbPath = process.env.SQLITE_PATH || "/data/clopus.db";
    this.db = new Database(dbPath);

    // ChromaDB connection
    const chromaHost = process.env.CHROMADB_HOST || "chromadb";
    const chromaPort = process.env.CHROMADB_PORT || "8000";
    this.chromaClient = new ChromaClient({
      path: `http://${chromaHost}:${chromaPort}`,
    });

    this.collection = await this.chromaClient.getOrCreateCollection({
      name: "clopus_memory",
    });
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "memory_store",
            description: "Store information in long-term memory with semantic indexing",
            inputSchema: {
              type: "object",
              properties: {
                type: {
                  type: "string",
                  description: "Type of memory (learning, pattern, solution, error, context)",
                  enum: ["learning", "pattern", "solution", "error", "context"],
                },
                content: { type: "string", description: "Content to store" },
                metadata: {
                  type: "object",
                  description: "Additional metadata",
                  additionalProperties: true,
                },
              },
              required: ["type", "content"],
            },
          },
          {
            name: "memory_retrieve",
            description: "Retrieve a specific memory by ID",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string", description: "Memory ID" },
              },
              required: ["id"],
            },
          },
          {
            name: "memory_search",
            description: "Search memories semantically by content similarity",
            inputSchema: {
              type: "object",
              properties: {
                query: { type: "string", description: "Search query" },
                type: {
                  type: "string",
                  description: "Filter by memory type",
                  enum: ["learning", "pattern", "solution", "error", "context"],
                },
                limit: {
                  type: "number",
                  description: "Maximum results to return",
                  default: 10,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "memory_forget",
            description: "Remove a memory from the system",
            inputSchema: {
              type: "object",
              properties: {
                id: { type: "string", description: "Memory ID to forget" },
              },
              required: ["id"],
            },
          },
          {
            name: "memory_list_recent",
            description: "List recent memories",
            inputSchema: {
              type: "object",
              properties: {
                type: {
                  type: "string",
                  description: "Filter by memory type",
                },
                limit: {
                  type: "number",
                  description: "Maximum results",
                  default: 20,
                },
              },
            },
          },
          {
            name: "state_get",
            description: "Get current session state from short-term memory",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "State key" },
              },
              required: ["key"],
            },
          },
          {
            name: "state_set",
            description: "Set session state in short-term memory",
            inputSchema: {
              type: "object",
              properties: {
                key: { type: "string", description: "State key" },
                value: { type: "string", description: "State value (JSON)" },
              },
              required: ["key", "value"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      await this.initializeConnections();

      switch (name) {
        case "memory_store": {
          const id = `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          const entry: MemoryEntry = {
            id,
            type: args.type as string,
            content: args.content as string,
            metadata: (args.metadata as Record<string, unknown>) || {},
            timestamp: new Date().toISOString(),
          };

          // Store in ChromaDB with embedding
          await this.collection!.add({
            ids: [id],
            documents: [entry.content],
            metadatas: [
              {
                type: entry.type,
                timestamp: entry.timestamp,
                ...entry.metadata,
              },
            ],
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: true, id, message: "Memory stored" }),
              },
            ],
          };
        }

        case "memory_retrieve": {
          const result = await this.collection!.get({
            ids: [args.id as string],
          });

          if (result.ids.length === 0) {
            return {
              content: [
                { type: "text", text: JSON.stringify({ error: "Memory not found" }) },
              ],
            };
          }

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  id: result.ids[0],
                  content: result.documents?.[0],
                  metadata: result.metadatas?.[0],
                }),
              },
            ],
          };
        }

        case "memory_search": {
          const whereFilter = args.type ? { type: args.type as string } : undefined;

          const results = await this.collection!.query({
            queryTexts: [args.query as string],
            nResults: (args.limit as number) || 10,
            where: whereFilter,
          });

          const memories = results.ids[0].map((id, i) => ({
            id,
            content: results.documents?.[0]?.[i],
            metadata: results.metadatas?.[0]?.[i],
            distance: results.distances?.[0]?.[i],
          }));

          return {
            content: [{ type: "text", text: JSON.stringify({ results: memories }) }],
          };
        }

        case "memory_forget": {
          await this.collection!.delete({
            ids: [args.id as string],
          });

          return {
            content: [
              { type: "text", text: JSON.stringify({ success: true, message: "Memory forgotten" }) },
            ],
          };
        }

        case "memory_list_recent": {
          const whereFilter = args.type ? { type: args.type as string } : undefined;

          const results = await this.collection!.get({
            where: whereFilter,
            limit: (args.limit as number) || 20,
          });

          const memories = results.ids.map((id, i) => ({
            id,
            content: results.documents?.[i],
            metadata: results.metadatas?.[i],
          }));

          return {
            content: [{ type: "text", text: JSON.stringify({ results: memories }) }],
          };
        }

        case "state_get": {
          const stmt = this.db!.prepare(
            "SELECT value FROM session_state WHERE key = ?"
          );
          const row = stmt.get(args.key as string) as { value: string } | undefined;

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  key: args.key,
                  value: row ? JSON.parse(row.value) : null,
                }),
              },
            ],
          };
        }

        case "state_set": {
          const stmt = this.db!.prepare(`
            INSERT INTO session_state (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = datetime('now')
          `);
          stmt.run(args.key, args.value, args.value);

          return {
            content: [
              { type: "text", text: JSON.stringify({ success: true, key: args.key }) },
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
    console.error("Memory MCP server running");
  }
}

const server = new MemoryMCP();
server.run().catch(console.error);
