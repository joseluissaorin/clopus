import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Pool, PoolClient, QueryResult } from "pg";

class PostgresMCP {
  private server: Server;
  private pool: Pool | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "database-postgres-mcp",
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

  private getPool(): Pool {
    if (!this.pool) {
      this.pool = new Pool({
        host: process.env.POSTGRES_HOST || "postgres",
        port: parseInt(process.env.POSTGRES_PORT || "5432"),
        database: process.env.POSTGRES_DB || "clopus",
        user: process.env.POSTGRES_USER || "clopus",
        password: process.env.POSTGRES_PASSWORD || "clopus",
        max: 20,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 2000,
      });
    }
    return this.pool;
  }

  private formatResults(result: QueryResult): object {
    return {
      rows: result.rows,
      rowCount: result.rowCount,
      fields: result.fields.map((f) => ({
        name: f.name,
        dataTypeID: f.dataTypeID,
      })),
    };
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "query",
            description: "Execute a SELECT query and return results",
            inputSchema: {
              type: "object",
              properties: {
                sql: { type: "string", description: "SQL SELECT query" },
                params: {
                  type: "array",
                  items: {},
                  description: "Query parameters for prepared statement",
                },
              },
              required: ["sql"],
            },
          },
          {
            name: "execute",
            description: "Execute an INSERT, UPDATE, or DELETE query",
            inputSchema: {
              type: "object",
              properties: {
                sql: { type: "string", description: "SQL query" },
                params: {
                  type: "array",
                  items: {},
                  description: "Query parameters",
                },
              },
              required: ["sql"],
            },
          },
          {
            name: "transaction",
            description: "Execute multiple queries in a transaction",
            inputSchema: {
              type: "object",
              properties: {
                queries: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      sql: { type: "string" },
                      params: { type: "array", items: {} },
                    },
                    required: ["sql"],
                  },
                  description: "Array of queries to execute",
                },
              },
              required: ["queries"],
            },
          },
          {
            name: "list_tables",
            description: "List all tables in the database",
            inputSchema: {
              type: "object",
              properties: {
                schema: {
                  type: "string",
                  description: "Schema name (default: public)",
                },
              },
            },
          },
          {
            name: "describe_table",
            description: "Get table schema/columns",
            inputSchema: {
              type: "object",
              properties: {
                table: { type: "string", description: "Table name" },
                schema: { type: "string", description: "Schema name" },
              },
              required: ["table"],
            },
          },
          {
            name: "create_table",
            description: "Create a new table",
            inputSchema: {
              type: "object",
              properties: {
                table: { type: "string", description: "Table name" },
                columns: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      name: { type: "string" },
                      type: { type: "string" },
                      nullable: { type: "boolean" },
                      default: { type: "string" },
                      primary_key: { type: "boolean" },
                    },
                    required: ["name", "type"],
                  },
                  description: "Column definitions",
                },
                if_not_exists: { type: "boolean" },
              },
              required: ["table", "columns"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      const pool = this.getPool();

      switch (name) {
        case "query": {
          const result = await pool.query(
            args.sql as string,
            args.params as unknown[] | undefined
          );
          return {
            content: [
              { type: "text", text: JSON.stringify(this.formatResults(result), null, 2) },
            ],
          };
        }

        case "execute": {
          const result = await pool.query(
            args.sql as string,
            args.params as unknown[] | undefined
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  rowCount: result.rowCount,
                  command: result.command,
                }),
              },
            ],
          };
        }

        case "transaction": {
          const queries = args.queries as Array<{
            sql: string;
            params?: unknown[];
          }>;
          const client: PoolClient = await pool.connect();

          try {
            await client.query("BEGIN");
            const results: object[] = [];

            for (const q of queries) {
              const result = await client.query(q.sql, q.params);
              results.push(this.formatResults(result));
            }

            await client.query("COMMIT");

            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify({
                    success: true,
                    results,
                    message: `Transaction completed with ${queries.length} queries`,
                  }),
                },
              ],
            };
          } catch (error) {
            await client.query("ROLLBACK");
            throw error;
          } finally {
            client.release();
          }
        }

        case "list_tables": {
          const schema = (args.schema as string) || "public";
          const result = await pool.query(
            `SELECT table_name, table_type
             FROM information_schema.tables
             WHERE table_schema = $1
             ORDER BY table_name`,
            [schema]
          );
          return {
            content: [{ type: "text", text: JSON.stringify(result.rows, null, 2) }],
          };
        }

        case "describe_table": {
          const table = args.table as string;
          const schema = (args.schema as string) || "public";

          const result = await pool.query(
            `SELECT
               column_name,
               data_type,
               is_nullable,
               column_default,
               character_maximum_length
             FROM information_schema.columns
             WHERE table_schema = $1 AND table_name = $2
             ORDER BY ordinal_position`,
            [schema, table]
          );

          // Get primary key info
          const pkResult = await pool.query(
            `SELECT a.attname as column_name
             FROM pg_index i
             JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
             WHERE i.indrelid = $1::regclass AND i.indisprimary`,
            [`${schema}.${table}`]
          );

          const pkColumns = new Set(pkResult.rows.map((r) => r.column_name));

          const columns = result.rows.map((row) => ({
            ...row,
            is_primary_key: pkColumns.has(row.column_name),
          }));

          return {
            content: [{ type: "text", text: JSON.stringify(columns, null, 2) }],
          };
        }

        case "create_table": {
          const table = args.table as string;
          const columns = args.columns as Array<{
            name: string;
            type: string;
            nullable?: boolean;
            default?: string;
            primary_key?: boolean;
          }>;
          const ifNotExists = args.if_not_exists ? "IF NOT EXISTS " : "";

          const columnDefs = columns.map((col) => {
            let def = `"${col.name}" ${col.type}`;
            if (col.primary_key) def += " PRIMARY KEY";
            if (col.nullable === false) def += " NOT NULL";
            if (col.default) def += ` DEFAULT ${col.default}`;
            return def;
          });

          const sql = `CREATE TABLE ${ifNotExists}"${table}" (\n  ${columnDefs.join(",\n  ")}\n)`;

          await pool.query(sql);

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  message: `Table "${table}" created`,
                  sql,
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
    console.error("PostgreSQL MCP server running");
  }
}

const server = new PostgresMCP();
server.run().catch(console.error);
