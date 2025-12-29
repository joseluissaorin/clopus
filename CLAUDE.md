# CLOPUS v3 - Universal Autonomous Agent System

> **CLOPUS** = Claude Orchestrated Parallel Universal System
> A self-evolving autonomous agent that can do ANYTHING.

---

## CRITICAL SAFETY RULES

### Docker Container Safety:
- `/workspace` inside containers is VOLUME-MOUNTED to `~/Dev/clopus-projects` on host
- This isolates CLOPUS projects from your main Dev directory
- NEVER run `rm -rf /workspace` or any destructive command on /workspace
- NEVER run cleanup scripts without verifying mount points first
- All file deletions in containers affect the HOST

### Before Running Destructive Commands:
```bash
# Always check what's mounted:
docker inspect <container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{end}}'
```

### Protected Paths (NEVER delete):
- `/home/joseluis/Dev/clopus` - This repository
- `/home/joseluis/Dev/shortgpt` - ArsOculum repository
- `/home/joseluis/Dev/clopus-projects` - CLOPUS workspace (mounted as /workspace in containers)

---

## SYSTEM ARCHITECTURE

### Core Components (12 Parts Working in Tandem)

```
USER INPUT (CLI/File/Webhook)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Python)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Objective   │  │    Task      │  │   Worker     │  │
│  │   Parser     │  │   Planner    │  │   Manager    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Confidence  │  │   Skills     │  │    MCP       │  │
│  │   Engine     │  │   Engine     │  │  Generator   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Template   │  │   GitHub     │  │  Capability  │  │
│  │  Extractor   │  │    Sync      │  │  Installer   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     WORKER POOL (11 Claude Code Instances)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │ CODER   │ │ TESTER  │ │REVIEWER │ │RESEARCH │ │DEBUGGER │ │DESIGNER │               │
│  │         │ │         │ │         │ │         │ │         │ │         │               │
│  │ Writes  │ │ Tests   │ │ Reviews │ │ Looks   │ │ Fixes   │ │ Creates │               │
│  │ code    │ │ + E2E   │ │ code    │ │ things  │ │ issues  │ │ design  │               │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘               │
│  ┌─────────────────────────┐ ┌─────────────────────────────┐ ← Reserved Workers        │
│  │ HEARTBEAT (Worker 7)    │ │ VERIFICATOR (Worker 8)      │                           │
│  │ Completion Guardian     │ │ Intelligent Verification    │                           │
│  └─────────────────────────┘ └─────────────────────────────┘                           │
│  ┌─────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────┐   │
│  │ BROWSER-HEADLESS (9)    │ │ BROWSER-CHROME (10)         │ │ SERVICES (11)       │   │
│  │ Playwright automation   │ │ Chrome + VNC (visual)       │ │ Email/API services  │   │
│  └─────────────────────────┘ └─────────────────────────────┘ └─────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    SHARED SERVICES                       │
│  PostgreSQL │ Redis │ ChromaDB │ MinIO │ Browser        │
│  Traefik │ Prometheus │ Grafana │ Mailhog               │
└─────────────────────────────────────────────────────────┘
```

---

## AI-FIRST PLANNING (NEW in v3.1)

CLOPUS now uses **Claude Code intelligence** instead of pattern matching for task planning.

### What Changed

**OLD APPROACH (DEPRECATED):**
- Regex patterns to detect project types (`todo_app`, `api`, `dashboard`)
- Hardcoded task templates for each project type
- Limited to ~10 predefined project patterns
- Falls back to generic 3-task plan for unknown types

**NEW APPROACH (AI-FIRST):**
- Claude analyzes each objective using real intelligence
- Custom project structures generated dynamically
- Tasks tailored to specific requirements
- Supports ANY type of objective
- Multi-project objectives supported natively

### How It Works

```
USER OBJECTIVE
      │
      ▼
┌─────────────────────────────────────────────────┐
│            AI PLANNER                            │
│                                                  │
│  1. OBJECTIVE_ANALYSIS                          │
│     Claude Code analyzes the objective:         │
│     - What projects need to be created?         │
│     - What technologies are appropriate?        │
│     - How do projects relate to each other?     │
│                                                  │
│  2. TASK_GENERATION (per project)               │
│     Claude Code generates specific tasks:       │
│     - What files need to be created?            │
│     - What dependencies exist?                  │
│     - What validation criteria apply?           │
│                                                  │
└─────────────────────────────────────────────────┘
      │
      ▼
CUSTOMIZED TASKS FOR THIS SPECIFIC OBJECTIVE
```

### Multi-Project Support

One objective can now generate multiple related projects:

```
Objective: "Build a knowledge graph API with a React frontend"

AI Planner Output:
├── nexus-api/          # FastAPI backend
│   └── Tasks: Setup, Models, Endpoints, Auth, Tests
└── nexus-web/          # React frontend
    └── Tasks: Setup, Components, API Client, Tests
    └── Depends on: nexus-api (for API types)
```

### Example: Before vs After

**Before (Pattern Matching):**
```
Objective: "Build a real-time collaborative whiteboard"

Pattern matching result:
  - Type: "custom" (no pattern matched)
  - Tasks: Generic 3-task fallback
    1. Research and planning
    2. Project setup
    3. Core implementation
```

**After (AI-First):**
```
Objective: "Build a real-time collaborative whiteboard"

AI analysis result:
  - Projects: [whiteboard-backend, whiteboard-frontend]
  - Technologies: [FastAPI, WebSockets, React, Canvas API, Redis]
  - Tasks: 15+ specific tasks including:
    1. Setup WebSocket server infrastructure
    2. Create canvas state synchronization protocol
    3. Implement conflict resolution for concurrent edits
    4. Build React canvas component with touch support
    5. Add Redis pub/sub for multi-server scaling
    ...etc
```

### Files Involved

| File | Purpose |
|------|---------|
| `orchestrator/ai_planner.py` | AI-first planning implementation |
| `orchestrator/objective_parser.py` | Now uses AI for parsing (patterns deprecated) |
| `orchestrator/task_planner.py` | Now uses AI for task generation (templates deprecated) |
| `orchestrator/worker_pool.py` | OBJECTIVE_ANALYSIS and TASK_GENERATION task types |

### Fallback Behavior

If AI planning fails (network issues, worker unavailable), the system falls back to the deprecated template-based approach. Logs will show:
```
WARNING: Using DEPRECATED template-based planning - AI planner unavailable
```

---

## CLAUDE CODE INTEGRATION (NEW in v3.2)

CLOPUS now fully integrates with Claude Code's native features for enhanced autonomy and context preservation.

### Session Handling

Each worker maintains persistent sessions for each project they work on:

```
┌─────────────────────────────────────────────────────────┐
│                  SESSION FLOW                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Task 1 (Setup project)                                 │
│     │                                                    │
│     ▼ Session ID: abc123                                │
│  ┌─────────────────────────────────┐                    │
│  │ --output-format json            │                    │
│  │ Returns: {session_id: "abc123"} │                    │
│  └─────────────────────────────────┘                    │
│     │                                                    │
│     ▼ Session saved to IPC                              │
│                                                          │
│  Task 2 (Add feature - same worker, same project)       │
│     │                                                    │
│     ▼                                                    │
│  ┌─────────────────────────────────┐                    │
│  │ --continue                       │                    │
│  │ Maintains full context          │                    │
│  └─────────────────────────────────┘                    │
│     │                                                    │
│     ▼ Full memory of Task 1                             │
│                                                          │
│  Task 3 (Debug issue - orchestrator requests resume)    │
│     │                                                    │
│     ▼                                                    │
│  ┌─────────────────────────────────┐                    │
│  │ --resume abc123                  │                    │
│  │ Resumes specific session        │                    │
│  └─────────────────────────────────┘                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Session Modes

| Mode | Flag | Use Case |
|------|------|----------|
| **Auto** | (default) | Start new session or continue existing |
| **Continue** | `--continue` | Continue last session in current project |
| **Resume** | `--resume <id>` | Resume specific session by ID |
| **New** | (no flag) | Force new session |

### Hooks System

Workers use Claude Code hooks for safety and logging:

| Hook | When | Purpose |
|------|------|---------|
| **PreToolUse** | Before Bash | Block dangerous commands |
| **PostToolUse** | After any tool | Log operations to IPC |

**Dangerous Command Blocking:**
- `rm -rf /` - Blocked
- `sudo` commands - Blocked
- `DROP DATABASE` - Blocked
- `git push --force main` - Blocked

### Role-Specific Configuration

All workers use **Claude Opus 4.5** for maximum capability. Each role has tailored permissions:

| Role | Model | Permissions |
|------|-------|-------------|
| **Coder** | Opus | Full file access, all build tools |
| **Tester** | Opus | Test files only, Playwright access |
| **Reviewer** | Opus | Read-only mode for safety |
| **Designer** | Opus | Design files (md, json, css) only |
| **Researcher** | Opus | Read-only, web search |
| **Debugger** | Opus | Full access for debugging |
| **Verificator** | Opus | Verification and analysis tasks |

### Files Structure

```
.claude/
├── settings.json           # Base configuration
├── settings.coder.json     # Coder overrides
├── settings.reviewer.json  # Reviewer (read-only, opus)
├── settings.designer.json  # Designer (design files only)
├── settings.tester.json    # Tester (test files only)
├── hooks/
│   ├── validate_command.py # PreToolUse: block dangerous commands
│   └── log_operation.py    # PostToolUse: log to IPC
├── skills/
│   ├── architecture-compliance/
│   └── test-strategies/
└── commands/
    └── worker/
        ├── start-task.md
        └── report-status.md
```

### Docker Volume Mounts

```yaml
volumes:
  # Claude Code configuration (hooks, skills, settings)
  - ./.claude:/app/claude-config:ro

  # Session persistence across restarts
  - claude-sessions:/home/ubuntu/.claude/projects
```

### AI Planner Session Continuity

The AI Planner uses session continuity to maintain context during planning:

```
┌─────────────────────────────────────────────────────────┐
│          AI PLANNING WITH SESSION CONTINUITY            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Objective: "Build a knowledge graph API with frontend"  │
│       │                                                  │
│       ▼                                                  │
│  ┌─────────────────────────────────────────────┐        │
│  │ OBJECTIVE_ANALYSIS (starts session)         │        │
│  │ - Identifies 2 projects needed              │        │
│  │ - Determines technologies                   │        │
│  │ - Session ID: session_abc123                │        │
│  └─────────────────────────────────────────────┘        │
│       │                                                  │
│       ▼ --continue (same session)                       │
│  ┌─────────────────────────────────────────────┐        │
│  │ TASK_GENERATION (nexus-api)                 │        │
│  │ - Generates 8 tasks for backend             │        │
│  │ - Has full context from analysis            │        │
│  └─────────────────────────────────────────────┘        │
│       │                                                  │
│       ▼ --continue (same session)                       │
│  ┌─────────────────────────────────────────────┐        │
│  │ TASK_GENERATION (nexus-web)                 │        │
│  │ - Generates 6 tasks for frontend            │        │
│  │ - Knows about API project from context      │        │
│  └─────────────────────────────────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

Benefits:
- **Full context preserved** across analysis → task generation
- **Multi-project awareness** - later projects know about earlier ones
- **Better task quality** - no repeated explanations needed
- **Faster execution** - context doesn't need rebuilding

---

## CONFIDENCE ENGINE

The Confidence Engine decides when to proceed autonomously vs. ask the user.

### How It Works

```python
# Confidence Score Calculation (0.0 - 1.0)
confidence = weighted_average(
    task_complexity         × 0.20,  # How complex is this?
    similar_past_success    × 0.25,  # Have we succeeded before?
    clear_requirements      × 0.25,  # Are requirements clear?
    available_context       × 0.15,  # Do we have enough info?
    domain_familiarity      × 0.15   # Do we know this domain?
)

if confidence >= 0.4:  # Threshold (configurable)
    → PROCEED AUTONOMOUSLY
else:
    → ASK USER FOR CLARIFICATION
```

### Confidence Factors

| Factor | What It Measures |
|--------|------------------|
| `task_complexity` | Low=0.9, Medium=0.7, High=0.5, Very High=0.3 |
| `similar_past_success` | Success rate of similar past decisions |
| `clear_requirements` | Deducts for vague terms, short objectives |
| `available_context` | Relevant memories, specified technologies |
| `domain_familiarity` | Known project types, common technologies |

### Decision Categories

**ALWAYS AUTONOMOUS (Don't ask):**
- Code formatting and style
- Variable/function naming
- File organization
- Dependency version selection
- Test implementation details
- Documentation content
- Commit message formatting

**CONFIDENCE-BASED (Ask if uncertain):**
- Architecture decisions
- Feature scope interpretation
- UI/UX design choices
- Third-party service selection
- Authentication approach
- Data model design
- API design

**ALWAYS ASK (Never assume):**
- Billing/payment integration
- External API credentials
- Production deployment targets
- Domain names and branding
- Legal/compliance requirements
- Cost-incurring decisions

### Learning from Outcomes

The engine learns from every decision:
- If confident but failed → Lower confidence for similar patterns
- If uncertain but succeeded → Raise confidence for similar patterns
- User corrections → Store preference, reduce confidence for that context

---

## HEARTBEAT AGENT (Completion Guardian)

The Heartbeat Agent is a periodic supervisor that ensures projects actually meet their objectives. It's the "little voice in the head" that asks: **"Did we actually build what we promised?"**

### The Problem It Solves

CLOPUS plans tasks upfront and executes them, but without the Heartbeat Agent there's no feedback loop checking:
- Did we actually build what was in the objective?
- Is the API complete or just scaffolded?
- Do the frontend and backend actually work together?
- Did all 8 validation phases run, or just 3?

### How It Works

```
HEARTBEAT CYCLE (every 5 minutes):
1. READ the original objective
2. ASSESS current project state (files, endpoints, tests, validation)
3. COMPARE reality vs requirements (using Claude)
4. IDENTIFY gaps ("objective says edges, but no /edges endpoint exists")
5. SPAWN new tasks to fill gaps
6. VERIFY integration (can frontend actually call backend?)
7. ENFORCE full 8-stage validation before marking complete
8. REPEAT until objective is truly met
```

### Key Behaviors

| Behavior | Description |
|----------|-------------|
| **Objective Parsing** | Uses Claude to extract concrete requirements from objective text |
| **Reality Checking** | Inspects actual files, checks endpoints exist, verifies test coverage |
| **Gap Detection** | "Objective mentions auth, but no auth middleware exists" |
| **Task Spawning** | Creates specific tasks: "Implement POST /edges endpoint" |
| **Integration Testing** | For multi-project: starts both services, runs real requests |
| **Validation Enforcement** | Won't sign off until all 8 phases pass with real tests |
| **Completion Gate** | Project can't be marked "done" without heartbeat approval |

### Multi-Project Integration

For objectives spanning multiple projects (e.g., nexus-api + nexus-web):

1. **Starts all project services** on their allocated ports
2. **Runs real integration tests** - frontend calls backend
3. **Verifies data flow** - create via UI, verify in DB
4. **Takes screenshots** as proof of working features
5. **Only marks complete** when everything works together

### Configuration

```yaml
# config.yaml
heartbeat:
  enabled: true
  interval_seconds: 300  # 5 minutes
  use_claude_analysis: true
  integration_testing:
    enabled: true
    start_services: true
    take_screenshots: true
  completion_gate:
    require_all_validation_stages: true
    require_integration_tests: true
    allowed_failed_tasks: 0
```

### Files

| File | Purpose |
|------|---------|
| `orchestrator/heartbeat_agent.py` | HeartbeatAgent class |
| `orchestrator/config.py` | HeartbeatConfig, CompletionGateConfig |
| `config.yaml` | Heartbeat configuration |

---

## VERIFICATOR WORKER (Intelligent Verification)

The Verificator (Worker 8) is a dedicated Claude Code instance that uses AI intelligence to replace regex/heuristic-based approaches throughout CLOPUS.

### What It Does

| Task Type | Description |
|-----------|-------------|
| **SPECIFY_ARTIFACTS** | Intelligently determines what files/endpoints a task should create |
| **VERIFY_COMPLETION** | Semantically verifies if a completed task actually created its artifacts |
| **CHECK_DUPLICATE** | Detects semantically duplicate tasks (not just word matching) |
| **MATCH_PROJECT** | Matches objectives to correct projects using content analysis |
| **AUDIT_COMPLETED** | Retroactively audits old completed tasks for missing artifacts |
| **SEMANTIC_CHECK** | Checks if task output matches requirements semantically |

### Why It Exists

Before the Verificator, CLOPUS used regex patterns to:
- Infer expected artifacts from task titles (fragile)
- Detect duplicate tasks via word overlap (missed semantic duplicates)
- Match objectives to projects via keyword matching (inaccurate)

**The Problem**: Tasks could be marked "completed" without actually creating their files, and deduplication would block re-creation. This caused gaps like missing `edges.py` despite "Create Edge endpoints" being marked complete.

**The Solution**: Use Claude's intelligence to understand task semantics rather than relying on pattern matching.

### Integration Points

1. **Task Assignment**: Before a task is dispatched, Verificator specifies expected artifacts
2. **Task Completion**: After worker reports success, Verificator verifies artifacts exist
3. **Heartbeat Cycle**: Retroactively audits unverified completed tasks
4. **Task Spawning**: Uses semantic deduplication to prevent true duplicates while allowing re-attempts of failed work

### Files

| File | Purpose |
|------|---------|
| `orchestrator/verificator_client.py` | High-level client for orchestrator |
| `orchestrator/worker_pool.py:verificator` | Worker role definition and prompts |
| `docker-compose.yml:worker-8` | Container configuration |

### Reserved Worker

The Verificator is a **reserved worker** - it is never assigned regular tasks by the task planner. It only handles verification requests from the orchestrator and heartbeat agent.

---

## BROWSER WORKERS (Workers 9-10)

CLOPUS now includes dedicated browser automation workers for web tasks.

### Worker 9: Browser-Headless (Playwright)

A headless Playwright-based worker for fast, automated browser tasks:
- Web scraping and data extraction
- Form filling and submission
- Screenshot capture
- Automated testing
- No visual interface needed

**Docker Configuration:**
```yaml
worker-9:
  environment:
    WORKER_ROLE: browser-headless
    BROWSER_WORKER: "true"
    PLAYWRIGHT_BROWSERS_PATH: /home/ubuntu/.cache/ms-playwright
```

### Worker 10: Browser-Chrome (VNC)

Chrome browser with VNC access for visual browser control:
- Claude in Chrome extension support
- Visual debugging via VNC
- Manual intervention when needed
- Screenshot and recording capabilities

**Access:**
- noVNC: http://localhost:6280
- VNC: localhost:5920

**Docker Configuration:**
```yaml
worker-10:
  build:
    dockerfile: Dockerfile.browser-chrome
  environment:
    WORKER_ROLE: browser-chrome
    BROWSER_MODE: vnc
    DISPLAY: ":99"
  ports:
    - "6280:6080"  # noVNC
    - "5920:5900"  # VNC
```

### Browser Worker Capabilities

| Capability | Worker 9 | Worker 10 |
|------------|----------|-----------|
| Headless operation | Yes | No |
| VNC access | No | Yes |
| Playwright MCP | Yes | Yes |
| Visual debugging | No | Yes |
| Speed | Fast | Moderate |

---

## SERVICES WORKER (Worker 11)

A dedicated worker for external service integrations.

### What It Does

- **Email Automation**: Send, read, organize emails via Gmail MCP
- **Web Scraping**: Advanced data extraction via Firecrawl MCP
- **API Integrations**: Connect to external services
- **Calendar Management**: Google Calendar operations

### Available MCPs

| MCP | Capabilities |
|-----|--------------|
| `gmail` | Read, send, reply, organize emails |
| `firecrawl` | Web scraping, structured data extraction |
| `calendar` | Events, scheduling, availability |

### Docker Configuration

```yaml
worker-11:
  environment:
    WORKER_ROLE: services
    SERVICES_WORKER: "true"
```

### Use Cases

| Use Case | How It Works |
|----------|--------------|
| Cold outreach | Gmail MCP sends personalized emails |
| Competitor research | Firecrawl scrapes competitor sites |
| Meeting scheduling | Calendar MCP manages availability |
| Email answering | Gmail MCP reads and responds |

---

## QUESTION/ANSWER SYSTEM

### How Questions Work

1. **Confidence below threshold** → Question generated
2. **Question written to `/questions/{uuid}.md`**
3. **User answers in `/answers/{uuid}.md`**
4. **CLOPUS processes answer and continues**

### Question File Format
```markdown
# Question

I need clarification on this objective...

## Context

Additional context about the decision...

## Options

1. Option A
2. Option B
3. Option C

---
Confidence: 50%

---
Question ID: e319123d-f37c-4940-97db-b07f1f44d669
Asked at: 2025-12-26T10:29:44

To answer, create a file in the answers directory with this ID as the filename.
```

---

## MCP SERVERS (20 Core Capabilities)

| MCP Server | What It Does |
|------------|--------------|
| `browser` | Full browser control, screenshots, automation |
| `playwright` | Headless browser automation via Playwright MCP |
| `gmail` | Gmail API - read, send, manage emails with OAuth |
| `firecrawl` | Advanced web scraping and data extraction |
| `memory` | Short-term (SQLite) + Long-term (ChromaDB) |
| `validation` | 8-stage validation pipeline |
| `github` | Repos, commits, PRs, issues |
| `database-postgres` | PostgreSQL operations |
| `database-redis` | Redis caching |
| `storage-s3` | MinIO/S3 file storage |
| `search` | Web search |
| `calendar` | Google Calendar integration |
| `notifications` | Push notifications (Firebase, OneSignal) |
| `email-resend` | Transactional email (Resend API) |
| `email-smtp` | SMTP email sending |
| `stripe` | Payment processing |
| `twilio` | SMS/Voice calls |
| `openai` | OpenAI API access |

---

## SKILLS LIBRARY

Skills are loaded based on the task at hand.

### Available Skills

| Category | Skills |
|----------|--------|
| **Development** | React, Vue, Angular, Python, Go, Rust, APIs, TypeScript |
| **Testing** | Jest, Pytest, Playwright E2E, Cypress, Load testing |
| **Communication** | Cold outreach, Email automation, Slack, Discord, SMS |
| **Research** | Web search, Competitor research, Documentation reader |
| **DevOps** | Docker, Kubernetes, CI/CD, Cloud deployments |
| **Media** | Video processing, Image manipulation, Audio |
| **Security** | Vulnerability scanning, OWASP checks |

### Skill Structure
```
/skills/core/
├── development/     # React, Python, APIs, etc.
├── testing/         # Jest, Playwright, Pytest
├── communication/   # Cold outreach, Email, Slack
├── research/        # Web search, Competitor analysis
├── devops/          # Docker, Kubernetes, CI/CD
├── media/           # FFmpeg, ImageMagick
└── security/        # Vulnerability scanning
```

---

## TEMPLATES

Templates are used to scaffold new projects quickly.

### Available Templates

| Template | Description |
|----------|-------------|
| `react-dashboard` | Admin dashboard with charts, auth, dark mode |
| `saas-starter` | SaaS boilerplate with auth, billing, dashboard |
| `python-api` | FastAPI backend with PostgreSQL |
| `expo-app` | React Native mobile app |
| `cli-tool` | Command-line tool boilerplate |

### Template Auto-Extraction

After completing a project, CLOPUS:
1. Anonymizes project-specific details
2. Extracts reusable template
3. Saves to `/templates/extracted/`
4. Pushes to GitHub

---

## CAPABILITY INSTALLER

Auto-installs ANY tool needed for a task.

### Available Tools

| Category | Tools |
|----------|-------|
| **Languages** | Python, Node, Go, Rust, Ruby, PHP, Java |
| **Media** | FFmpeg, ImageMagick, Whisper, yt-dlp |
| **DevOps** | Docker, Kubectl, Terraform, Ansible |
| **Mobile** | Expo, React Native, Flutter |
| **Cloud CLIs** | AWS, GCloud, Azure, Vercel, Railway, Fly.io |
| **Databases** | PostgreSQL, MongoDB, Redis clients |
| **Testing** | Playwright, Cypress |
| **Utilities** | jq, yq, httpie, pandoc |

### How It Works
```python
# Auto-detect from project files
if "package.json" exists → install Node
if "requirements.txt" exists → install Python
if "playwright.config.ts" exists → install Playwright

# Or install on-demand when needed
capability_installer.install("ffmpeg")
```

---

## DYNAMIC PORT MANAGER

Automatically allocates available ports for project dev servers.

### How It Works

```python
# Port range for CLOPUS projects: 3100-3199
# Avoids reserved ports: 3000, 3001, 5173, 8080, etc.

port_manager = get_port_manager()
port = port_manager.get_project_port("my-project")
# Returns 3142 (hash-based, consistent for project name)

# If port is in use, automatically finds next available
```

### Features

| Feature | Description |
|---------|-------------|
| **Availability Check** | Tests if port is actually free before allocating |
| **Hash-Based Assignment** | Same project always tries same port first |
| **Registry Persistence** | Remembers port assignments across restarts |
| **Fallback Scanning** | Scans range if hash-based port unavailable |

### Reserved Ports (Avoided)
- 80, 443 (HTTP/HTTPS)
- 3000, 3001 (Common dev ports)
- 5173, 5174 (Vite defaults)
- 8080, 8000 (Web servers)
- 5432 (PostgreSQL), 6379 (Redis)

---

## AUTO-GENERATED PROJECT DOCUMENTATION

Every completed project gets a PROJECT.md file automatically.

### Generated Content

```markdown
# Project Name

> Auto-generated by CLOPUS on 2025-12-27

## Running the Project
URL: http://localhost:3142

## Technology Stack
- Frontend: React 18
- Tools: Vite, TypeScript
- Styling: Tailwind CSS
- Testing: Vitest

## Features Implemented
- [Done] Add todos
- [Done] Delete todos
- [Done] Dark mode toggle

## Validation Results
- Syntax: Pass
- Lint: Pass
- Build: Pass
- Unit Tests: Pass
```

### Stack Detection
Automatically detects from project files:
- package.json → React, Vue, Next.js, Vite, TypeScript, etc.
- requirements.txt → Django, FastAPI, Flask
- Cargo.toml → Rust
- go.mod → Go

---

## DESIGNER WORKER

The Designer is a dedicated worker that creates comprehensive branding and design systems.

### Designer Responsibilities

1. **Early in Project:** Creates complete design system before implementation
2. **For Existing Projects:** Analyzes and documents existing branding
3. **Ongoing:** Answers design questions from other workers
4. **E2E Testing:** Reviews screenshots and provides feedback

### Design System Output

Designer creates `.clopus/design/DESIGN_SYSTEM.md` with:

```markdown
# [Project Name] Design System

## Brand Identity
- Project Name, Tagline, Personality

## Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Primary | #3B82F6 | Main actions |
| Secondary | #6366F1 | Supporting |
| Accent | #22D3EE | Highlights |
| ... | ... | ... |

## Typography
- Heading Font: [family]
- Body Font: [family]
- Type Scale: H1-H6, body, small

## Spacing System
Base: 4px → xs, sm, md, lg, xl, 2xl

## Component Styles
- Buttons (primary, secondary, ghost)
- Inputs (text, select, checkbox)
- Cards (shadow, border-radius)
- Navigation (header, sidebar)
```

### Design Consultation

Other workers can request design help:
- Ask about colors, spacing, component styles
- Request screenshot feedback
- Get guidance on new features matching existing design

### Task Flow
```
1. Setup task completes
2. DESIGNER creates design system ← RUNS EARLY
3. CODER implements features (follows design system)
4. TESTER takes screenshots
5. DESIGNER reviews screenshots (optional)
```

---

## 8-STAGE VALIDATION PIPELINE

ALL stages must pass. No exceptions.

| Stage | What It Does | Tools |
|-------|--------------|-------|
| 1. Syntax & Format | Parse files, run formatters | Prettier, Black |
| 2. Linting | ESLint, Pylint, TypeScript strict | Language linters |
| 3. Build | Install deps, compile, bundle | npm, pip, webpack |
| 4. Unit Tests | Run tests, 80% coverage | Jest, Pytest |
| 5. Integration Tests | API endpoints, DB integration | Supertest, pytest-asyncio |
| 6. E2E Tests | Browser tests, screenshots | Playwright |
| 7. Security Scan | Vulnerabilities, secrets | npm audit, Semgrep |
| 8. Peer Review | Code quality assessment | Reviewer worker |

### On Failure:
1. Record failure in memory
2. Assign DEBUGGER worker to fix
3. Re-run entire pipeline
4. After 3 failures → escalate to orchestrator
5. After 5 failures → ask user for guidance

---

## BROWSER TESTING & SCREENSHOTS

### Browser Container
- Full Chromium browser at `clopus-browser`
- VNC access at port 6180 (web) / 5910 (VNC)
- Screenshots saved to `/output/screenshots/`
- Session recordings available

### E2E Testing Flow
1. **Start dev server** (`npm run dev`)
2. **Open browser** via MCP
3. **Navigate to localhost**
4. **Test each feature**
5. **Screenshot EVERY step**
6. **Save to /output/screenshots/**

---

## FULL AUTONOMY FLOW

```
1. OBJECTIVE RECEIVED
   ↓
2. PARSE & PLAN
   - Check confidence score
   - If < 0.4 → Ask question
   - Check templates
   ↓
3. AUTO-INSTALL TOOLS
   - Detect needed tools
   - Install if missing
   ↓
4. LOAD SKILLS & SYSTEM PROMPTS
   - Role-specific prompts
   - Relevant skills
   ↓
5. CREATE PROJECT
   - Use template if available
   - Create GitHub repo
   - Scaffold in ~/Dev/clopus-projects/
   ↓
6. WORKERS EXECUTE
   - Coder builds
   - Tester tests + screenshots
   - Researcher looks up APIs
   - Reviewer reviews
   - Debugger fixes issues
   ↓
7. START DEV SERVER
   - npm run dev / python runserver / etc.
   ↓
8. BROWSER TESTING
   - Screenshot every step
   - Save to /output/screenshots/
   ↓
9. VALIDATION (8 stages)
   - All must pass
   - On failure → Debugger → Re-run
   ↓
10. COMPLETION
    - Final commit + push
    - Extract template
    - Store learnings in memory
```

---

## GENERALISTIC USE CASES

| Use Case | How CLOPUS Does It |
|----------|-------------------|
| Build SaaS | Templates + Workers + Validation |
| Answer emails | Email MCP + Skills + Memory |
| Cold outreach | Browser + Email + cold-outreach skill |
| Google Maps scraping | Browser MCP + search skill |
| Mobile app | Expo/Flutter install + development skills |
| Video editing | FFmpeg install + media skills |
| Deploy to cloud | Cloud CLI install + devops skills |
| Payment integration | Stripe MCP + development skills |
| SMS campaigns | Twilio MCP + communication skills |
| Competitor research | Browser + search + research skills |

---

## STARTING CLOPUS

```bash
cd /home/joseluis/Dev/clopus
docker compose up -d
docker logs -f clopus-orchestrator
```

### Submitting an Objective

**Option 1: CLI**
```bash
./clopus "Build a React todo app with dark mode"
```

**Option 2: File**
```bash
echo "Build a React todo app with dark mode" > objectives/my-task.md
# CLOPUS will pick it up automatically
```

---

## GIT REPOSITORY

**Remote:** https://github.com/joseluissaorin/clopus.git

If the local repo is lost, recover with:
```bash
git clone https://github.com/joseluissaorin/clopus.git
```

---

## AUTONOMY IMPROVEMENTS

### Automatic Worker Refresh on Restart

When the orchestrator restarts, it now:
1. **Clears stale IPC files** - Removes old `pending.json`, `result.json`, and `cancel` files from all workers
2. **Workers pick up fresh tasks** - No need to manually restart workers after orchestrator restart
3. **Prevents task duplication** - Old tasks are properly cleaned up before new resumption tasks are created

### Smart Project Path Detection

The validation pipeline now uses a 4-priority system to find the correct project:

1. **Task metadata** - `project_path` field in task metadata (highest priority)
2. **Task description** - Looks for `Project Path:` or `/workspace/<project>` patterns
3. **Task result** - Extracts path from task output
4. **Auto-detection** - Finds most recently modified project with `package.json` or `requirements.txt`

This ensures validation runs on the correct project, not `/workspace` root.

### Real-Time Project State Updates

Project state (`project_state.json`) is now automatically updated when:

| Task Type | State Updated |
|-----------|---------------|
| Design system creation | `design: completed`, `has_design_system: true` |
| E2E testing | `e2e_testing: completed`, screenshots list |
| PROJECT.md generation | `documentation: completed` |
| Validation passes | `validation: completed` |
| Dev server starts | `dev_server.running: true`, port info |
| Implementation tasks | `implementation: in_progress` |

When all stages complete, project is marked as `status: completed`.

---

## RELIABILITY IMPROVEMENTS (v3.1)

Major reliability fixes implemented to ensure projects complete successfully.

### Circular Dependency Detection

**File:** `orchestrator/task_planner.py`

Tasks with circular dependencies are now detected and broken:
```python
# Before: Infinite loop possible
# After: Detects cycles and raises ValueError
def _get_dependency_depth(self, task, task_map, visited=None):
    if task.id in visited:
        raise ValueError(f"Circular dependency: {task.id}")
    visited.add(task.id)
    # ... continues safely
```

### Failed Dependency Handling

**File:** `orchestrator/memory_client.py`

Tasks with failed dependencies are now marked BLOCKED instead of waiting forever:
```python
# New TaskStatus: BLOCKED
# When dependency fails → dependent task marked BLOCKED
# Prevents infinite waiting for impossible completions
```

### ChromaDB Graceful Degradation

**File:** `memory/long_term.py`

If ChromaDB is unavailable, system continues with fallback:
- 5 retry attempts with exponential backoff
- Falls back to in-memory storage
- Operations continue without crashing

### IPC Acknowledgment Handshake

**File:** `orchestrator/worker_pool.py`

Tasks now require acknowledgment before marked as dispatched:
```
1. Orchestrator writes pending.json
2. Worker reads pending.json, writes ack.json
3. Orchestrator verifies ack.json within timeout
4. Only then is task marked as dispatched
```

### Atomic Result Collection

**File:** `orchestrator/worker_pool.py`

Results are collected atomically to prevent race conditions:
```
1. Worker writes result.json
2. Orchestrator renames to result.collected (atomic)
3. Orchestrator reads result.collected
4. Orchestrator deletes result.collected
```

### Configurable Validation Timeouts

**File:** `validation/pipeline.py`

Per-stage configurable timeouts with graceful handling:
```python
DEFAULT_STAGE_TIMEOUTS = {
    "syntax": 60,      # 1 minute
    "lint": 120,       # 2 minutes
    "build": 300,      # 5 minutes
    "unit_tests": 300, # 5 minutes
    "integration_tests": 600,  # 10 minutes
    "e2e_tests": 600,  # 10 minutes
    "security": 180,   # 3 minutes
    "review": 300      # 5 minutes
}
# Timeout → TIMEOUT status (not failure)
# Non-strict mode continues after timeout
```

### Post-Retry Escalation

**File:** `orchestrator/memory_client.py`

When max retries exhausted, task escalates to user:
```
1. Task fails
2. Retry 1, 2, 3...
3. Max retries reached → Create user question
4. User decides: retry, skip, or manual fix
```

### Task Deduplication with Reporting

**File:** `orchestrator/memory_client.py`

Duplicate tasks are detected and reported:
```python
# Returns (created_tasks, skipped_tasks) if return_skipped=True
created, skipped = await memory.create_tasks(objective_id, tasks, return_skipped=True)
# Logs: "Created 5 tasks, skipped 3 duplicates"
```

### Verificator Timeout with Retry Info

**File:** `orchestrator/worker_pool.py`, `orchestrator/verificator_client.py`

Verificator timeouts now return error info for retry handling:
```python
# Before: return None
# After: return {"error": "timeout", "retryable": True, "message": "..."}
```

---

## AI-FIRST VALIDATION (NEW in v3.3)

Validation output parsing now uses semantic understanding instead of naive keyword matching.

### The Problem (Before v3.3)

Validation stages used naive keyword matching that caused false positives:
- Any line containing "error" was marked as an error (even `error_handler.ts` or "0 errors found")
- Review parser matched headers like `## CRITICAL Issues` as actual issues
- Test output parsing matched `PASS` keyword in any context
- Security scanner flagged code comments containing "password"

### The Solution (AI-First v3.3)

| File | What Changed |
|------|--------------|
| `validation/stages/base.py` | Semantic patterns for error/warning detection; success patterns filter false positives |
| `validation/stages/lint.py` | Uses JSON output from ESLint, Ruff, golangci-lint, Clippy |
| `validation/stages/unit_tests.py` | Parses JSON reporters from Jest/Vitest/pytest |
| `validation/stages/security.py` | Context-aware checks that skip test files, comments, and false positive patterns |
| `validation/stages/review.py` | Section-aware parsing (CRITICAL/WARNING headers vs actual issues) |
| `orchestrator/heartbeat_agent.py` | Verificator AI is now primary for project matching and duplicate detection |

### Key Improvements

**Exit codes are primary indicators:**
```python
# Before: relied on keyword matching
if "error" in output:
    errors.append(line)

# After: exit code + semantic patterns
if returncode != 0:
    errors = self.parse_errors(output, returncode)  # Uses semantic patterns
```

**JSON output parsing:**
```python
# ESLint with JSON
cmd = ["eslint", ".", "--format", "json"]
results = json.loads(stdout)
for file_result in results:
    for msg in file_result.get("messages", []):
        if msg.get("severity") == 2:  # Error
            errors.append(...)
```

**Context-aware security scanning:**
```python
SECURITY_CHECKS = [
    {
        "pattern": r'password\s*=\s*["\'][^"\']+["\']',
        "skip_in": ["test", "example", "mock"],
        "skip_patterns": [r"placeholder", r"your_password"],
    }
]
```

**AI-First duplicate detection:**
```python
# Priority 1: Exact match
# Priority 2: Verificator semantic check (primary)
# Priority 3: Word overlap (deprecated fallback, 80% threshold)
```

---

## LESSONS LEARNED

**2025-12-27 (Morning)**: Project was accidentally deleted by running `rm -rf` inside a Docker container on a volume-mounted `/workspace` directory. This affected the host filesystem.

**ALWAYS verify mount points before running destructive commands in containers.**

Workspace is now isolated to `~/Dev/clopus-projects` to prevent future accidents.

**2025-12-27 (Afternoon)**: Workers were stuck on old tasks after orchestrator restart. Root cause: stale IPC files in `/app/ipc/tasks/`. Fixed by clearing IPC files during worker pool initialization.

**2025-12-27 (Evening)**: Duplicate tasks created on orchestrator restart. Root cause: `MemoryClient.create_tasks()` had no deduplication logic - each restart would create new tasks even if identical ones existed. Fixed by adding deduplication in `orchestrator/memory_client.py:132-183` that checks for existing tasks with the same title before creating new ones.

**2025-12-27 (Night)**: Implemented multi-project support for building related projects in parallel. Key changes:
- Added `shared_context.py` for cross-project artifact sharing via `/workspace/.shared/`
- Fixed worker dispatch to use correct project-specific `cwd` instead of `/workspace` root
- Added `_get_project_path_for_task()` helper for consistent project path detection
- Task descriptions now include `Project Path:` for proper worker routing
- Projects can be linked (e.g., nexus-web depends on nexus-api) with shared artifacts

**2025-12-28**: AI-first planning was failing silently. Multiple bugs fixed:
1. **Worker exit code handling** (`workers/worker-entrypoint.sh:346`): Using `||` with command substitution replaced valid Claude output with error codes. Fixed by adding `|| true` to prevent `set -e` from triggering, then handling errors based on output content.
2. **JSON serialization** (`orchestrator/ai_planner.py:494`): Using Python's `str(dict)` produces single-quoted strings, not valid JSON. Fixed by using `json.dumps()`.
3. **Directory permissions** (`workers/worker-entrypoint.sh:41-52`): The `/home/ubuntu/.claude/projects` directory was owned by root in Docker containers, preventing Claude from creating session files. Fixed by adding permission check/fix on startup.
4. **Result collection race condition** (`orchestrator/worker_pool.py:860-872`): Verification result collector was picking up results from other tasks due to shared result file. Fixed by validating task_id before accepting results.
5. **Missing worker acknowledgment** (`workers/worker-entrypoint.sh:291-293`): Workers never wrote `ack.json` that the orchestrator expected, causing 10s timeout and task dispatch failures. Fixed by adding immediate acknowledgment after reading pending.json.
6. **Missing directory handling** (`workers/worker-entrypoint.sh:322-340`): Worker crashed with `cd: No such file or directory` when task had invalid cwd. Fixed by adding directory existence check with fallback to `/workspace`.

**2025-12-29**: Validation stages were failing due to naive keyword matching. Two root causes:
1. **Project directory permissions** (`orchestrator/project_setup.py`, `orchestrator/project_state.py`): Project directories were created by orchestrator (root) but workers run as ubuntu (uid 1000). Workers couldn't write files, so they created alternate directories. Fixed by adding `shutil.chown(path, user=1000, group=1000)` after directory creation.
2. **Review validation false positives** (`validation/stages/review.py`): Parser matched any line containing "error" or "critical" as failures - including headers like `## CRITICAL Issues` and code like `throw new Error()`. Fixed with section-aware parsing that only counts bullet points under CRITICAL/WARNING headers as actual issues.

Additionally, removed naive keyword matching throughout the codebase:
- `validation/stages/base.py`: Added semantic SUCCESS_PATTERNS and ERROR_PATTERNS
- `validation/stages/lint.py`: Now uses JSON output from linters
- `validation/stages/unit_tests.py`: Parses JSON from test reporters
- `validation/stages/security.py`: Context-aware scanning with skip lists
- `orchestrator/heartbeat_agent.py`: Verificator AI is now primary for project matching and duplicate detection (keyword matching demoted to fallback)

---

## MULTI-PROJECT SUPPORT

CLOPUS can now build multiple related projects in parallel with shared context.

### How It Works

1. **Shared Context Directory**: `/workspace/.shared/` stores cross-project data
2. **Project Links**: Defined in `index.json` with source, target, and shared artifacts
3. **Automatic Context Injection**: Workers receive dependency info in task descriptions
4. **Parallel Development**: Both projects build simultaneously where possible

### Key Files

| File | Purpose |
|------|---------|
| `/workspace/.shared/index.json` | Project registry and link definitions |
| `/workspace/.shared/{project}/` | Project-specific shared artifacts |
| `orchestrator/shared_context.py` | SharedContextManager class |
| `orchestrator/main.py:775-833` | `_get_project_path_for_task()` helper |

### Creating Project Links

```python
# In orchestrator or via shared context
shared_context.link_projects(
    source_project="nexus-api",
    target_project="nexus-web",
    link_type="api_consumer",
    shared_artifacts=["api-info.json"]
)
```

### Shared Artifacts

Common artifact types:
- `api-info.json` - API endpoints, OpenAPI spec location
- `design-tokens.json` - Shared colors, spacing, typography
- `config.json` - Environment variables, ports, URLs
