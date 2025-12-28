/**
 * CLOPUS Collaboration MCP Server
 *
 * Provides inter-worker communication tools for the CLOPUS system.
 * Workers can ask each other for help, request browser automation,
 * share learnings, and spawn subtasks.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";

// Environment configuration
const IPC_PATH = process.env.IPC_PATH || "/app/ipc";
const WORKER_ID = process.env.WORKER_ID || "0";
const WORKER_ROLE = process.env.WORKER_ROLE || "unknown";
const COLLAB_PATH = path.join(IPC_PATH, "collaboration");
const MEMORY_SHARED_PATH = path.join(IPC_PATH, "memory", "shared");

// Valid worker roles for type safety
const WORKER_ROLES = ["coder", "tester", "reviewer", "researcher", "debugger", "designer", "browser-headless", "browser-chrome", "services"] as const;
type WorkerRole = typeof WORKER_ROLES[number];

// Request types
interface CollaborationRequest {
  id: string;
  type: "help_request" | "browser_action" | "e2e_test" | "screenshot";
  from_worker_id: string;
  from_role: string;
  to_role: string;
  question?: string;
  action?: string;
  context?: Record<string, unknown>;
  timeout_seconds: number;
  created_at: string;
}

interface CollaborationResponse {
  request_id: string;
  success: boolean;
  response?: string;
  error?: string;
  from_role?: string;
  from_worker_id?: string;
  screenshots?: string[];
  completed_at: string;
}

interface CollaborationEvent {
  id: string;
  type: "spawn_subtask" | "share_learning" | "report_issue" | "update_context";
  from_worker_id: string;
  from_role: string;
  payload: Record<string, unknown>;
  created_at: string;
}

class CollaborationMCP {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: "collaboration-mcp",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.ensureDirectories();
    this.setupHandlers();
  }

  /**
   * Ensure all IPC directories exist
   */
  private ensureDirectories(): void {
    const dirs = [
      path.join(COLLAB_PATH, "requests"),
      path.join(COLLAB_PATH, "responses"),
      path.join(COLLAB_PATH, "events"),
      path.join(COLLAB_PATH, "screenshots"),
      MEMORY_SHARED_PATH,
    ];

    for (const dir of dirs) {
      try {
        fs.mkdirSync(dir, { recursive: true });
      } catch (err) {
        // Directory might already exist or permission issues
        console.error(`Warning: Could not create directory ${dir}:`, err);
      }
    }
  }

  /**
   * Generate a unique request ID
   */
  private generateId(prefix: string = "req"): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Setup all tool handlers
   */
  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "ask_worker",
            description: "Ask another worker for help and wait for a response. Use this to consult with other specialized workers (e.g., ask designer for colors, ask researcher for API info).",
            inputSchema: {
              type: "object",
              properties: {
                role: {
                  type: "string",
                  enum: WORKER_ROLES,
                  description: "The role of the worker to ask (e.g., 'designer', 'researcher')",
                },
                question: {
                  type: "string",
                  description: "The question or request to send to the worker",
                },
                context: {
                  type: "object",
                  description: "Optional context to include with the request (file paths, code snippets, etc.)",
                  additionalProperties: true,
                },
                timeout_seconds: {
                  type: "number",
                  default: 60,
                  description: "Maximum time to wait for a response (default: 60 seconds)",
                },
              },
              required: ["role", "question"],
            },
          },
          {
            name: "spawn_subtask",
            description: "Create a new task for another worker. Use this when you need another worker to do something but don't need to wait for the result.",
            inputSchema: {
              type: "object",
              properties: {
                role: {
                  type: "string",
                  enum: WORKER_ROLES,
                  description: "The role of the worker to assign the task to",
                },
                title: {
                  type: "string",
                  description: "Short title for the task",
                },
                description: {
                  type: "string",
                  description: "Detailed description of what needs to be done",
                },
                priority: {
                  type: "string",
                  enum: ["low", "normal", "high", "urgent"],
                  default: "normal",
                  description: "Task priority level",
                },
                wait_for_completion: {
                  type: "boolean",
                  default: false,
                  description: "If true, wait for the task to complete before returning",
                },
                timeout_seconds: {
                  type: "number",
                  default: 300,
                  description: "Maximum time to wait if wait_for_completion is true (default: 5 minutes)",
                },
              },
              required: ["role", "title", "description"],
            },
          },
          {
            name: "request_browser_action",
            description: "Request a browser worker to perform any automation task. The browser worker will interpret your natural language request and execute it using Playwright.",
            inputSchema: {
              type: "object",
              properties: {
                action: {
                  type: "string",
                  description: "What you want the browser to do (natural language). Example: 'Test login with user@test.com', 'Navigate to /dashboard and take a screenshot'",
                },
                url: {
                  type: "string",
                  description: "Starting URL (optional if implied by action)",
                },
                test_data: {
                  type: "object",
                  description: "Test data to use (credentials, form values, etc.)",
                  additionalProperties: true,
                },
                capture_screenshots: {
                  type: "boolean",
                  default: true,
                  description: "Capture screenshots during execution",
                },
                timeout_seconds: {
                  type: "number",
                  default: 120,
                  description: "Maximum time for browser action (default: 2 minutes)",
                },
              },
              required: ["action"],
            },
          },
          {
            name: "run_e2e_test",
            description: "Run a complete E2E test scenario with assertions. The browser worker will execute the scenario and verify the assertions.",
            inputSchema: {
              type: "object",
              properties: {
                scenario: {
                  type: "string",
                  description: "Description of the test scenario (e.g., 'User registration flow')",
                },
                steps: {
                  type: "array",
                  items: { type: "string" },
                  description: "Optional explicit steps to follow. If not provided, browser worker will infer from scenario.",
                },
                assertions: {
                  type: "array",
                  items: { type: "string" },
                  description: "What to verify (e.g., 'user is logged in', 'cart shows 3 items')",
                },
                base_url: {
                  type: "string",
                  description: "Base URL for the application (e.g., 'http://localhost:3142')",
                },
                test_data: {
                  type: "object",
                  description: "Test data for the scenario",
                  additionalProperties: true,
                },
                timeout_seconds: {
                  type: "number",
                  default: 180,
                  description: "Maximum time for E2E test (default: 3 minutes)",
                },
              },
              required: ["scenario", "assertions"],
            },
          },
          {
            name: "capture_screenshot",
            description: "Capture a screenshot of a page or element. This is a convenience wrapper for simple screenshot requests.",
            inputSchema: {
              type: "object",
              properties: {
                url: {
                  type: "string",
                  description: "URL to navigate to before capturing",
                },
                selector: {
                  type: "string",
                  description: "CSS selector for element to capture (optional, captures full page if not specified)",
                },
                full_page: {
                  type: "boolean",
                  default: false,
                  description: "Capture full scrollable page",
                },
                wait_for: {
                  type: "string",
                  description: "CSS selector to wait for before capturing",
                },
                timeout_seconds: {
                  type: "number",
                  default: 30,
                  description: "Maximum time to wait (default: 30 seconds)",
                },
              },
              required: ["url"],
            },
          },
          {
            name: "share_learning",
            description: "Share a discovery or pattern with other workers via memory. Use this when you learn something that other workers might benefit from.",
            inputSchema: {
              type: "object",
              properties: {
                type: {
                  type: "string",
                  enum: ["pattern", "solution", "warning", "api_endpoint", "design_token", "best_practice"],
                  description: "Type of learning being shared",
                },
                content: {
                  type: "string",
                  description: "The learning content to share",
                },
                metadata: {
                  type: "object",
                  description: "Additional metadata (project, file, context)",
                  additionalProperties: true,
                },
              },
              required: ["type", "content"],
            },
          },
          {
            name: "find_relevant_context",
            description: "Search memory for context relevant to the current task. Finds patterns, solutions, and learnings from past work.",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Search query describing what you're looking for",
                },
                type: {
                  type: "string",
                  enum: ["pattern", "solution", "warning", "api_endpoint", "design_token", "best_practice"],
                  description: "Filter by learning type",
                },
                limit: {
                  type: "number",
                  default: 5,
                  description: "Maximum number of results to return",
                },
              },
              required: ["query"],
            },
          },
          {
            name: "get_design_system",
            description: "Get the project's design system (colors, typography, spacing, etc.). Use this before implementing any UI.",
            inputSchema: {
              type: "object",
              properties: {
                project_path: {
                  type: "string",
                  description: "Path to the project (defaults to current workspace)",
                },
              },
            },
          },
          {
            name: "report_issue",
            description: "Report a bug or issue for the debugger to investigate. Creates a high-priority task for the debugger worker.",
            inputSchema: {
              type: "object",
              properties: {
                title: {
                  type: "string",
                  description: "Short title for the issue",
                },
                description: {
                  type: "string",
                  description: "Detailed description of the issue",
                },
                file_path: {
                  type: "string",
                  description: "Path to the file where the issue occurs",
                },
                error_message: {
                  type: "string",
                  description: "Error message if applicable",
                },
                stack_trace: {
                  type: "string",
                  description: "Stack trace if available",
                },
                severity: {
                  type: "string",
                  enum: ["low", "medium", "high", "critical"],
                  default: "medium",
                  description: "Issue severity",
                },
              },
              required: ["title", "description"],
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "ask_worker":
            return await this.handleAskWorker(args as Record<string, unknown>);
          case "spawn_subtask":
            return await this.handleSpawnSubtask(args as Record<string, unknown>);
          case "request_browser_action":
            return await this.handleBrowserAction(args as Record<string, unknown>);
          case "run_e2e_test":
            return await this.handleE2ETest(args as Record<string, unknown>);
          case "capture_screenshot":
            return await this.handleScreenshot(args as Record<string, unknown>);
          case "share_learning":
            return await this.handleShareLearning(args as Record<string, unknown>);
          case "find_relevant_context":
            return await this.handleFindContext(args as Record<string, unknown>);
          case "get_design_system":
            return await this.handleGetDesignSystem(args as Record<string, unknown>);
          case "report_issue":
            return await this.handleReportIssue(args as Record<string, unknown>);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ error: true, message: errorMessage }),
            },
          ],
        };
      }
    });
  }

  /**
   * Handle ask_worker - synchronous request to another worker
   */
  private async handleAskWorker(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const requestId = this.generateId("req");
    const timeoutSeconds = (args.timeout_seconds as number) || 60;

    const request: CollaborationRequest = {
      id: requestId,
      type: "help_request",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      to_role: args.role as string,
      question: args.question as string,
      context: (args.context as Record<string, unknown>) || {},
      timeout_seconds: timeoutSeconds,
      created_at: new Date().toISOString(),
    };

    // Write request file
    const requestPath = path.join(COLLAB_PATH, "requests", `${requestId}.json`);
    fs.writeFileSync(requestPath, JSON.stringify(request, null, 2));

    // Poll for response
    const responsePath = path.join(COLLAB_PATH, "responses", `${requestId}.json`);
    const timeoutMs = timeoutSeconds * 1000;
    const startTime = Date.now();
    const pollInterval = 500; // 500ms

    while (Date.now() - startTime < timeoutMs) {
      if (fs.existsSync(responsePath)) {
        try {
          const response = JSON.parse(fs.readFileSync(responsePath, "utf-8")) as CollaborationResponse;

          // Clean up files
          try { fs.unlinkSync(responsePath); } catch {}
          try { fs.unlinkSync(requestPath); } catch {}

          return {
            content: [{ type: "text", text: JSON.stringify(response) }],
          };
        } catch (parseError) {
          // Response file exists but couldn't be parsed - wait and retry
        }
      }
      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    // Timeout - clean up and return error
    try { fs.unlinkSync(requestPath); } catch {}

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            request_id: requestId,
            success: false,
            error: "timeout",
            message: `No response from ${args.role} worker within ${timeoutSeconds} seconds`,
            completed_at: new Date().toISOString(),
          }),
        },
      ],
    };
  }

  /**
   * Handle spawn_subtask - create a task for another worker
   */
  private async handleSpawnSubtask(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const eventId = this.generateId("evt");

    const event: CollaborationEvent = {
      id: eventId,
      type: "spawn_subtask",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      payload: {
        target_role: args.role,
        title: args.title,
        description: args.description,
        priority: args.priority || "normal",
      },
      created_at: new Date().toISOString(),
    };

    // Write event file
    const eventPath = path.join(COLLAB_PATH, "events", `${eventId}.json`);
    fs.writeFileSync(eventPath, JSON.stringify(event, null, 2));

    // If wait_for_completion is true, poll for result
    if (args.wait_for_completion) {
      const timeoutSeconds = (args.timeout_seconds as number) || 300;
      const responsePath = path.join(COLLAB_PATH, "responses", `${eventId}.json`);
      const timeoutMs = timeoutSeconds * 1000;
      const startTime = Date.now();

      while (Date.now() - startTime < timeoutMs) {
        if (fs.existsSync(responsePath)) {
          try {
            const response = JSON.parse(fs.readFileSync(responsePath, "utf-8"));
            try { fs.unlinkSync(responsePath); } catch {}
            return {
              content: [{ type: "text", text: JSON.stringify(response) }],
            };
          } catch {}
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              event_id: eventId,
              success: false,
              error: "timeout",
              message: `Task did not complete within ${timeoutSeconds} seconds`,
            }),
          },
        ],
      };
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: true,
            event_id: eventId,
            message: `Subtask created for ${args.role} worker: ${args.title}`,
          }),
        },
      ],
    };
  }

  /**
   * Handle request_browser_action - full browser automation
   */
  private async handleBrowserAction(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const requestId = this.generateId("browser");
    const timeoutSeconds = (args.timeout_seconds as number) || 120;

    const request: CollaborationRequest = {
      id: requestId,
      type: "browser_action",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      to_role: "browser-headless",
      action: args.action as string,
      context: {
        url: args.url,
        test_data: args.test_data,
        capture_screenshots: args.capture_screenshots !== false,
      },
      timeout_seconds: timeoutSeconds,
      created_at: new Date().toISOString(),
    };

    // Write request file
    const requestPath = path.join(COLLAB_PATH, "requests", `${requestId}.json`);
    fs.writeFileSync(requestPath, JSON.stringify(request, null, 2));

    // Poll for response
    const responsePath = path.join(COLLAB_PATH, "responses", `${requestId}.json`);
    const timeoutMs = timeoutSeconds * 1000;
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      if (fs.existsSync(responsePath)) {
        try {
          const response = JSON.parse(fs.readFileSync(responsePath, "utf-8"));
          try { fs.unlinkSync(responsePath); } catch {}
          try { fs.unlinkSync(requestPath); } catch {}
          return {
            content: [{ type: "text", text: JSON.stringify(response) }],
          };
        } catch {}
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    try { fs.unlinkSync(requestPath); } catch {}

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            request_id: requestId,
            success: false,
            error: "timeout",
            message: `Browser action did not complete within ${timeoutSeconds} seconds`,
          }),
        },
      ],
    };
  }

  /**
   * Handle run_e2e_test - full E2E test scenario
   */
  private async handleE2ETest(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const requestId = this.generateId("e2e");
    const timeoutSeconds = (args.timeout_seconds as number) || 180;

    const request: CollaborationRequest = {
      id: requestId,
      type: "e2e_test",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      to_role: "browser-headless",
      context: {
        scenario: args.scenario,
        steps: args.steps,
        assertions: args.assertions,
        base_url: args.base_url,
        test_data: args.test_data,
      },
      timeout_seconds: timeoutSeconds,
      created_at: new Date().toISOString(),
    };

    // Write request file
    const requestPath = path.join(COLLAB_PATH, "requests", `${requestId}.json`);
    fs.writeFileSync(requestPath, JSON.stringify(request, null, 2));

    // Poll for response
    const responsePath = path.join(COLLAB_PATH, "responses", `${requestId}.json`);
    const timeoutMs = timeoutSeconds * 1000;
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      if (fs.existsSync(responsePath)) {
        try {
          const response = JSON.parse(fs.readFileSync(responsePath, "utf-8"));
          try { fs.unlinkSync(responsePath); } catch {}
          try { fs.unlinkSync(requestPath); } catch {}
          return {
            content: [{ type: "text", text: JSON.stringify(response) }],
          };
        } catch {}
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    try { fs.unlinkSync(requestPath); } catch {}

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            request_id: requestId,
            success: false,
            error: "timeout",
            message: `E2E test did not complete within ${timeoutSeconds} seconds`,
          }),
        },
      ],
    };
  }

  /**
   * Handle capture_screenshot - simple screenshot request
   */
  private async handleScreenshot(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const requestId = this.generateId("ss");
    const timeoutSeconds = (args.timeout_seconds as number) || 30;

    const request: CollaborationRequest = {
      id: requestId,
      type: "screenshot",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      to_role: "browser-headless",
      context: {
        url: args.url,
        selector: args.selector,
        full_page: args.full_page,
        wait_for: args.wait_for,
      },
      timeout_seconds: timeoutSeconds,
      created_at: new Date().toISOString(),
    };

    // Write request file
    const requestPath = path.join(COLLAB_PATH, "requests", `${requestId}.json`);
    fs.writeFileSync(requestPath, JSON.stringify(request, null, 2));

    // Poll for response
    const responsePath = path.join(COLLAB_PATH, "responses", `${requestId}.json`);
    const timeoutMs = timeoutSeconds * 1000;
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      if (fs.existsSync(responsePath)) {
        try {
          const response = JSON.parse(fs.readFileSync(responsePath, "utf-8"));
          try { fs.unlinkSync(responsePath); } catch {}
          try { fs.unlinkSync(requestPath); } catch {}
          return {
            content: [{ type: "text", text: JSON.stringify(response) }],
          };
        } catch {}
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    try { fs.unlinkSync(requestPath); } catch {}

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            request_id: requestId,
            success: false,
            error: "timeout",
            message: `Screenshot capture did not complete within ${timeoutSeconds} seconds`,
          }),
        },
      ],
    };
  }

  /**
   * Handle share_learning - store in memory via event
   */
  private async handleShareLearning(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const eventId = this.generateId("learn");

    const event: CollaborationEvent = {
      id: eventId,
      type: "share_learning",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      payload: {
        learning_type: args.type,
        content: args.content,
        metadata: args.metadata || {},
      },
      created_at: new Date().toISOString(),
    };

    // Write event file
    const eventPath = path.join(COLLAB_PATH, "events", `${eventId}.json`);
    fs.writeFileSync(eventPath, JSON.stringify(event, null, 2));

    // Also write to shared memory cache for quick access
    try {
      const recentPath = path.join(MEMORY_SHARED_PATH, "recent_learnings.json");
      let recent: Array<Record<string, unknown>> = [];

      if (fs.existsSync(recentPath)) {
        try {
          recent = JSON.parse(fs.readFileSync(recentPath, "utf-8"));
        } catch {}
      }

      recent.unshift({
        id: eventId,
        type: args.type,
        content: args.content,
        from_role: WORKER_ROLE,
        timestamp: new Date().toISOString(),
      });

      // Keep only last 50 learnings in quick cache
      recent = recent.slice(0, 50);
      fs.writeFileSync(recentPath, JSON.stringify(recent, null, 2));
    } catch {}

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: true,
            event_id: eventId,
            message: `Learning shared: ${(args.content as string).substring(0, 100)}...`,
          }),
        },
      ],
    };
  }

  /**
   * Handle find_relevant_context - search memory
   */
  private async handleFindContext(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const query = args.query as string;
    const typeFilter = args.type as string | undefined;
    const limit = (args.limit as number) || 5;

    // First, check the quick cache
    const results: Array<Record<string, unknown>> = [];

    try {
      const recentPath = path.join(MEMORY_SHARED_PATH, "recent_learnings.json");
      if (fs.existsSync(recentPath)) {
        const recent = JSON.parse(fs.readFileSync(recentPath, "utf-8")) as Array<Record<string, unknown>>;

        // Simple keyword matching (orchestrator will do semantic search)
        const queryLower = query.toLowerCase();
        const words = queryLower.split(/\s+/);

        for (const item of recent) {
          if (typeFilter && item.type !== typeFilter) continue;

          const content = (item.content as string || "").toLowerCase();
          const matches = words.filter((word) => content.includes(word));

          if (matches.length > 0) {
            results.push({
              ...item,
              relevance: matches.length / words.length,
            });
          }
        }

        // Sort by relevance and limit
        results.sort((a, b) => (b.relevance as number) - (a.relevance as number));
        results.splice(limit);
      }
    } catch {}

    // Also check design system if relevant
    if (query.toLowerCase().includes("design") || query.toLowerCase().includes("color") || query.toLowerCase().includes("style")) {
      try {
        const designPath = path.join(MEMORY_SHARED_PATH, "design_system.json");
        if (fs.existsSync(designPath)) {
          const design = JSON.parse(fs.readFileSync(designPath, "utf-8"));
          results.unshift({
            type: "design_system",
            content: JSON.stringify(design),
            source: "design_system.json",
          });
        }
      } catch {}
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: true,
            results,
            count: results.length,
            note: results.length === 0 ? "No matching context found in quick cache. Orchestrator may have more in long-term memory." : undefined,
          }),
        },
      ],
    };
  }

  /**
   * Handle get_design_system - get project design system
   */
  private async handleGetDesignSystem(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const projectPath = (args.project_path as string) || "/workspace";

    // Check multiple locations for design system
    const possiblePaths = [
      path.join(projectPath, ".clopus", "design", "DESIGN_SYSTEM.md"),
      path.join(projectPath, "DESIGN_SYSTEM.md"),
      path.join(MEMORY_SHARED_PATH, "design_system.json"),
    ];

    for (const designPath of possiblePaths) {
      if (fs.existsSync(designPath)) {
        try {
          const content = fs.readFileSync(designPath, "utf-8");
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  source: designPath,
                  design_system: content,
                }),
              },
            ],
          };
        } catch {}
      }
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            message: "No design system found. Consider asking the designer worker to create one.",
            searched_paths: possiblePaths,
          }),
        },
      ],
    };
  }

  /**
   * Handle report_issue - spawn debugger task
   */
  private async handleReportIssue(args: Record<string, unknown>): Promise<{ content: Array<{ type: string; text: string }> }> {
    const eventId = this.generateId("issue");

    const event: CollaborationEvent = {
      id: eventId,
      type: "report_issue",
      from_worker_id: WORKER_ID,
      from_role: WORKER_ROLE,
      payload: {
        title: args.title,
        description: args.description,
        file_path: args.file_path,
        error_message: args.error_message,
        stack_trace: args.stack_trace,
        severity: args.severity || "medium",
      },
      created_at: new Date().toISOString(),
    };

    // Write event file
    const eventPath = path.join(COLLAB_PATH, "events", `${eventId}.json`);
    fs.writeFileSync(eventPath, JSON.stringify(event, null, 2));

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: true,
            event_id: eventId,
            message: `Issue reported: ${args.title}. Debugger will investigate.`,
            severity: args.severity || "medium",
          }),
        },
      ],
    };
  }

  /**
   * Start the MCP server
   */
  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error(`Collaboration MCP server running (worker ${WORKER_ID}, role: ${WORKER_ROLE})`);
  }
}

// Main entry point
const server = new CollaborationMCP();
server.run().catch((error) => {
  console.error("Failed to start Collaboration MCP:", error);
  process.exit(1);
});
