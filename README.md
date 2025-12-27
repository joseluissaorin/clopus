<p align="center">
  <h1 align="center">CLOPUS v3</h1>
  <p align="center">
    <strong>Autonomous Multi-Agent Claude Code System</strong>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> |
    <a href="#features">Features</a> |
    <a href="#architecture">Architecture</a> |
    <a href="#documentation">Docs</a>
  </p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://github.com/joseluissaorin/clopus"><img src="https://img.shields.io/badge/python-3.11+-green.svg" alt="Python"></a>
  <a href="https://github.com/joseluissaorin/clopus"><img src="https://img.shields.io/badge/docker-required-blue.svg" alt="Docker"></a>
  <a href="https://claude.ai"><img src="https://img.shields.io/badge/powered%20by-Claude-orange.svg" alt="Claude"></a>
</p>

---

**CLOPUS** (Claude-based Locally Orchestrated Production Unified System) is a fully autonomous development system that orchestrates multiple Claude Code instances to build complete software projects with minimal human intervention.

Give it an objective like *"Build a todo app with React and FastAPI"* and watch as 6 specialized AI workers collaborate to design, implement, test, and validate production-ready code.

## Table of Contents

- [Why CLOPUS?](#why-clopus)
- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Architecture](#architecture)
- [Worker Roles](#worker-roles)
- [Designer Agent](#designer-agent)
- [Project Continuity](#project-continuity)
- [Validation Pipeline](#validation-pipeline)
- [Memory System](#memory-system)
- [Self-Generating Ecosystem](#self-generating-ecosystem)
- [MCP Servers](#mcp-servers)
- [Skills](#skills)
- [Templates](#templates)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Why CLOPUS?

Traditional AI coding assistants require constant human guidance. CLOPUS takes a different approach:

| Traditional AI Coding | CLOPUS |
|----------------------|--------|
| Single conversation context | Persistent memory across sessions |
| One task at a time | 6 parallel specialized workers |
| Manual testing | 8-stage automated validation |
| No learning | Learns from every project |
| Basic code generation | Full project scaffolding + deployment |
| Asks for everything | Only asks when genuinely uncertain |
| No design consistency | Designer agent creates unified branding |
| Loses progress on restart | Project continuity system resumes work |

### Key Differentiators

- **True Autonomy**: Confidence-based decision making means CLOPUS only interrupts you when it genuinely needs guidance
- **Self-Improvement**: Automatically extracts patterns, skills, and templates from completed work
- **Production Quality**: 8-stage validation ensures generated code is production-ready
- **Persistent Memory**: ChromaDB-powered semantic memory means CLOPUS remembers solutions and patterns
- **Extensible**: MCP servers, skills, and templates can be added without code changes

## Features

### Multi-Agent Architecture
- **6 Parallel Workers**: Specialized roles (Coder, Tester, Reviewer, Researcher, Debugger, Designer) work concurrently
- **Intelligent Task Distribution**: Orchestrator assigns tasks based on worker specialization and workload
- **File-Based IPC**: Simple, debuggable communication via JSON files
- **Designer Agent**: Creates comprehensive branding and design systems before implementation

### Project Continuity
- **Automatic Resumption**: Incomplete projects are automatically resumed on restart
- **State Tracking**: Every project has a state file tracking progress, validation, and dev server
- **Port Management**: Dynamic port allocation with availability checking
- **PROJECT.md**: Live documentation showing current status, validation results, and running state

### Python Orchestrator
- **Async Everything**: Built on asyncio for maximum concurrency
- **Objective Parsing**: Natural language objectives parsed into structured tasks
- **Confidence Engine**: Learns when to act autonomously vs. ask for help

### Dual Memory System
- **Short-Term (SQLite)**: Current objectives, tasks, worker states, validation results
- **Long-Term (ChromaDB)**: Semantic search over patterns, solutions, errors, and decisions

### Self-Generating Ecosystem
- **Skills**: Automatically discovers and generates reusable skills from patterns
- **MCP Servers**: Generates TypeScript MCP servers when new API access is needed
- **Templates**: Extracts parameterized templates from completed projects

### 8-Stage Validation Pipeline
Every piece of generated code passes through:
1. **Syntax Check** - Language-specific syntax validation
2. **Lint** - ESLint, Pylint, Ruff, and more
3. **Build** - Compilation and build verification
4. **Unit Tests** - Jest, pytest, Go test
5. **Integration Tests** - API and service integration
6. **E2E Tests** - Playwright/Cypress browser tests
7. **Security Scan** - npm audit, pip-audit, pattern detection
8. **Code Review** - Automated review by Reviewer worker

### Browser Automation
- **MCP Server**: Playwright-based automation for reliable web interactions
- **VNC Container**: Chromium with noVNC for visual debugging

### Universal Dev Tools
Pre-installed: Python, Node.js, Go, Rust, PHP, Ruby, cloud CLIs (AWS, GCP, Azure, Vercel, Railway, Fly.io), Docker, kubectl, terraform, and more.

### GitHub Integration
- **Auto-Sync**: Skills, templates, and MCP servers sync to shared repository
- **Project Repos**: Each project gets its own GitHub repository
- **PR Workflow**: Automated PR creation and branch management

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (v2.0+)
- **Git**
- **GitHub CLI** (`gh`) - authenticated
- **Anthropic API key** or **Claude Max/Pro subscription**

### Installation

```bash
# Clone the repository
git clone https://github.com/joseluissaorin/clopus.git
cd clopus

# Run setup (configures environment, builds containers)
./setup.sh

# Start CLOPUS
./clopus start
```

### One-Liner Install

```bash
curl -fsSL https://raw.githubusercontent.com/joseluissaorin/clopus/main/install.sh | bash
```

### First Objective

```bash
# Give CLOPUS its first task
./clopus objective "Build a todo app with React frontend and FastAPI backend"

# Watch progress
./clopus status

# Check if CLOPUS has questions
./clopus questions

# Answer any questions
./clopus answer <question_id> "Your answer here"
```

## Usage

### CLI Commands

```bash
# Lifecycle
./clopus start                  # Start all services
./clopus stop                   # Stop all services
./clopus restart                # Restart services
./clopus status                 # Show system status

# Objectives
./clopus objective "..."        # Submit a new objective
./clopus objectives             # List all objectives
./clopus cancel <id>            # Cancel an objective

# Questions & Answers
./clopus questions              # List pending questions
./clopus answer <id> "..."      # Answer a question

# Workers
./clopus workers                # Show worker status
./clopus worker <id>            # Show specific worker details
./clopus logs <service>         # View service logs

# Skills & Templates
./clopus skills                 # List available skills
./clopus templates              # List available templates
./clopus template use <name> <dest>  # Apply a template

# GitHub
./clopus sync                   # Sync to GitHub
./clopus repos                  # List created repositories

# Validation
./clopus validate <path>        # Run validation on a project

# Configuration
./clopus login                  # Configure authentication
./clopus config                 # View/edit configuration
```

### File-Based Interface

For automation or when CLI isn't available:

```bash
# Submit an objective
echo "Build a REST API for user management" > ipc/interface/objective.txt

# Check for questions
cat ipc/interface/questions.json

# Submit answers
echo '{"question_id": "q123", "answer": "Use JWT for auth"}' > ipc/interface/answer.txt

# View current status
cat ipc/interface/status.json
```

### Example Session

```bash
$ ./clopus start
Starting CLOPUS v3...
  [OK] ChromaDB
  [OK] SQLite
  [OK] Orchestrator
  [OK] Worker 1 (Coder)
  [OK] Worker 2 (Tester)
  [OK] Worker 3 (Reviewer)
  [OK] Worker 4 (Researcher)
  [OK] Worker 5 (Debugger)
  [OK] Worker 6 (Designer)
Scanning for incomplete projects...
  Found 1 incomplete project(s)
  [RESUME] todo-app (validation: 4/8, e2e: pending)
System ready.

$ ./clopus objective "Build a blog with Next.js, markdown support, and dark mode"
Objective submitted: obj_a1b2c3d4
Parsing objective...
Detected: Next.js project with MDX support
Planning 13 tasks across 6 workers...
Started.

$ ./clopus status
Objective: Build a blog with Next.js...
Progress: 7/13 tasks (54%)
Workers:
  - Coder: implementing dark mode toggle
  - Tester: writing component tests
  - Reviewer: reviewing navigation component
  - Researcher: idle
  - Debugger: idle
  - Designer: completed design system
Validation: 6 passed, 0 failed

$ ./clopus questions
No pending questions.

# Later...
$ ./clopus status
Objective: Build a blog with Next.js...
Progress: 12/12 tasks (100%)
Validation: All 8 stages passed
Repository: https://github.com/joseluissaorin/blog-nextjs

Done! Project available at: /workspace/projects/blog-nextjs
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
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │  Knowledge  │ │  Service    │ │ Capability  │               │
│  │    Base     │ │   Manager   │ │  Installer  │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   Worker 1    │       │   Worker 2    │       │   Worker 3    │
│    (Coder)    │       │   (Tester)    │       │  (Reviewer)   │
│  Claude Code  │       │  Claude Code  │       │  Claude Code  │
└───────────────┘       └───────────────┘       └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   Worker 4    │       │   Worker 5    │       │   Worker 6    │
│ (Researcher)  │       │  (Debugger)   │       │  (Designer)   │
│  Claude Code  │       │  Claude Code  │       │  Claude Code  │
└───────────────┘       └───────────────┘       └───────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│    SQLite     │       │   ChromaDB    │       │  MCP Servers  │
│ (Short-term)  │       │ (Long-term)   │       │  (10+ tools)  │
└───────────────┘       └───────────────┘       └───────────────┘
```

### Service Tiers

**Tier 1 (Always Running)**:
- Orchestrator
- 6 Claude Code Workers (Coder, Tester, Reviewer, Researcher, Debugger, Designer)
- SQLite
- ChromaDB

**Tier 2 (On-Demand)**:
- PostgreSQL
- Redis
- MinIO (S3)
- Prometheus
- Grafana
- Browser (VNC)

The Service Manager automatically provisions Tier 2 services when a project needs them.

## Worker Roles

Each worker runs a full Claude Code instance with role-specific system prompts and skills:

| Worker | Role | Specialization | Skills |
|--------|------|----------------|--------|
| Worker 1 | **Coder** | Primary development, feature implementation | react-typescript, python-fastapi, nextjs-fullstack |
| Worker 2 | **Tester** | Write and run all test types | playwright-e2e, jest-unit, pytest-python |
| Worker 3 | **Reviewer** | Code review, security, best practices | security-audit, code-review |
| Worker 4 | **Researcher** | Documentation, API research, solutions | web-search, documentation-reader |
| Worker 5 | **Debugger** | Bug fixing, performance, troubleshooting | debugging, performance-profiling |
| Worker 6 | **Designer** | Branding, design systems, visual consistency | design-system, ui-ux |

Workers communicate via file-based IPC:
- `ipc/tasks/{worker_id}/pending.json` - Tasks for worker
- `ipc/tasks/{worker_id}/status.json` - Worker status
- `ipc/tasks/{worker_id}/result.json` - Task results

## Designer Agent

The Designer is a specialized worker that creates comprehensive branding and design documentation before implementation begins.

### Responsibilities

1. **Early in Project**: Creates complete design system after project setup
2. **For Existing Projects**: Analyzes and documents existing branding
3. **Ongoing Support**: Other workers can request design guidance
4. **Screenshot Review**: Reviews E2E test screenshots for visual quality

### Design System Output

The Designer creates `.clopus/design/DESIGN_SYSTEM.md` containing:

- **Brand Identity**: Project name, tagline, personality
- **Color Palette**: Primary, secondary, accent colors (with dark mode)
- **Typography**: Font families, type scale, weights
- **Spacing System**: Consistent spacing scale (4px base)
- **Component Styles**: Buttons, inputs, cards, navigation
- **Animation Guidelines**: Transition timing and motion principles

### Workflow

```
1. Setup task completes
2. DESIGNER creates design system ← Runs early (priority 9)
3. CODER follows design system when implementing
4. TESTER takes screenshots
5. DESIGNER reviews screenshots (optional)
```

## Project Continuity

CLOPUS automatically resumes incomplete projects across restarts.

### How It Works

```
CLOPUS STARTS
    │
    ▼
┌─────────────────────────────────┐
│  SCAN /workspace FOR PROJECTS   │
│  Look for .clopus/project_state │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  FOR EACH INCOMPLETE PROJECT:   │
│  1. Load state file             │
│  2. Check dev server status     │
│  3. Detect port conflicts       │
│  4. Create resumption tasks     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  QUEUE RESUMPTION TASKS         │
│  - Fix port allocation          │
│  - Run pending validation       │
│  - Run E2E tests                │
│  - Generate PROJECT.md          │
└─────────────────────────────────┘
```

### Project State

Each project has `.clopus/project_state.json`:

```json
{
  "project_name": "todo-app",
  "status": "in_progress",
  "stages": {
    "setup": {"status": "completed"},
    "design": {"status": "completed"},
    "implementation": {"status": "completed"},
    "validation": {"status": "partial"},
    "e2e_testing": {"status": "pending"},
    "documentation": {"status": "pending"}
  },
  "validation": {
    "stages_passed": ["syntax", "lint", "build", "unit_tests"],
    "stages_pending": ["e2e_tests", "security", "review"]
  },
  "dev_server": {
    "running": true,
    "port": 3142,
    "url": "http://0.0.0.0:3142"
  }
}
```

### Dynamic Port Allocation

- **Port Range**: 3100-3199 for CLOPUS projects
- **Availability Check**: Tests if port is actually free before allocating
- **Process Detection**: Finds and can kill processes on conflicting ports
- **Registry**: Remembers port assignments across restarts

### PROJECT.md

Every project gets auto-generated documentation with live state:

```markdown
# Todo App

> Status: **IN_PROGRESS** | Validation: 4/8 passed

## Stage Progress
| Stage | Status |
|-------|--------|
| Setup | [x] Completed |
| Design | [x] Completed |
| Implementation | [x] Completed |
| Validation | [~] Partial |
| E2E Testing | [ ] Pending |

## Dev Server
- **Port:** 3142
- **URL:** http://localhost:3142
```

## Validation Pipeline

All generated code must pass 8 validation stages:

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Syntax  │ → │   Lint   │ → │  Build   │ → │  Unit    │
│  Check   │   │          │   │          │   │  Tests   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                   │
                                                   ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│   Code   │ ← │ Security │ ← │   E2E    │ ← │  Integ   │
│  Review  │   │   Scan   │   │  Tests   │   │  Tests   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### Stage Details

| Stage | Tools | What It Checks |
|-------|-------|----------------|
| Syntax | Language parsers | Valid syntax for all files |
| Lint | ESLint, Pylint, Ruff | Code style, common errors |
| Build | npm, pip, cargo, go | Project compiles/builds |
| Unit Tests | Jest, pytest, go test | Individual function behavior |
| Integration Tests | Supertest, pytest | API and service integration |
| E2E Tests | Playwright, Cypress | Full user flows in browser |
| Security | npm audit, pip-audit, Semgrep | Vulnerabilities, secrets |
| Code Review | Reviewer worker | Architecture, best practices |

### Configuration

```yaml
validation:
  strict_mode: true          # All stages must pass
  required_stages:           # Must pass
    - syntax
    - lint
    - build
    - unit_tests
  optional_stages:           # Can fail without blocking
    - integration_tests
    - e2e_tests
    - security
    - review
  coverage_threshold: 80     # Minimum test coverage %
```

## Memory System

### Short-Term Memory (SQLite)

Stores transient state:
- Current objectives and task queues
- Worker assignments and status
- Validation results
- Active session data

### Long-Term Memory (ChromaDB)

Semantic vector database for:
- **Patterns**: Reusable code patterns with embeddings
- **Solutions**: Problem-solution pairs for reference
- **Mistakes**: Anti-patterns to avoid
- **Decisions**: Past decisions with outcomes for learning

### How It Works

```python
# Storing a pattern
await memory.long_term.store(
    memory_type="pattern",
    content="React hook for API calls with loading/error states",
    metadata={"category": "react", "tags": ["hooks", "api"]}
)

# Semantic search
results = await memory.long_term.search(
    query="how to handle API errors in React",
    n_results=5
)
```

## Self-Generating Ecosystem

CLOPUS learns and improves from every project:

### Skills Generation

When CLOPUS notices recurring patterns:
1. Identifies pattern across multiple tasks
2. Abstracts into reusable skill
3. Validates skill works in isolation
4. Syncs to GitHub repository

### MCP Server Generation

When CLOPUS needs a new API:
1. Searches for existing MCP servers
2. If none found, researches API documentation
3. Generates TypeScript MCP server
4. Tests with sample requests
5. Syncs to GitHub

### Template Extraction

After completing a project:
1. Analyzes project structure
2. Identifies project-specific vs. reusable code
3. Replaces specifics with `{{PARAMETERS}}`
4. Creates template.json manifest
5. Validates template can regenerate
6. Syncs to GitHub

## MCP Servers

### Core Servers

| Server | Description | Key Tools |
|--------|-------------|-----------|
| **browser** | Playwright automation | navigate, screenshot, click, fill, evaluate |
| **memory** | Memory system access | store, retrieve, search, forget |
| **validation** | Run validation pipeline | validate, get_results, get_coverage |
| **email-resend** | Email via Resend API | send_email, send_template |
| **email-smtp** | Email via SMTP | send_email, send_with_attachment |
| **database-postgres** | PostgreSQL operations | query, execute, transaction |
| **database-redis** | Redis operations | get, set, delete, publish, subscribe |
| **storage-s3** | S3/MinIO storage | upload, download, list, delete |
| **github** | GitHub API | create_repo, create_pr, create_issue |
| **search** | Web search | search, fetch_page |
| **calendar** | Google Calendar | list_events, create_event, find_free_time |
| **notifications** | Push notifications | send_firebase, send_onesignal |

### Adding Custom MCP Servers

1. Create server in `mcp-servers/custom/your-server/`
2. Add to `workers/.mcp.json`
3. Rebuild workers: `docker-compose build worker`

## Skills

Skills are Claude-invokable capabilities defined in SKILL.md files:

```markdown
---
name: react-typescript
description: Build React applications with TypeScript, Vite, or Next.js. Use when creating React components, implementing hooks, or building frontend UIs.
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
  - component
---

# React TypeScript Development

## Context
You are an expert React developer using TypeScript...

## Instructions
1. Use functional components with hooks
2. Define proper TypeScript interfaces for all props
3. Implement error boundaries for resilience
...
```

### Core Skills

| Category | Skills |
|----------|--------|
| Development | react-typescript, nextjs-fullstack, python-fastapi, expo-mobile |
| Testing | playwright-e2e, jest-unit, pytest-python |
| Data | web-scraping, data-analysis |
| DevOps | docker-containerization, ci-cd-github-actions |
| Research | web-search, documentation-reader |
| Media | ffmpeg-video, imagemagick-images, whisper-transcription |

## Templates

Templates are parameterized project scaffolds:

```json
{
  "name": "saas-starter",
  "description": "Full-stack SaaS with Next.js, Prisma, Stripe",
  "version": "1.0.0",
  "type": "nextjs",
  "parameters": {
    "PROJECT_NAME": {"required": true, "default": "my-saas"},
    "DATABASE_URL": {"required": true},
    "STRIPE_KEY": {"required": false}
  },
  "technologies": ["nextjs", "prisma", "stripe", "tailwindcss"],
  "hooks": {
    "post-create": "npm install && prisma generate"
  }
}
```

### Using Templates

```bash
# List available templates
./clopus templates

# Apply a template
./clopus template use saas-starter my-new-app

# With parameters
./clopus template use saas-starter my-app \
  --param DATABASE_URL="postgresql://..." \
  --param STRIPE_KEY="sk_..."
```

## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
# Authentication (choose one)
AUTH_MODE=oauth                    # oauth or api
CLAUDE_OAUTH_TOKEN=...             # For oauth mode
ANTHROPIC_API_KEY=sk-ant-...       # For api mode

# GitHub
GITHUB_TOKEN=ghp_...

# Workers
WORKERS=6
CLAUDE_MODEL=claude-sonnet-4-20250514

# External Services (optional)
RESEND_API_KEY=re_...
STRIPE_SECRET_KEY=sk_...
OPENAI_API_KEY=sk-...

# Google Calendar (optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...

# Notifications (optional)
FIREBASE_SERVICE_ACCOUNT=...
ONESIGNAL_APP_ID=...
```

### config.yaml

```yaml
workers:
  count: 6
  roles: [coder, tester, reviewer, researcher, debugger, designer]
  heartbeat_interval: 30
  task_timeout: 3600

memory:
  sqlite_path: ./data/clopus.db
  chromadb_path: ./data/chromadb
  embedding_model: all-MiniLM-L6-v2

validation:
  strict_mode: true
  coverage_threshold: 80

confidence:
  threshold: 0.7
  learning_rate: 0.1

github:
  auto_sync: true
  default_visibility: private
```

## Monitoring

CLOPUS includes Prometheus and Grafana:

```bash
# Enable monitoring
./clopus start --with-monitoring

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

### Metrics

- Worker status and task throughput
- Validation pass/fail rates by stage
- Memory query latency
- Confidence scores over time
- API token usage

## API Reference

### Orchestrator API

The orchestrator exposes an internal API for programmatic access:

```python
from clopus import ClopusClient

client = ClopusClient()

# Submit objective
obj = await client.submit_objective("Build a todo app")

# Get status
status = await client.get_status(obj.id)

# Answer question
await client.answer_question(question_id, "Use React")

# Get results
results = await client.get_results(obj.id)
```

### Webhook Interface

```bash
# Start with webhook server
./clopus start --webhook-port 8080
```

```bash
# Submit objective via webhook
curl -X POST http://localhost:8080/objective \
  -H "Content-Type: application/json" \
  -d '{"objective": "Build a REST API"}'

# Get status
curl http://localhost:8080/status/{objective_id}
```

## Troubleshooting

### Common Issues

**Workers not starting**
```bash
./clopus logs worker-1
./clopus login  # Reconfigure auth
```

**Memory errors**
```bash
docker-compose down -v  # Reset volumes
./clopus start
```

**Validation failures**
```bash
cat data/validation_results.json
./clopus validate ./project --verbose
```

**MCP server issues**
```bash
./clopus logs mcp-servers
docker-compose build mcp-servers
```

### Debug Mode

```bash
LOG_LEVEL=DEBUG ./clopus start
```

### Reset Everything

```bash
./clopus stop
docker-compose down -v
rm -rf data/
./clopus start
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone
git clone https://github.com/joseluissaorin/clopus.git
cd clopus

# Install dev dependencies
pip install -r requirements-dev.txt
npm install

# Run tests
./clopus test all

# Build containers
docker-compose build
```

### Areas for Contribution

- New MCP servers for APIs
- Additional skills
- Project templates
- Documentation improvements
- Bug fixes

## Roadmap

### v3.1 (Next)
- [ ] Web UI dashboard
- [ ] Multi-project management
- [ ] Cost tracking and budgets
- [ ] Custom worker roles

### v3.2
- [ ] Cloud deployment (AWS, GCP)
- [ ] Team collaboration features
- [ ] Webhook notifications
- [ ] Plugin system

### Future
- [ ] Voice interface
- [ ] Mobile app
- [ ] Self-hosted marketplace for skills/templates

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by [Clopus-02](https://denislavgavrilov.com/p/clopus-02-a-24-hour-claude-code-run) by Denislav Gavrilov
- Built with [Claude Code](https://claude.ai/code) by Anthropic
- Uses [Model Context Protocol](https://modelcontextprotocol.io/) for tool integration
- Vector search powered by [ChromaDB](https://www.trychroma.com/)

---

<p align="center">
  <strong>CLOPUS v3</strong> - Autonomous development, amplified.
</p>

<p align="center">
  <a href="https://github.com/joseluissaorin/clopus/issues">Report Bug</a> |
  <a href="https://github.com/joseluissaorin/clopus/issues">Request Feature</a>
</p>
