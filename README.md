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

Give it an objective like *"Build a todo app with React and FastAPI"* and watch as 11 specialized AI workers collaborate to design, implement, test, and validate production-ready code.

## Table of Contents

- [Why CLOPUS?](#why-clopus)
- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Terminal User Interface (TUI)](#terminal-user-interface-tui)
- [Architecture](#architecture)
- [Worker Roles](#worker-roles)
- [Designer Agent](#designer-agent)
- [Project Continuity](#project-continuity)
- [Multi-Project Support](#multi-project-support)
- [Heartbeat Agent](#heartbeat-agent)
- [Verificator Worker](#verificator-worker)
- [Inter-Worker Collaboration](#inter-worker-collaboration)
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
| One task at a time | 11 parallel specialized workers |
| Manual testing | 8-stage automated validation |
| No learning | Learns from every project |
| Basic code generation | Full project scaffolding + deployment |
| Asks for everything | Only asks when genuinely uncertain |
| No design consistency | Designer agent creates unified branding |
| Loses progress on restart | Project continuity system resumes work |
| No verification | Verificator ensures tasks actually complete |
| CLI-only interaction | Rich Terminal UI with 10 screens |

### Key Differentiators

- **True Autonomy**: Confidence-based decision making means CLOPUS only interrupts you when it genuinely needs guidance
- **Self-Improvement**: Automatically extracts patterns, skills, and templates from completed work
- **Production Quality**: 8-stage validation ensures generated code is production-ready
- **Persistent Memory**: ChromaDB-powered semantic memory means CLOPUS remembers solutions and patterns
- **Extensible**: MCP servers, skills, and templates can be added without code changes
- **Rich Terminal UI**: Monitor workers, tasks, and projects in real-time with a 10-screen TUI

## Features

### Multi-Agent Architecture
- **11 Parallel Workers**: 6 core roles (Coder, Tester, Reviewer, Researcher, Debugger, Designer) + 2 browser workers + 3 reserved
- **Browser Workers**: Browser-Headless (Worker 9) and Browser-Chrome (Worker 10) are now assignable for visual testing tasks
- **Reserved Workers**: Heartbeat, Verificator, Services (not assignable for regular tasks)
- **Inter-Worker Collaboration**: Workers can communicate, ask each other for help, and share knowledge
- **Intelligent Task Distribution**: Orchestrator assigns tasks based on worker specialization and workload
- **File-Based IPC**: Simple, debuggable communication via JSON files with acknowledgment handshake
- **Designer Agent**: Creates comprehensive branding and design systems before implementation
- **Verificator Worker**: Uses Claude's intelligence to verify task completions and detect semantic duplicates
- **Browser Workers**: Playwright (headless) and Chrome+VNC (visual) for web automation
- **Services Worker**: Email, calendar, and external API integrations via MCP
- **Context Injection**: Pre-task memory search injects relevant patterns and solutions

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
- **Worker 9 (Browser-Headless)**: Playwright-based automation for fast, headless web tasks
- **Worker 10 (Browser-Chrome)**: Chrome with VNC for visual debugging and Claude extension support
  - **VNC Access**: noVNC at http://localhost:6280, VNC client at localhost:5920
  - **Auto-Start**: Chrome launches automatically on container boot
- **MCP Servers**: Playwright MCP, Gmail MCP, Firecrawl MCP for comprehensive web/email automation
- **Task Assignment**: AI planner can assign tasks directly to browser workers for visual testing

### Permission System (v3.3)
- **Blocklist Approach**: All Bash commands allowed except dangerous ones
- **Blocked Commands**: `rm -rf /`, `sudo`, `shutdown`, `reboot`, `mkfs`, `dd if=/dev/zero`
- **Role-Specific Settings**: Each worker role has its own settings file (settings.coder.json, etc.)
- **Docker Isolation**: Container boundaries provide additional security layer

### Terminal User Interface (TUI)
- **10 Screens**: Dashboard, Workers, Projects, Tasks, Logs, Objectives, Memory, Questions, Config, Browser
- **Real-Time Updates**: WebSocket connection for live task and worker status
- **Worker Control**: Restart, stop, and view logs for any worker
- **Task Management**: Filter, retry, cancel, and adjust priority
- **Question Answering**: Quick-answer buttons for common responses
- **Light/Dark Themes**: Toggle with Ctrl+T

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
./clopus tui                    # Launch Terminal UI (light theme, WebSocket)
./clopus tui --dark             # Launch TUI with dark theme

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

## Terminal User Interface (TUI)

CLOPUS includes a rich terminal-based user interface built with [Textual](https://textual.textualize.io/) for real-time monitoring and control.

### Starting the TUI

```bash
# Start with defaults (light theme, WebSocket enabled)
./clopus tui

# Start with dark theme
./clopus tui --dark

# Start without WebSocket (uses mock data for testing)
./clopus tui --no-websocket
```

### TUI Screens

| Screen | Key | Description |
|--------|-----|-------------|
| **Dashboard** | `d` | System overview with stats, progress, and recent activity |
| **Workers** | `w` | Worker status, task assignments, logs, restart/stop controls |
| **Projects** | `p` | Project list, validation status, dev server controls |
| **Tasks** | `t` | Task queue with filtering, retry/cancel actions, priority adjustment |
| **Logs** | `l` | Real-time logs from orchestrator and all workers |
| **Objectives** | `o` | Submit new objectives, view progress, cancel objectives |
| **Memory** | `m` | Memory system browser, search, cleanup tools |
| **Questions** | `q` | Answer pending questions with quick-answer buttons |
| **Config** | `c` | Edit system configuration (confidence, heartbeat, validation) |
| **Browser** | `b` | Browser worker controls, VNC access, screenshot capture |

### Keyboard Shortcuts

```
Navigation:
  d     Dashboard          w     Workers           p     Projects
  t     Tasks              l     Logs              o     Objectives
  m     Memory             q     Questions         c     Config
  b     Browser

Actions:
  r         Refresh current view
  Ctrl+T    Toggle dark/light theme
  Ctrl+Q    Quit
  ?         Show help

Screen-specific:
  Enter     Select/Confirm
  Escape    Go back / Cancel
  Tab       Next field
  /         Search (where available)
```

### Dashboard

The dashboard provides a real-time overview:

```
┌─────────────────────────────────────────────────────────────────┐
│ System Health          │ Statistics                             │
│ ● Workers: 10/11       │ Total Tasks:    264                    │
│ ● Memory: OK           │ Completed:      30                     │
│ ● Database: OK         │ Active Workers: 7/11                   │
├─────────────────────────────────────────────────────────────────┤
│ Task Progress                                                    │
│ [████████████░░░░░░░░░░░░░] 30/264 (11%)                       │
│ [New Objective] [View Tasks] [View Logs]                        │
├─────────────────────────────────────────────────────────────────┤
│ Activity              │ Recent Activity                         │
│ ▁▂▃▅▇▆▅▄▃▂▁          │ ✓ Initialize FastAPI project            │
│ Worker Busy: ▂▃▄▅▆▇   │ ✗ Clean up removed filter components    │
│                       │ ● Implement feature X                    │
└─────────────────────────────────────────────────────────────────┘
```

### Workers Screen

Monitor and control all 11 workers:

```
┌─────────────────────────────────────────────────────────────────┐
│ Workers                         │ Worker Details                 │
│ ID  Role             Status     │ Worker 1                       │
│ ─────────────────────────────── │ Role: CODER                    │
│  1  CODER            BUSY       │ Status: BUSY                   │
│  2  TESTER           BUSY       │ Model: claude-sonnet-4         │
│  3  REVIEWER         IDLE       │ Task: 8f8a4c95...              │
│  4  RESEARCHER       BUSY       │ Started: 2025-12-28T22:00:00   │
│  5  DEBUGGER         BUSY       │                                │
│  6  DESIGNER         BUSY       │ [Restart] [Stop] [View Logs]   │
│  7  HEARTBEAT        IDLE       ├────────────────────────────────│
│  8  VERIFICATOR      BUSY       │ Recent Logs:                   │
│  9  BROWSER-HEADLESS BUSY       │ [22:15:01] Processing task...  │
│ 10  BROWSER-CHROME   IDLE       │ [22:15:05] Claude Code output  │
│ 11  SERVICES         IDLE       │ [22:15:10] Task completed      │
└─────────────────────────────────────────────────────────────────┘
```

### Real-Time Updates

The TUI connects to the orchestrator via WebSocket (port 8765) for real-time updates:

- **Task Events**: Completion, failure, assignment notifications
- **Worker Status**: Busy/idle state changes
- **Questions**: Desktop notifications when questions are pending
- **Validation Results**: Live validation stage progress

### Data Sources

| Source | Data |
|--------|------|
| SQLite Database | Tasks, objectives, projects, questions, activity log |
| IPC Files | Worker status, task assignments, session info |
| Docker | Container status, logs |
| WebSocket | Real-time events from orchestrator |

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
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌────────────────────────────┐   ┌────────────────────────────┐
│       Worker 7             │   │       Worker 8             │
│   (Heartbeat - Reserved)   │   │  (Verificator - Reserved)  │
│    Completion Guardian     │   │   Intelligent Verification │
└────────────────────────────┘   └────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌────────────────────────────┐   ┌────────────────────────────┐   ┌────────────────────────────┐
│       Worker 9             │   │       Worker 10            │   │       Worker 11            │
│  (Browser-Headless)        │   │   (Browser-Chrome)         │   │      (Services)            │
│   Playwright automation    │   │   Chrome + VNC (visual)    │   │   Email/API integrations   │
└────────────────────────────┘   └────────────────────────────┘   └────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│    SQLite     │       │   ChromaDB    │       │  MCP Servers  │
│ (Short-term)  │       │ (Long-term)   │       │  (20+ tools)  │
└───────────────┘       └───────────────┘       └───────────────┘
```

### Service Tiers

**Tier 1 (Always Running)**:
- Orchestrator
- 6 Core Claude Code Workers (Coder, Tester, Reviewer, Researcher, Debugger, Designer)
- 2 Browser Workers (Browser-Headless, Browser-Chrome) - assignable for visual testing
- 3 Reserved Workers (Heartbeat, Verificator, Services)
- SQLite
- ChromaDB

**Tier 2 (On-Demand)**:
- PostgreSQL
- Redis
- MinIO (S3)
- Prometheus
- Grafana

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
| Worker 7 | **Heartbeat** *(reserved)* | Gap analysis, completion verification | objective-analysis, integration-testing |
| Worker 8 | **Verificator** *(reserved)* | Intelligent verification, deduplication | artifact-verification, semantic-analysis |
| Worker 9 | **Browser-Headless** | Playwright automation, web scraping, headless testing | playwright-mcp, web-scraping |
| Worker 10 | **Browser-Chrome** | Chrome + VNC, visual debugging, interactive testing | chrome-automation, vnc-access |
| Worker 11 | **Services** *(reserved)* | Email, calendar, API integrations | gmail-mcp, firecrawl-mcp, calendar-mcp |

Workers communicate via file-based IPC:
- `ipc/tasks/{worker_id}/pending.json` - Tasks for worker
- `ipc/tasks/{worker_id}/status.json` - Worker status
- `ipc/tasks/{worker_id}/result.json` - Task results
- `ipc/collaboration/requests/` - Inter-worker help requests
- `ipc/collaboration/responses/` - Help request responses

All workers can use the **Collaboration MCP** to ask other workers for help, request browser automation, and share learnings.

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

## Multi-Project Support

CLOPUS can build multiple related projects in parallel with shared context.

### Cross-Project Dependencies

When building full-stack applications (e.g., API + Frontend), CLOPUS:

1. **Links Projects**: Establishes relationships between projects (e.g., `nexus-web` depends on `nexus-api`)
2. **Shares Context**: Projects can share artifacts like OpenAPI specs, design tokens, and configuration
3. **Parallel Development**: Both projects build simultaneously where possible
4. **Smart Routing**: Workers receive the correct project context via task descriptions

### Shared Context Directory

Projects share data through `/workspace/.shared/`:

```
/workspace/.shared/
├── index.json              # Project registry and links
├── nexus-api/
│   └── api-info.json       # API endpoint information
└── nexus-web/
    └── design-tokens.json  # Shared design system
```

### Project Links

```json
{
  "links": [
    {
      "source": "nexus-api",
      "target": "nexus-web",
      "type": "api_consumer",
      "artifacts": ["api-info.json"]
    }
  ]
}
```

### Example: Full-Stack Application

```bash
# Submit API backend objective
./clopus objective "Build NEXUS API with FastAPI - knowledge graph backend"

# Submit frontend objective (references API)
./clopus objective "Build NEXUS Web frontend with React - connects to nexus-api"
```

## Heartbeat Agent

The Heartbeat Agent (Completion Guardian) is a periodic supervisor that ensures projects actually meet their objectives. It's the "little voice in the head" asking: **"Did we actually build what we promised?"**

### Why It Exists

Without the Heartbeat Agent, CLOPUS could mark a project "complete" even if:
- API endpoints were scaffolded but not implemented
- Tests pass but mock everything
- Frontend and backend don't actually work together
- Only 3 of 8 validation stages ran

### How It Works

Every 5 minutes, the Heartbeat Agent:

1. **Reads the original objective** and extracts concrete requirements using Claude
2. **Assesses current project state** - files, endpoints, tests, validation results
3. **Compares reality vs requirements** - "objective says edges, but no `/edges` endpoint exists"
4. **Spawns tasks to fill gaps** - creates specific remediation tasks
5. **Runs integration tests** - for multi-project, starts services and tests real interactions
6. **Enforces validation** - won't approve until all 8 stages pass

### Completion Gate

A project cannot be marked complete until:

- ✅ All 8 validation stages pass (syntax, lint, build, unit_tests, integration_tests, e2e_tests, security, review)
- ✅ No failed tasks remain
- ✅ All requirements from objective are met (verified by Claude)
- ✅ Integration tests pass (for multi-project objectives)

### Configuration

```yaml
# config.yaml
heartbeat:
  enabled: true
  interval_seconds: 300  # 5 minutes
  use_claude_analysis: true
  completion_gate:
    require_all_validation_stages: true
    require_integration_tests: true
    allowed_failed_tasks: 0
```

## Verificator Worker

The Verificator (Worker 8) is a dedicated Claude Code instance that uses AI intelligence to replace regex/heuristic-based approaches throughout CLOPUS.

### Why It Exists

Before the Verificator, CLOPUS used regex patterns to:
- Infer expected artifacts from task titles (fragile)
- Detect duplicate tasks via word overlap (missed semantic duplicates)
- Match objectives to projects via keyword matching (inaccurate)

**The Problem**: Tasks could be marked "completed" without actually creating their files, and deduplication would block re-creation. This caused gaps like missing `edges.py` despite "Create Edge endpoints" being marked complete.

**The Solution**: Use Claude's intelligence to understand task semantics rather than relying on pattern matching.

### Task Types

| Task Type | Description |
|-----------|-------------|
| **SPECIFY_ARTIFACTS** | Determines what files/endpoints a task should create |
| **VERIFY_COMPLETION** | Verifies if a completed task actually created its artifacts |
| **CHECK_DUPLICATE** | Detects semantically duplicate tasks (not just word matching) |
| **MATCH_PROJECT** | Matches objectives to correct projects using content analysis |
| **AUDIT_COMPLETED** | Retroactively audits old completed tasks for missing artifacts |
| **SEMANTIC_CHECK** | Checks if task output matches requirements semantically |

### Integration Points

1. **Task Assignment**: Before a task is dispatched, Verificator specifies expected artifacts
2. **Task Completion**: After worker reports success, Verificator verifies artifacts exist
3. **Heartbeat Cycle**: Retroactively audits unverified completed tasks
4. **Task Spawning**: Uses semantic deduplication to prevent true duplicates while allowing re-attempts of failed work

### Backwards Compatibility

The Verificator gracefully handles existing tasks:
- Tasks without `expected_artifacts` are marked as verified (no artifacts to check)
- All verification methods have regex-based fallbacks when Verificator is unavailable
- Database migrations automatically add new columns to existing databases
- Existing completed tasks are retroactively audited during heartbeat cycles

## Inter-Worker Collaboration

CLOPUS v3.1 introduces a comprehensive inter-worker collaboration system that enables workers to communicate with each other, request browser automation, and share knowledge through long-term memory.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           COLLABORATION SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐                │
│  │   Worker 1   │────▶│  Collaboration   │────▶│   Worker 6   │                │
│  │   (Coder)    │◀────│   MCP Server     │◀────│  (Designer)  │                │
│  └──────────────┘     └──────────────────┘     └──────────────┘                │
│         │                      │                      │                         │
│         │              ┌───────┴───────┐              │                         │
│         │              ▼               ▼              │                         │
│         │      /collaboration/  /collaboration/       │                         │
│         │        requests/        responses/          │                         │
│         │              │               │              │                         │
│         │              └───────┬───────┘              │                         │
│         │                      ▼                      │                         │
│         │         ┌──────────────────────┐            │                         │
│         │         │    Orchestrator      │            │                         │
│         │         │ CollaborationManager │            │                         │
│         │         │   MessageRouter      │            │                         │
│         │         └──────────────────────┘            │                         │
│         │                      │                      │                         │
│         └──────────────────────┼──────────────────────┘                         │
│                                ▼                                                 │
│                    ┌──────────────────────┐                                     │
│                    │  Long-Term Memory    │                                     │
│                    │    (ChromaDB)        │                                     │
│                    │  Context Injection   │                                     │
│                    └──────────────────────┘                                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Collaboration MCP Server

Workers have access to a dedicated `collaboration` MCP server that provides 9 tools for inter-worker communication:

| Tool | Description | Sync |
|------|-------------|------|
| `ask_worker` | Ask another worker for help and wait for response | Yes |
| `spawn_subtask` | Create a task for another worker | Optional |
| `request_browser_action` | Request ANY browser automation (natural language) | Yes |
| `run_e2e_test` | Run E2E test scenario with assertions | Yes |
| `capture_screenshot` | Capture screenshot of page/element | Yes |
| `share_learning` | Share discovery with other workers via memory | No |
| `find_relevant_context` | Search memory for relevant context | Yes |
| `get_design_system` | Get project's design system | Yes |
| `report_issue` | Report bug for debugger to investigate | No |

### Communication Flow

When a worker needs help from another worker:

```
1. Worker (Coder) calls ask_worker("designer", "What color for buttons?")
       │
       ▼
2. Collaboration MCP writes request to /ipc/collaboration/requests/req_123.json
       │
       ▼
3. Orchestrator detects new request (500ms polling)
       │
       ▼
4. MessageRouter creates high-priority task for Designer worker
       │
       ▼
5. Designer receives task, completes it, returns response
       │
       ▼
6. Orchestrator writes response to /ipc/collaboration/responses/req_123.json
       │
       ▼
7. Collaboration MCP detects response, returns to waiting Coder
```

### Worker-to-Worker Examples

**Coder asking Designer for color guidance:**
```javascript
ask_worker("designer", "What primary color should I use for action buttons?")
// Response: "Use #3B82F6 (blue-500) for primary actions, matching the design system"
```

**Tester requesting E2E browser automation:**
```javascript
run_e2e_test({
  scenario: "User registration and login flow",
  base_url: "http://localhost:3142",
  assertions: [
    "Registration success message appears",
    "User is redirected to dashboard",
    "Username is displayed in header"
  ]
})
// Browser worker executes full flow, returns screenshots and results
```

**Reviewer reporting bugs to Debugger:**
```javascript
report_issue({
  title: "Null pointer in UserService",
  description: "getUserById doesn't check for null before accessing properties",
  file_path: "src/services/UserService.ts",
  severity: "high"
})
```

**Researcher sharing API discoveries:**
```javascript
share_learning({
  type: "api_endpoint",
  content: "Stripe webhooks require signature verification using stripe.webhooks.constructEvent()"
})
```

### Browser Automation

Workers can request full browser automation from browser workers (9-10):

```javascript
// Natural language browser automation
request_browser_action("Test the checkout flow with an invalid credit card")

// Structured E2E test
run_e2e_test({
  scenario: "Checkout flow validation",
  steps: [
    "Navigate to /cart",
    "Click checkout button",
    "Fill invalid card number",
    "Verify error message appears"
  ],
  assertions: ["Error message shows 'Invalid card number'"]
})

// Screenshot capture
capture_screenshot("http://localhost:3142/dashboard")
```

Browser workers are full Claude Code instances that translate natural language requests into Playwright MCP actions.

### Memory Integration

#### Pre-Task Context Injection

Before dispatching any task, the orchestrator's `ContextInjector`:
1. Searches long-term memory for relevant patterns/solutions
2. Gets shared context from other workers
3. Loads design system if applicable
4. Injects context into task prompt

#### Post-Task Learning Extraction

After task completion:
1. Extracts patterns from task output
2. Stores learnings in long-term memory with role tags
3. Updates shared cache for quick access

#### Role-Filtered Queries

Workers can search memory filtered by role:
```python
# Search for patterns discovered by designers
results = await memory.search_for_role(
    query="button styling",
    role="designer",
    limit=5
)
```

### IPC Structure

```
/app/ipc/
├── tasks/{worker_id}/          # Existing task dispatch
│   ├── pending.json
│   ├── result.json
│   ├── status.json
│   └── ack.json
│
├── collaboration/              # Inter-worker communication
│   ├── requests/               # Help requests awaiting response
│   │   └── {request_id}.json
│   ├── responses/              # Completed responses
│   │   └── {request_id}.json
│   ├── events/                 # Async events (spawn_subtask, etc.)
│   │   └── {event_id}.json
│   └── screenshots/            # Screenshot results
│       └── {request_id}.png
│
└── memory/                     # Shared memory cache
    └── shared/
        ├── design_system.json
        ├── api_endpoints.json
        └── recent_learnings.json
```

### Request/Response Protocol

**Request Format:**
```json
{
  "id": "req_abc123",
  "type": "help_request",
  "from_worker_id": "1",
  "from_role": "coder",
  "to_role": "designer",
  "question": "What color should the primary button be?",
  "context": {
    "project": "/workspace/todo-app",
    "file": "src/components/Button.tsx"
  },
  "timeout_seconds": 60,
  "created_at": "2024-12-28T10:00:00Z"
}
```

**Response Format:**
```json
{
  "request_id": "req_abc123",
  "success": true,
  "response": "Use the primary color from the design system: #3B82F6 (blue-500).",
  "from_role": "designer",
  "from_worker_id": "6",
  "completed_at": "2024-12-28T10:00:45Z"
}
```

### Graceful Degradation

- **Timeout Handling**: Requests timeout after configurable period (default 60s)
- **No Deadlocks**: Workers continue after timeout with error response
- **Fallback Behavior**: System works without collaboration (workers just don't get help)
- **Retryable Responses**: Timeout responses indicate retryability

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
| **collaboration** | Inter-worker communication | ask_worker, spawn_subtask, request_browser_action, run_e2e_test, share_learning |
| **browser** | Playwright automation | navigate, screenshot, click, fill, evaluate |
| **playwright** | Headless browser via Playwright MCP | navigate, click, fill, screenshot, evaluate |
| **gmail** | Gmail API with OAuth | read_email, send_email, list_messages, search |
| **firecrawl** | Advanced web scraping | scrape_page, extract_data, crawl_site |
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
  count: 11
  roles: [coder, tester, reviewer, researcher, debugger, designer, heartbeat, verificator, browser-headless, browser-chrome, services]
  reserved_roles: [heartbeat, verificator, services]  # Browser workers are now assignable
  heartbeat_interval: 30
  task_timeout: 1800  # 30-minute default timeout

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

### v3.3 (Current)
- [x] Terminal User Interface (TUI) *(implemented)* - 10-screen Textual-based interface with real-time updates
- [x] AI-First Planning *(implemented)* - Claude-powered task planning replaces pattern matching
- [x] Claude Code Integration *(implemented)* - Session continuity, hooks, role-specific permissions
- [x] Multi-project management *(implemented)*
- [x] Verificator Worker *(implemented)* - Intelligent artifact verification and semantic deduplication
- [x] 11 Workers Architecture *(implemented)* - Expanded from 8 to 11 workers
- [x] Browser Workers *(implemented)* - Playwright headless + Chrome with VNC
- [x] Services Worker *(implemented)* - Gmail, Firecrawl, Calendar integrations
- [x] Reliability Improvements *(implemented)* - Circular deps, graceful degradation, atomic IPC
- [x] Inter-Worker Collaboration *(implemented)* - Workers can communicate, request browser automation, share knowledge
- [x] Context Injection *(implemented)* - Pre-task memory search for relevant patterns and solutions
- [x] Collaboration MCP Server *(implemented)* - 9 tools for ask_worker, spawn_subtask, browser automation
- [x] **Permission Blocklist System** *(v3.3)* - Changed from allowlist to blocklist; workers can run any command except dangerous ones
- [x] **Browser Workers Assignable** *(v3.3)* - Browser-headless and browser-chrome can now receive tasks from AI planner
- [x] **Chrome Auto-Start** *(v3.3)* - Worker-10 auto-starts Chrome on boot with VNC access at localhost:6280
- [x] **Task Timeout Protection** *(v3.3)* - 30-minute default timeout prevents indefinite task hangs
- [x] **AI-First Validation** *(v3.3)* - Semantic output parsing replaces naive keyword matching
- [ ] Web UI dashboard
- [ ] Cost tracking and budgets
- [ ] Custom worker roles

### v3.4
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
