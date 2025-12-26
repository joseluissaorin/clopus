# =============================================================================
# CLOPUS v3 MCP Generator
# =============================================================================
"""
Generates MCP (Model Context Protocol) servers for external integrations.
Auto-creates TypeScript MCP servers based on API documentation.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("clopus.mcp_generator")


class MCPGenerator:
    """Generate MCP servers for API integrations."""

    def __init__(
        self,
        memory_client,
        github_sync,
        worker_pool,
        mcp_path: str = "/app/mcp-servers"
    ):
        self.memory = memory_client
        self.github_sync = github_sync
        self.worker_pool = worker_pool
        self.mcp_path = Path(mcp_path)
        self.core_path = self.mcp_path / "core"
        self.generated_path = self.mcp_path / "generated"

        # Ensure directories exist
        self.core_path.mkdir(parents=True, exist_ok=True)
        self.generated_path.mkdir(parents=True, exist_ok=True)

    async def generate_mcp(
        self,
        name: str,
        api_spec: Dict[str, Any],
        description: Optional[str] = None
    ) -> Optional[Path]:
        """Generate an MCP server from API specification."""
        logger.info(f"Generating MCP server: {name}")

        # Create MCP directory
        mcp_dir = self.generated_path / name
        mcp_dir.mkdir(parents=True, exist_ok=True)
        src_dir = mcp_dir / "src"
        src_dir.mkdir(exist_ok=True)

        try:
            # Generate package.json
            await self._generate_package_json(mcp_dir, name, description)

            # Generate tsconfig.json
            await self._generate_tsconfig(mcp_dir)

            # Generate main MCP server
            await self._generate_server(src_dir, name, api_spec)

            # Generate types
            await self._generate_types(src_dir, api_spec)

            # Generate README
            await self._generate_readme(mcp_dir, name, description, api_spec)

            # Store in memory
            await self.memory.long_term.store(
                memory_type="api",
                content=f"Generated MCP: {name}\n{description or ''}\nEndpoints: {len(api_spec.get('endpoints', []))}",
                metadata={
                    "mcp_name": name,
                    "generated": True
                }
            )

            # Sync to GitHub
            if self.github_sync:
                await self.github_sync.sync_mcps()

            logger.info(f"Generated MCP server: {mcp_dir}")
            return mcp_dir

        except Exception as e:
            logger.error(f"Error generating MCP {name}: {e}")
            return None

    async def _generate_package_json(
        self,
        mcp_dir: Path,
        name: str,
        description: Optional[str]
    ) -> None:
        """Generate package.json."""
        package = {
            "name": f"@clopus/mcp-{name}",
            "version": "1.0.0",
            "description": description or f"MCP server for {name}",
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "scripts": {
                "build": "tsc",
                "start": "node dist/index.js",
                "dev": "ts-node src/index.ts"
            },
            "dependencies": {
                "@modelcontextprotocol/sdk": "^0.5.0",
                "zod": "^3.22.4"
            },
            "devDependencies": {
                "@types/node": "^20.10.0",
                "typescript": "^5.3.0",
                "ts-node": "^10.9.0"
            },
            "author": "CLOPUS",
            "license": "MIT"
        }

        (mcp_dir / "package.json").write_text(
            json.dumps(package, indent=2)
        )

    async def _generate_tsconfig(self, mcp_dir: Path) -> None:
        """Generate tsconfig.json."""
        tsconfig = {
            "compilerOptions": {
                "target": "ES2022",
                "module": "commonjs",
                "lib": ["ES2022"],
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "declaration": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist"]
        }

        (mcp_dir / "tsconfig.json").write_text(
            json.dumps(tsconfig, indent=2)
        )

    async def _generate_server(
        self,
        src_dir: Path,
        name: str,
        api_spec: Dict
    ) -> None:
        """Generate the main MCP server file."""
        endpoints = api_spec.get("endpoints", [])
        base_url = api_spec.get("base_url", "")
        auth_type = api_spec.get("auth_type", "bearer")

        # Generate tool definitions
        tools = []
        handlers = []

        for endpoint in endpoints:
            tool_name = self._endpoint_to_tool_name(endpoint)
            tools.append(self._generate_tool_definition(endpoint))
            handlers.append(self._generate_handler(endpoint))

        server_code = f'''import {{ Server }} from "@modelcontextprotocol/sdk/server/index.js";
import {{ StdioServerTransport }} from "@modelcontextprotocol/sdk/server/stdio.js";
import {{
  CallToolRequestSchema,
  ListToolsRequestSchema,
}} from "@modelcontextprotocol/sdk/types.js";
import {{ z }} from "zod";

const BASE_URL = "{base_url}";

class {self._to_pascal_case(name)}MCP {{
  private server: Server;
  private apiKey: string;

  constructor() {{
    this.server = new Server(
      {{
        name: "{name}-mcp",
        version: "1.0.0",
      }},
      {{
        capabilities: {{
          tools: {{}},
        }},
      }}
    );

    this.apiKey = process.env.{name.upper()}_API_KEY || "";

    this.setupHandlers();
  }}

  private setupHandlers() {{
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {{
      return {{
        tools: [
{chr(10).join('          ' + t + ',' for t in tools)}
        ],
      }};
    }});

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {{
      const {{ name, arguments: args }} = request.params;

      switch (name) {{
{chr(10).join(handlers)}
        default:
          throw new Error(`Unknown tool: ${{name}}`);
      }}
    }});
  }}

  private async makeRequest(
    method: string,
    path: string,
    body?: any
  ): Promise<any> {{
    const response = await fetch(`${{BASE_URL}}${{path}}`, {{
      method,
      headers: {{
        "Content-Type": "application/json",
        "Authorization": `{"Bearer" if auth_type == "bearer" else "Api-Key"} ${{this.apiKey}}`,
      }},
      body: body ? JSON.stringify(body) : undefined,
    }});

    if (!response.ok) {{
      throw new Error(`API error: ${{response.status}}`);
    }}

    return response.json();
  }}

  async run() {{
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("{name} MCP server running");
  }}
}}

const server = new {self._to_pascal_case(name)}MCP();
server.run().catch(console.error);
'''

        (src_dir / "index.ts").write_text(server_code)

    def _endpoint_to_tool_name(self, endpoint: Dict) -> str:
        """Convert endpoint to tool name."""
        method = endpoint.get("method", "GET").lower()
        path = endpoint.get("path", "")

        # Convert path to name
        name_parts = path.strip("/").split("/")
        name_parts = [p for p in name_parts if not p.startswith("{")]

        return f"{method}_{('_'.join(name_parts))}"

    def _generate_tool_definition(self, endpoint: Dict) -> str:
        """Generate tool definition object."""
        name = self._endpoint_to_tool_name(endpoint)
        description = endpoint.get("description", f"Call {endpoint.get('path')}")
        params = endpoint.get("parameters", [])

        properties = {}
        required = []

        for param in params:
            properties[param["name"]] = {
                "type": param.get("type", "string"),
                "description": param.get("description", "")
            }
            if param.get("required", False):
                required.append(param["name"])

        return f'''{{
            name: "{name}",
            description: "{description}",
            inputSchema: {{
              type: "object",
              properties: {json.dumps(properties)},
              required: {json.dumps(required)},
            }},
          }}'''

    def _generate_handler(self, endpoint: Dict) -> str:
        """Generate handler case for endpoint."""
        name = self._endpoint_to_tool_name(endpoint)
        method = endpoint.get("method", "GET").upper()
        path = endpoint.get("path", "")

        # Handle path parameters
        path_with_params = path
        for match in re.findall(r"\{(\w+)\}", path):
            path_with_params = path_with_params.replace(
                f"{{{match}}}",
                f"${{args.{match}}}"
            )

        body_code = ""
        if method in ("POST", "PUT", "PATCH"):
            body_code = "args"

        return f'''        case "{name}": {{
          const result = await this.makeRequest(
            "{method}",
            `{path_with_params}`,
            {body_code or "undefined"}
          );
          return {{ content: [{{ type: "text", text: JSON.stringify(result, null, 2) }}] }};
        }}'''

    async def _generate_types(self, src_dir: Path, api_spec: Dict) -> None:
        """Generate TypeScript types."""
        types_code = '''// Auto-generated types

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
'''

        (src_dir / "types.ts").write_text(types_code)

    async def _generate_readme(
        self,
        mcp_dir: Path,
        name: str,
        description: Optional[str],
        api_spec: Dict
    ) -> None:
        """Generate README.md."""
        endpoints = api_spec.get("endpoints", [])

        readme = f'''# {name} MCP Server

{description or f"MCP server for {name} API integration."}

## Installation

```bash
npm install
npm run build
```

## Configuration

Set the following environment variable:

```bash
export {name.upper()}_API_KEY="your-api-key"
```

## Usage

Add to your Claude Code MCP configuration:

```json
{{
  "mcpServers": {{
    "{name}": {{
      "command": "node",
      "args": ["{mcp_dir}/dist/index.js"],
      "env": {{
        "{name.upper()}_API_KEY": "your-api-key"
      }}
    }}
  }}
}}
```

## Available Tools

'''

        for endpoint in endpoints:
            tool_name = self._endpoint_to_tool_name(endpoint)
            readme += f"- `{tool_name}`: {endpoint.get('description', '')}\n"

        readme += "\n---\nGenerated by CLOPUS\n"

        (mcp_dir / "README.md").write_text(readme)

    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        return "".join(word.capitalize() for word in name.split("-"))

    async def discover_mcps(self) -> List[Dict]:
        """Discover all available MCP servers."""
        mcps = []

        for mcp_dir in self.core_path.iterdir():
            if mcp_dir.is_dir() and (mcp_dir / "package.json").exists():
                mcp = self._load_mcp_info(mcp_dir)
                if mcp:
                    mcp["source"] = "core"
                    mcps.append(mcp)

        for mcp_dir in self.generated_path.iterdir():
            if mcp_dir.is_dir() and (mcp_dir / "package.json").exists():
                mcp = self._load_mcp_info(mcp_dir)
                if mcp:
                    mcp["source"] = "generated"
                    mcps.append(mcp)

        return mcps

    def _load_mcp_info(self, mcp_dir: Path) -> Optional[Dict]:
        """Load MCP server info."""
        try:
            package = json.loads((mcp_dir / "package.json").read_text())
            return {
                "name": package.get("name", mcp_dir.name),
                "version": package.get("version", "1.0.0"),
                "description": package.get("description", ""),
                "path": str(mcp_dir)
            }
        except Exception:
            return None

    async def generate_from_url(self, api_docs_url: str, name: str) -> Optional[Path]:
        """Generate MCP from API documentation URL."""
        # Use researcher worker to fetch and analyze docs
        if not self.worker_pool:
            return None

        researcher_id = self.worker_pool.get_worker_by_role("researcher")
        if not researcher_id:
            return None

        # Dispatch research task
        await self.worker_pool.dispatch_task(
            worker_id=researcher_id,
            task_id=f"research_api_{name}",
            title=f"Research API: {name}",
            description=f"Analyze the API documentation at {api_docs_url} and extract: base URL, endpoints (method, path, parameters, description), authentication type."
        )

        # Wait for result
        for _ in range(60):
            results = await self.worker_pool.collect_results()
            if researcher_id in results:
                result = results[researcher_id].get("result", "")
                api_spec = self._parse_api_research(result)
                if api_spec:
                    return await self.generate_mcp(name, api_spec)
            await asyncio.sleep(5)

        return None

    def _parse_api_research(self, result: str) -> Optional[Dict]:
        """Parse API research result into spec."""
        # This would parse Claude's research output
        # For now, return a basic structure
        return {
            "base_url": "",
            "auth_type": "bearer",
            "endpoints": []
        }
