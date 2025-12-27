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
┌─────────────────────────────────────────────────────────┐
│              WORKER POOL (5 Claude Code Instances)       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  │ CODER   │ │ TESTER  │ │REVIEWER │ │RESEARCH │ │DEBUGGER │
│  │         │ │         │ │         │ │         │ │         │
│  │ Writes  │ │ Tests   │ │ Reviews │ │ Looks   │ │ Fixes   │
│  │ code    │ │ + E2E   │ │ code    │ │ things  │ │ issues  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    SHARED SERVICES                       │
│  PostgreSQL │ Redis │ ChromaDB │ MinIO │ Browser        │
│  Traefik │ Prometheus │ Grafana │ Mailhog               │
└─────────────────────────────────────────────────────────┘
```

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

## MCP SERVERS (17 Core Capabilities)

| MCP Server | What It Does |
|------------|--------------|
| `browser` | Full browser control, screenshots, automation |
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

## LESSON LEARNED

**2025-12-27**: Project was accidentally deleted by running `rm -rf` inside a Docker container on a volume-mounted `/workspace` directory. This affected the host filesystem.

**ALWAYS verify mount points before running destructive commands in containers.**

Workspace is now isolated to `~/Dev/clopus-projects` to prevent future accidents.
