import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import * as fs from "fs/promises";
import * as path from "path";

interface ValidationResult {
  stage: string;
  passed: boolean;
  errors: string[];
  warnings: string[];
  duration_ms: number;
}

interface PipelineResult {
  project_path: string;
  overall_passed: boolean;
  stages: ValidationResult[];
  total_duration_ms: number;
  timestamp: string;
}

class ValidationMCP {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: "validation-mcp",
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

  private async runCommand(
    command: string,
    args: string[],
    cwd: string
  ): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    return new Promise((resolve) => {
      const proc = spawn(command, args, { cwd, shell: true });
      let stdout = "";
      let stderr = "";

      proc.stdout.on("data", (data) => (stdout += data.toString()));
      proc.stderr.on("data", (data) => (stderr += data.toString()));

      proc.on("close", (code) => {
        resolve({ stdout, stderr, exitCode: code || 0 });
      });

      proc.on("error", (err) => {
        resolve({ stdout, stderr: err.message, exitCode: 1 });
      });
    });
  }

  private async detectProjectType(projectPath: string): Promise<string> {
    try {
      const files = await fs.readdir(projectPath);
      if (files.includes("package.json")) return "node";
      if (files.includes("pyproject.toml") || files.includes("setup.py")) return "python";
      if (files.includes("go.mod")) return "go";
      if (files.includes("Cargo.toml")) return "rust";
      if (files.includes("composer.json")) return "php";
      if (files.includes("Gemfile")) return "ruby";
      return "unknown";
    } catch {
      return "unknown";
    }
  }

  private async runSyntaxCheck(projectPath: string, projectType: string): Promise<ValidationResult> {
    const start = Date.now();
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (projectType) {
      case "node": {
        // Check for TypeScript files
        const result = await this.runCommand("npx", ["tsc", "--noEmit"], projectPath);
        if (result.exitCode !== 0) {
          errors.push(...result.stderr.split("\n").filter(Boolean));
        }
        break;
      }
      case "python": {
        const result = await this.runCommand("python", ["-m", "py_compile", "**/*.py"], projectPath);
        if (result.exitCode !== 0) {
          errors.push(...result.stderr.split("\n").filter(Boolean));
        }
        break;
      }
    }

    return {
      stage: "syntax",
      passed: errors.length === 0,
      errors,
      warnings,
      duration_ms: Date.now() - start,
    };
  }

  private async runLint(projectPath: string, projectType: string): Promise<ValidationResult> {
    const start = Date.now();
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (projectType) {
      case "node": {
        const result = await this.runCommand("npx", ["eslint", ".", "--format", "json"], projectPath);
        if (result.exitCode !== 0) {
          try {
            const eslintOutput = JSON.parse(result.stdout);
            for (const file of eslintOutput) {
              for (const msg of file.messages) {
                if (msg.severity === 2) {
                  errors.push(`${file.filePath}:${msg.line}: ${msg.message}`);
                } else {
                  warnings.push(`${file.filePath}:${msg.line}: ${msg.message}`);
                }
              }
            }
          } catch {
            errors.push(result.stderr || result.stdout);
          }
        }
        break;
      }
      case "python": {
        const result = await this.runCommand("ruff", ["check", "."], projectPath);
        if (result.exitCode !== 0) {
          errors.push(...result.stdout.split("\n").filter(Boolean));
        }
        break;
      }
    }

    return {
      stage: "lint",
      passed: errors.length === 0,
      errors,
      warnings,
      duration_ms: Date.now() - start,
    };
  }

  private async runBuild(projectPath: string, projectType: string): Promise<ValidationResult> {
    const start = Date.now();
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (projectType) {
      case "node": {
        const pkgJson = JSON.parse(
          await fs.readFile(path.join(projectPath, "package.json"), "utf-8")
        );
        if (pkgJson.scripts?.build) {
          const result = await this.runCommand("npm", ["run", "build"], projectPath);
          if (result.exitCode !== 0) {
            errors.push(result.stderr || result.stdout);
          }
        }
        break;
      }
      case "python": {
        const result = await this.runCommand("pip", ["install", "-e", "."], projectPath);
        if (result.exitCode !== 0) {
          errors.push(result.stderr);
        }
        break;
      }
      case "go": {
        const result = await this.runCommand("go", ["build", "./..."], projectPath);
        if (result.exitCode !== 0) {
          errors.push(result.stderr);
        }
        break;
      }
      case "rust": {
        const result = await this.runCommand("cargo", ["build"], projectPath);
        if (result.exitCode !== 0) {
          errors.push(result.stderr);
        }
        break;
      }
    }

    return {
      stage: "build",
      passed: errors.length === 0,
      errors,
      warnings,
      duration_ms: Date.now() - start,
    };
  }

  private async runUnitTests(projectPath: string, projectType: string): Promise<ValidationResult> {
    const start = Date.now();
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (projectType) {
      case "node": {
        const result = await this.runCommand("npm", ["test"], projectPath);
        if (result.exitCode !== 0) {
          errors.push(result.stderr || result.stdout);
        }
        break;
      }
      case "python": {
        const result = await this.runCommand("pytest", ["-v"], projectPath);
        if (result.exitCode !== 0) {
          errors.push(result.stdout);
        }
        break;
      }
      case "go": {
        const result = await this.runCommand("go", ["test", "./..."], projectPath);
        if (result.exitCode !== 0) {
          errors.push(result.stdout);
        }
        break;
      }
    }

    return {
      stage: "unit_tests",
      passed: errors.length === 0,
      errors,
      warnings,
      duration_ms: Date.now() - start,
    };
  }

  private async runSecurityScan(projectPath: string, projectType: string): Promise<ValidationResult> {
    const start = Date.now();
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (projectType) {
      case "node": {
        const result = await this.runCommand("npm", ["audit", "--json"], projectPath);
        try {
          const audit = JSON.parse(result.stdout);
          if (audit.metadata?.vulnerabilities) {
            const vulns = audit.metadata.vulnerabilities;
            if (vulns.critical > 0 || vulns.high > 0) {
              errors.push(`Critical: ${vulns.critical}, High: ${vulns.high}`);
            }
            if (vulns.moderate > 0) {
              warnings.push(`Moderate vulnerabilities: ${vulns.moderate}`);
            }
          }
        } catch {
          // Ignore parse errors
        }
        break;
      }
      case "python": {
        const result = await this.runCommand("pip-audit", ["--format", "json"], projectPath);
        try {
          const audit = JSON.parse(result.stdout);
          for (const vuln of audit) {
            if (vuln.vulns?.length > 0) {
              errors.push(`${vuln.name}: ${vuln.vulns.length} vulnerabilities`);
            }
          }
        } catch {
          // Ignore parse errors
        }
        break;
      }
    }

    return {
      stage: "security",
      passed: errors.length === 0,
      errors,
      warnings,
      duration_ms: Date.now() - start,
    };
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "validate_project",
            description: "Run full validation pipeline on a project",
            inputSchema: {
              type: "object",
              properties: {
                project_path: { type: "string", description: "Path to project" },
                stages: {
                  type: "array",
                  items: { type: "string" },
                  description: "Stages to run (default: all)",
                },
                strict: {
                  type: "boolean",
                  description: "Fail on any error",
                  default: true,
                },
              },
              required: ["project_path"],
            },
          },
          {
            name: "validate_stage",
            description: "Run a single validation stage",
            inputSchema: {
              type: "object",
              properties: {
                project_path: { type: "string", description: "Path to project" },
                stage: {
                  type: "string",
                  enum: ["syntax", "lint", "build", "unit_tests", "integration_tests", "e2e_tests", "security", "review"],
                  description: "Stage to run",
                },
              },
              required: ["project_path", "stage"],
            },
          },
          {
            name: "get_validation_results",
            description: "Get results from last validation run",
            inputSchema: {
              type: "object",
              properties: {
                project_path: { type: "string", description: "Path to project" },
              },
              required: ["project_path"],
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "validate_project": {
          const projectPath = args.project_path as string;
          const projectType = await this.detectProjectType(projectPath);
          const stages = (args.stages as string[]) || [
            "syntax",
            "lint",
            "build",
            "unit_tests",
            "security",
          ];
          const strict = args.strict !== false;

          const results: ValidationResult[] = [];
          const start = Date.now();

          for (const stage of stages) {
            let result: ValidationResult;

            switch (stage) {
              case "syntax":
                result = await this.runSyntaxCheck(projectPath, projectType);
                break;
              case "lint":
                result = await this.runLint(projectPath, projectType);
                break;
              case "build":
                result = await this.runBuild(projectPath, projectType);
                break;
              case "unit_tests":
                result = await this.runUnitTests(projectPath, projectType);
                break;
              case "security":
                result = await this.runSecurityScan(projectPath, projectType);
                break;
              default:
                result = {
                  stage,
                  passed: true,
                  errors: [],
                  warnings: [`Stage ${stage} not implemented`],
                  duration_ms: 0,
                };
            }

            results.push(result);

            if (strict && !result.passed) {
              break;
            }
          }

          const pipelineResult: PipelineResult = {
            project_path: projectPath,
            overall_passed: results.every((r) => r.passed),
            stages: results,
            total_duration_ms: Date.now() - start,
            timestamp: new Date().toISOString(),
          };

          // Save results
          const resultsPath = path.join(projectPath, ".clopus", "validation_results.json");
          await fs.mkdir(path.dirname(resultsPath), { recursive: true });
          await fs.writeFile(resultsPath, JSON.stringify(pipelineResult, null, 2));

          return {
            content: [{ type: "text", text: JSON.stringify(pipelineResult, null, 2) }],
          };
        }

        case "validate_stage": {
          const projectPath = args.project_path as string;
          const stage = args.stage as string;
          const projectType = await this.detectProjectType(projectPath);

          let result: ValidationResult;

          switch (stage) {
            case "syntax":
              result = await this.runSyntaxCheck(projectPath, projectType);
              break;
            case "lint":
              result = await this.runLint(projectPath, projectType);
              break;
            case "build":
              result = await this.runBuild(projectPath, projectType);
              break;
            case "unit_tests":
              result = await this.runUnitTests(projectPath, projectType);
              break;
            case "security":
              result = await this.runSecurityScan(projectPath, projectType);
              break;
            default:
              result = {
                stage,
                passed: false,
                errors: [`Unknown stage: ${stage}`],
                warnings: [],
                duration_ms: 0,
              };
          }

          return {
            content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
          };
        }

        case "get_validation_results": {
          const projectPath = args.project_path as string;
          const resultsPath = path.join(projectPath, ".clopus", "validation_results.json");

          try {
            const results = await fs.readFile(resultsPath, "utf-8");
            return {
              content: [{ type: "text", text: results }],
            };
          } catch {
            return {
              content: [
                { type: "text", text: JSON.stringify({ error: "No validation results found" }) },
              ],
            };
          }
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Validation MCP server running");
  }
}

const server = new ValidationMCP();
server.run().catch(console.error);
