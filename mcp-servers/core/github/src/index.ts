import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Octokit } from "@octokit/rest";

class GitHubMCP {
  private server: Server;
  private octokit: Octokit | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "github-mcp",
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

  private getOctokit(): Octokit {
    if (!this.octokit) {
      const token = process.env.GITHUB_TOKEN;
      if (!token) {
        throw new Error("GITHUB_TOKEN environment variable not set");
      }
      this.octokit = new Octokit({ auth: token });
    }
    return this.octokit;
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "create_repo",
            description: "Create a new GitHub repository",
            inputSchema: {
              type: "object",
              properties: {
                name: { type: "string", description: "Repository name" },
                description: { type: "string", description: "Repository description" },
                private: { type: "boolean", description: "Make repository private" },
                auto_init: { type: "boolean", description: "Initialize with README" },
              },
              required: ["name"],
            },
          },
          {
            name: "get_repo",
            description: "Get repository information",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
              },
              required: ["owner", "repo"],
            },
          },
          {
            name: "list_repos",
            description: "List repositories for authenticated user or organization",
            inputSchema: {
              type: "object",
              properties: {
                org: { type: "string", description: "Organization name (optional)" },
                type: {
                  type: "string",
                  enum: ["all", "owner", "public", "private", "member"],
                },
                sort: {
                  type: "string",
                  enum: ["created", "updated", "pushed", "full_name"],
                },
              },
            },
          },
          {
            name: "create_branch",
            description: "Create a new branch",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                branch: { type: "string", description: "New branch name" },
                from_branch: {
                  type: "string",
                  description: "Source branch (default: default branch)",
                },
              },
              required: ["owner", "repo", "branch"],
            },
          },
          {
            name: "create_pr",
            description: "Create a pull request",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                title: { type: "string", description: "PR title" },
                body: { type: "string", description: "PR description" },
                head: { type: "string", description: "Head branch" },
                base: { type: "string", description: "Base branch" },
                draft: { type: "boolean", description: "Create as draft" },
              },
              required: ["owner", "repo", "title", "head", "base"],
            },
          },
          {
            name: "merge_pr",
            description: "Merge a pull request",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                pull_number: { type: "number", description: "PR number" },
                merge_method: {
                  type: "string",
                  enum: ["merge", "squash", "rebase"],
                },
                commit_title: { type: "string", description: "Commit title" },
              },
              required: ["owner", "repo", "pull_number"],
            },
          },
          {
            name: "create_issue",
            description: "Create an issue",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                title: { type: "string", description: "Issue title" },
                body: { type: "string", description: "Issue body" },
                labels: {
                  type: "array",
                  items: { type: "string" },
                  description: "Labels",
                },
                assignees: {
                  type: "array",
                  items: { type: "string" },
                  description: "Assignees",
                },
              },
              required: ["owner", "repo", "title"],
            },
          },
          {
            name: "list_issues",
            description: "List issues for a repository",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                state: { type: "string", enum: ["open", "closed", "all"] },
                labels: { type: "string", description: "Comma-separated labels" },
              },
              required: ["owner", "repo"],
            },
          },
          {
            name: "get_file",
            description: "Get file contents from repository",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                path: { type: "string", description: "File path" },
                ref: { type: "string", description: "Branch/tag/commit" },
              },
              required: ["owner", "repo", "path"],
            },
          },
          {
            name: "create_or_update_file",
            description: "Create or update a file in repository",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                path: { type: "string", description: "File path" },
                message: { type: "string", description: "Commit message" },
                content: { type: "string", description: "File content" },
                branch: { type: "string", description: "Branch name" },
                sha: { type: "string", description: "SHA of file to update" },
              },
              required: ["owner", "repo", "path", "message", "content"],
            },
          },
          {
            name: "list_commits",
            description: "List commits for a repository",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                sha: { type: "string", description: "Branch/tag/SHA" },
                path: { type: "string", description: "File path filter" },
                per_page: { type: "number", description: "Results per page" },
              },
              required: ["owner", "repo"],
            },
          },
          {
            name: "create_release",
            description: "Create a release",
            inputSchema: {
              type: "object",
              properties: {
                owner: { type: "string", description: "Repository owner" },
                repo: { type: "string", description: "Repository name" },
                tag_name: { type: "string", description: "Tag name" },
                name: { type: "string", description: "Release name" },
                body: { type: "string", description: "Release notes" },
                draft: { type: "boolean", description: "Create as draft" },
                prerelease: { type: "boolean", description: "Mark as prerelease" },
              },
              required: ["owner", "repo", "tag_name"],
            },
          },
          {
            name: "get_user",
            description: "Get authenticated user info",
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
      const octokit = this.getOctokit();

      switch (name) {
        case "create_repo": {
          const response = await octokit.repos.createForAuthenticatedUser({
            name: args.name as string,
            description: args.description as string | undefined,
            private: args.private as boolean | undefined,
            auto_init: args.auto_init as boolean | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  repo: response.data.full_name,
                  url: response.data.html_url,
                  clone_url: response.data.clone_url,
                }),
              },
            ],
          };
        }

        case "get_repo": {
          const response = await octokit.repos.get({
            owner: args.owner as string,
            repo: args.repo as string,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  name: response.data.full_name,
                  description: response.data.description,
                  url: response.data.html_url,
                  default_branch: response.data.default_branch,
                  stars: response.data.stargazers_count,
                  forks: response.data.forks_count,
                  open_issues: response.data.open_issues_count,
                  created_at: response.data.created_at,
                  updated_at: response.data.updated_at,
                }),
              },
            ],
          };
        }

        case "list_repos": {
          const response = args.org
            ? await octokit.repos.listForOrg({
                org: args.org as string,
                type: args.type as "all" | "public" | "private" | "forks" | "sources" | "member" | undefined,
                sort: args.sort as "created" | "updated" | "pushed" | "full_name" | undefined,
              })
            : await octokit.repos.listForAuthenticatedUser({
                type: args.type as "all" | "owner" | "public" | "private" | "member" | undefined,
                sort: args.sort as "created" | "updated" | "pushed" | "full_name" | undefined,
              });

          const repos = response.data.map((r) => ({
            name: r.full_name,
            description: r.description,
            private: r.private,
            url: r.html_url,
          }));

          return {
            content: [{ type: "text", text: JSON.stringify({ repos }) }],
          };
        }

        case "create_branch": {
          const owner = args.owner as string;
          const repo = args.repo as string;

          // Get source branch SHA
          const repoInfo = await octokit.repos.get({ owner, repo });
          const sourceBranch = (args.from_branch as string) || repoInfo.data.default_branch;

          const refResponse = await octokit.git.getRef({
            owner,
            repo,
            ref: `heads/${sourceBranch}`,
          });

          await octokit.git.createRef({
            owner,
            repo,
            ref: `refs/heads/${args.branch}`,
            sha: refResponse.data.object.sha,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  branch: args.branch,
                  from: sourceBranch,
                }),
              },
            ],
          };
        }

        case "create_pr": {
          const response = await octokit.pulls.create({
            owner: args.owner as string,
            repo: args.repo as string,
            title: args.title as string,
            body: args.body as string | undefined,
            head: args.head as string,
            base: args.base as string,
            draft: args.draft as boolean | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  number: response.data.number,
                  url: response.data.html_url,
                  state: response.data.state,
                }),
              },
            ],
          };
        }

        case "merge_pr": {
          const response = await octokit.pulls.merge({
            owner: args.owner as string,
            repo: args.repo as string,
            pull_number: args.pull_number as number,
            merge_method: args.merge_method as "merge" | "squash" | "rebase" | undefined,
            commit_title: args.commit_title as string | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: response.data.merged,
                  sha: response.data.sha,
                  message: response.data.message,
                }),
              },
            ],
          };
        }

        case "create_issue": {
          const response = await octokit.issues.create({
            owner: args.owner as string,
            repo: args.repo as string,
            title: args.title as string,
            body: args.body as string | undefined,
            labels: args.labels as string[] | undefined,
            assignees: args.assignees as string[] | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  number: response.data.number,
                  url: response.data.html_url,
                }),
              },
            ],
          };
        }

        case "list_issues": {
          const response = await octokit.issues.listForRepo({
            owner: args.owner as string,
            repo: args.repo as string,
            state: args.state as "open" | "closed" | "all" | undefined,
            labels: args.labels as string | undefined,
          });

          const issues = response.data.map((i) => ({
            number: i.number,
            title: i.title,
            state: i.state,
            url: i.html_url,
            labels: i.labels.map((l) => (typeof l === "string" ? l : l.name)),
          }));

          return {
            content: [{ type: "text", text: JSON.stringify({ issues }) }],
          };
        }

        case "get_file": {
          const response = await octokit.repos.getContent({
            owner: args.owner as string,
            repo: args.repo as string,
            path: args.path as string,
            ref: args.ref as string | undefined,
          });

          const data = response.data as { content?: string; encoding?: string; sha: string };

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  path: args.path,
                  sha: data.sha,
                  content: data.content
                    ? Buffer.from(data.content, "base64").toString("utf-8")
                    : null,
                }),
              },
            ],
          };
        }

        case "create_or_update_file": {
          const response = await octokit.repos.createOrUpdateFileContents({
            owner: args.owner as string,
            repo: args.repo as string,
            path: args.path as string,
            message: args.message as string,
            content: Buffer.from(args.content as string).toString("base64"),
            branch: args.branch as string | undefined,
            sha: args.sha as string | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  commit: response.data.commit.sha,
                  path: args.path,
                }),
              },
            ],
          };
        }

        case "list_commits": {
          const response = await octokit.repos.listCommits({
            owner: args.owner as string,
            repo: args.repo as string,
            sha: args.sha as string | undefined,
            path: args.path as string | undefined,
            per_page: args.per_page as number | undefined,
          });

          const commits = response.data.map((c) => ({
            sha: c.sha,
            message: c.commit.message,
            author: c.commit.author?.name,
            date: c.commit.author?.date,
          }));

          return {
            content: [{ type: "text", text: JSON.stringify({ commits }) }],
          };
        }

        case "create_release": {
          const response = await octokit.repos.createRelease({
            owner: args.owner as string,
            repo: args.repo as string,
            tag_name: args.tag_name as string,
            name: args.name as string | undefined,
            body: args.body as string | undefined,
            draft: args.draft as boolean | undefined,
            prerelease: args.prerelease as boolean | undefined,
          });

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  id: response.data.id,
                  tag: response.data.tag_name,
                  url: response.data.html_url,
                }),
              },
            ],
          };
        }

        case "get_user": {
          const response = await octokit.users.getAuthenticated();

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  login: response.data.login,
                  name: response.data.name,
                  email: response.data.email,
                  public_repos: response.data.public_repos,
                  private_repos: response.data.total_private_repos,
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
    console.error("GitHub MCP server running");
  }
}

const server = new GitHubMCP();
server.run().catch(console.error);
