# CLOPUS v3

**Autonomous Multi-Agent Claude Code System**

CLOPUS (Claude-based Locally Orchestrated Production Unified System) is a fully autonomous development system that orchestrates multiple Claude Code instances to build complete software projects with minimal human intervention.

## Features

- **Multi-Agent Architecture**: 5 parallel Claude Code workers with specialized roles (Coder, Tester, Reviewer, Researcher, Debugger)
- **Python Orchestrator**: Async orchestration with intelligent task planning and distribution
- **Dual Memory System**: SQLite for short-term state, ChromaDB for long-term semantic memory
- **Self-Generating Ecosystem**: Automatically creates skills, MCP servers, and templates from patterns
- **8-Stage Validation Pipeline**: Syntax → Lint → Build → Unit Tests → Integration Tests → E2E Tests → Security → Code Review
- **Confidence-Based Autonomy**: Only asks for human input when genuinely uncertain (threshold: 0.7)
- **Browser Automation**: Dual support via MCP server (Playwright) and VNC container (Chromium)
- **Universal Dev Tools**: Python, Node.js, Go, Rust, PHP, Ruby, cloud CLIs, and more
- **GitHub Integration**: Auto-sync skills/templates/MCPs to shared repo, separate repos per project

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- GitHub CLI (`gh`) authenticated
- Anthropic API key or Claude Max subscription

### Installation

```bash
# Clone the repository
git clone https://github.com/joseluissaorin/clopus.git
cd clopus

# Run setup
./setup.sh

# Start CLOPUS
./clopus start
```

### One-Liner Install

```bash
curl -fsSL https://raw.githubusercontent.com/joseluissaorin/clopus/main/install.sh | bash
```

## Usage

### Basic Commands

```bash
# Start the system
./clopus start

# Stop the system
./clopus stop

# Check system status
./clopus status

# Give an objective
./clopus objective "Build a todo app with React and FastAPI backend"

# View pending questions
./clopus questions

# Answer a question
./clopus answer <question_id> "Your answer here"

# View worker status
./clopus workers

# View logs
./clopus logs [service]

# List available skills
./clopus skills

# List available templates
./clopus templates

# Sync to GitHub
./clopus sync

# Login (configure API key or subscription)
./clopus login
```

### File-Based Interface

You can also interact with CLOPUS via files:

```bash
# Submit an objective
echo "Build a REST API for user management" > ipc/interface/objective.txt

# Check for questions
cat ipc/interface/questions.json

# Submit answers
echo '{"question_id": "q123", "answer": "Use JWT for auth"}' > ipc/interface/answer.txt

# View status
cat ipc/interface/status.json
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (CLI / File / Webhook)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PYTHON ORCHESTRATOR                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │  Objective  │ │    Task     │ │ Confidence  │               │
│  │   Parser    │ │   Planner   │ │   Engine    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Worker    │ │   Memory    │ │   GitHub    │               │
│  │    Pool     │ │   Client    │ │    Sync     │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Skills    │ │     MCP     │ │  Template   │               │
│  │   Engine    │ │  Generator  │ │  Extractor  │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   Worker 1    │       │   Worker 2    │       │   Worker 3    │
│    (Coder)    │       │   (Tester)    │       │  (Reviewer)   │
└───────────────┘       └───────────────┘       └───────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   Worker 4    │       │   Worker 5    │       │  Validation   │
│ (Researcher)  │       │  (Debugger)   │       │   Pipeline    │
└───────────────┘       └───────────────┘       └───────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│    SQLite     │       │   ChromaDB    │       │  MCP Servers  │
│ (Short-term)  │       │ (Long-term)   │       │  (Browser,    │
│               │       │               │       │   Memory...)  │
└───────────────┘       └───────────────┘       └───────────────┘
```

## Worker Roles

| Worker | Role | Responsibilities |
|--------|------|------------------|
| Worker 1 | **Coder** | Primary development, feature implementation |
| Worker 2 | **Tester** | Write and run tests (unit, integration, E2E) |
| Worker 3 | **Reviewer** | Code review, quality assurance, best practices |
| Worker 4 | **Researcher** | Documentation, API research, solution discovery |
| Worker 5 | **Debugger** | Bug fixing, performance optimization, troubleshooting |

## Validation Pipeline

All generated code passes through 8 validation stages:

1. **Syntax Check** - Language-specific syntax validation
2. **Lint** - ESLint, Pylint, Ruff, and more
3. **Build** - Compilation and build verification
4. **Unit Tests** - Jest, pytest, Go test
5. **Integration Tests** - API and service integration
6. **E2E Tests** - Playwright/Cypress browser tests
7. **Security Scan** - npm audit, pip-audit, pattern detection
8. **Code Review** - Automated review by Reviewer worker

## Memory System

### Short-Term (SQLite)
- Current objectives and tasks
- Worker states and assignments
- Validation results
- Session state

### Long-Term (ChromaDB)
- Learned patterns and solutions
- Project context and decisions
- Error resolutions
- Skill and template metadata

## Self-Generating Ecosystem

### Skills
CLOPUS automatically discovers and generates skills:
- Scans filesystem for SKILL.md files
- Generates new skills from recurring patterns
- Validates and tests generated skills
- Syncs to GitHub repository

### MCP Servers
When external API access is needed:
- Searches existing MCP servers
- Researches API documentation
- Generates TypeScript MCP server
- Tests and validates
- Syncs to GitHub

### Templates
After completing projects:
- Analyzes project structure
- Abstracts project-specific details
- Creates parameterized templates
- Validates template can regenerate original
- Syncs to GitHub

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...        # Or use Claude subscription
GITHUB_TOKEN=ghp_...                 # For GitHub operations

# Optional
CLOPUS_WORKERS=5                     # Number of parallel workers
CLOPUS_CONFIDENCE_THRESHOLD=0.7      # Autonomy threshold
CLOPUS_VALIDATION_STRICT=true        # Require all stages to pass
CLOPUS_PROJECT_DIR=/home/user/Dev    # Project output directory
CLOPUS_LOG_LEVEL=INFO                # Logging level

# Services
POSTGRES_PASSWORD=clopus
REDIS_PASSWORD=clopus
MINIO_ROOT_USER=clopus
MINIO_ROOT_PASSWORD=clopuspassword
RESEND_API_KEY=re_...                # For email sending
```

### config.yaml

```yaml
workers:
  count: 5
  heartbeat_interval: 30
  task_timeout: 3600
  roles:
    - coder
    - tester
    - reviewer
    - researcher
    - debugger

memory:
  sqlite_path: ./data/clopus.db
  chromadb_path: ./data/chromadb
  embedding_model: all-MiniLM-L6-v2

validation:
  strict_mode: true
  required_stages:
    - syntax
    - lint
    - build
    - unit_tests
  optional_stages:
    - integration_tests
    - e2e_tests
    - security
    - review

confidence:
  threshold: 0.7
  factors:
    task_complexity: 0.2
    similar_past_success: 0.25
    clear_requirements: 0.25
    available_context: 0.15
    domain_familiarity: 0.15

github:
  auto_sync: true
  skills_repo: clopus
  create_project_repos: true
```

## Directory Structure

```
clopus/
├── clopus                    # Main CLI entrypoint
├── setup.sh                  # Setup script
├── docker-compose.yml        # Service orchestration
├── Dockerfile.*              # Container definitions
├── config.yaml               # Configuration
│
├── orchestrator/             # Python orchestrator
│   ├── main.py               # Entry point
│   ├── config.py             # Configuration loading
│   ├── objective_parser.py   # Parse user objectives
│   ├── task_planner.py       # Break into tasks
│   ├── worker_pool.py        # Manage workers
│   ├── confidence_engine.py  # Decision confidence
│   ├── memory_client.py      # Memory interface
│   ├── skills_engine.py      # Skill management
│   ├── mcp_generator.py      # Generate MCPs
│   ├── template_extractor.py # Extract templates
│   ├── github_sync.py        # GitHub operations
│   └── service_manager.py    # Service lifecycle
│
├── memory/                   # Memory system
│   ├── short_term.py         # SQLite operations
│   ├── long_term.py          # ChromaDB operations
│   ├── embeddings.py         # Embedding generation
│   └── schema.sql            # Database schema
│
├── validation/               # Validation pipeline
│   ├── pipeline.py           # Stage orchestration
│   └── stages/               # Individual validators
│
├── interfaces/               # User interfaces
│   ├── cli_adapter.py        # CLI interface
│   └── file_adapter.py       # File-based interface
│
├── mcp-servers/              # MCP servers
│   └── core/                 # Core servers
│       ├── browser/          # Playwright automation
│       ├── memory/           # Memory access
│       ├── validation/       # Run validation
│       ├── email-resend/     # Resend email
│       ├── email-smtp/       # SMTP email
│       ├── database-postgres/# PostgreSQL
│       ├── database-redis/   # Redis
│       ├── storage-s3/       # S3/MinIO
│       ├── github/           # GitHub API
│       └── search/           # Web search
│
├── skills/                   # Claude Skills
│   └── core/                 # Core skills
│       ├── development/      # Dev skills
│       ├── testing/          # Test skills
│       ├── data/             # Data skills
│       └── devops/           # DevOps skills
│
├── templates/                # Project templates
│   └── core/                 # Core templates
│
├── workers/                  # Worker configuration
│   ├── system-prompts/       # Role-specific prompts
│   └── hooks/                # Pre/post task hooks
│
├── monitoring/               # Monitoring configs
│   ├── prometheus.yml
│   └── grafana/
│
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── ipc/                      # Inter-process communication
│   ├── tasks/                # Worker task queues
│   └── interface/            # User interface files
│
└── data/                     # Persistent data
    ├── clopus.db             # SQLite database
    └── chromadb/             # Vector database
```

## MCP Servers

### Core Servers

| Server | Description | Tools |
|--------|-------------|-------|
| **browser** | Playwright automation | navigate, screenshot, click, fill, get_text, get_html |
| **memory** | Memory system access | store, retrieve, search, forget |
| **validation** | Run validation pipeline | validate, get_results |
| **email-resend** | Email via Resend API | send_email, send_template |
| **email-smtp** | Email via SMTP | send_email, send_with_attachment |
| **database-postgres** | PostgreSQL operations | query, execute, transaction |
| **database-redis** | Redis operations | get, set, delete, publish, subscribe |
| **storage-s3** | S3/MinIO storage | upload, download, list, delete |
| **github** | GitHub API operations | create_repo, create_pr, merge_pr, create_issue |
| **search** | Web search | search, fetch_page |

## Skills

Skills are Claude-invokable capabilities defined in SKILL.md files:

```markdown
---
name: react-typescript
description: Build React applications with TypeScript
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Glob
triggers:
  - react
  - typescript
  - frontend
---

# React TypeScript Development

## Context
You are building a React application with TypeScript...

## Instructions
1. Use functional components with hooks
2. Define proper TypeScript interfaces
...
```

### Available Core Skills

- **react-typescript** - React + TypeScript development
- **python-fastapi** - FastAPI backend development
- **playwright-e2e** - End-to-end testing with Playwright
- **web-scraping** - Web scraping with various tools
- **docker-containerization** - Docker and containerization

## Templates

Templates are reusable project scaffolds:

```json
{
  "name": "saas-starter",
  "description": "Full-stack SaaS application",
  "parameters": {
    "PROJECT_NAME": {"required": true},
    "DATABASE_URL": {"required": true}
  },
  "technologies": ["nextjs", "prisma", "stripe"],
  "features": ["authentication", "payments", "dashboard"]
}
```

### Available Core Templates

- **saas-starter** - Full-stack SaaS with Next.js, Prisma, Stripe
- **python-api** - FastAPI backend with SQLAlchemy, auth, testing

## Monitoring

CLOPUS includes Prometheus and Grafana for monitoring:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

Metrics tracked:
- Worker status and task throughput
- Validation pass/fail rates
- Memory usage and query performance
- API response times

## Development

### Running Tests

```bash
# Unit tests
./clopus test unit

# Integration tests
./clopus test integration

# E2E tests
./clopus test e2e

# All tests
./clopus test all
```

### Building

```bash
# Build all containers
docker-compose build

# Build specific service
docker-compose build orchestrator
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Troubleshooting

### Common Issues

**Workers not starting**
```bash
# Check worker logs
./clopus logs worker-1

# Verify API key
./clopus login
```

**Memory errors**
```bash
# Reset memory
docker-compose down -v
./clopus start
```

**Validation failures**
```bash
# View validation results
cat data/validation_results.json

# Run validation manually
./clopus validate ./project
```

### Logs

```bash
# All logs
./clopus logs

# Specific service
./clopus logs orchestrator
./clopus logs worker-1
./clopus logs chromadb
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by [Clopus-02](https://denislavgavrilov.com/p/clopus-02-a-24-hour-claude-code-run) by Denislav Gavrilov
- Built with [Claude Code](https://claude.ai/claude-code) by Anthropic
- Uses [Model Context Protocol](https://modelcontextprotocol.io/) for tool integration

---

**CLOPUS v3** - Autonomous development, amplified.
