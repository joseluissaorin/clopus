# CLOPUS v3: Self-Evolving Autonomous Multi-Agent Claude System

> **Version:** 3.0
> **Date:** 2025-12-26
> **Status:** Architecture Specification

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Core Philosophy](#2-core-philosophy)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [GitHub Repository Strategy](#4-github-repository-strategy)
5. [Confidence-Based Autonomy](#5-confidence-based-autonomy)
6. [Self-Generating Ecosystem](#6-self-generating-ecosystem)
7. [Shared Services Infrastructure](#7-shared-services-infrastructure)
8. [Worker Architecture](#8-worker-architecture)
9. [Memory System](#9-memory-system)
10. [Validation Pipeline](#10-validation-pipeline)
11. [Browser & Automation](#11-browser--automation)
12. [Authentication System](#12-authentication-system)
13. [Interface Layer](#13-interface-layer)
14. [Directory Structure](#14-directory-structure)
15. [Deployment & Operations](#15-deployment--operations)
16. [Security Considerations](#16-security-considerations)

---

## 1. Executive Summary

CLOPUS (Claude Orchestrated Parallel Universal System) is a self-evolving autonomous agent system that:

- Runs **5 parallel Claude Code workers** coordinated by a Python orchestrator
- **Generates its own tools**: Skills, MCP servers, templates, and utilities
- Uses **confidence-based autonomy** - only interrupts when genuinely uncertain
- **Extracts templates** from completed projects for future reuse
- Provides **universal capabilities**: development, media, email, mobile, web, and more
- Maintains **strict validation** - all code must pass comprehensive testing
- **Syncs everything to GitHub** - skills, MCPs, templates, and project outputs

### What Makes v3 Different

| Capability | Description |
|------------|-------------|
| **Self-Generating** | Creates and uploads new skills, MCPs, templates as it works |
| **Confidence Threshold** | Only asks when genuinely uncertain, continuous status updates otherwise |
| **Template Extraction** | Every project becomes a reusable template |
| **Universal Shared Services** | Pre-configured services for any project type |
| **MCP Auto-Generation** | Discovers need → researches API → generates MCP → uploads |

---

## 2. Core Philosophy

### 2.1 Autonomy with Accountability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTONOMY SPECTRUM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FULLY AUTONOMOUS ◄──────────────────────────────────────► FULLY GUIDED     │
│        │                                                          │          │
│        │    ┌─────────────────────────────────────┐              │          │
│        │    │         CLOPUS OPERATES HERE        │              │          │
│        │    │                                     │              │          │
│        │    │  • Continuous status updates        │              │          │
│        │    │  • Proceeds when confident          │              │          │
│        │    │  • Asks only when uncertain         │              │          │
│        │    │  • Learns from every interaction    │              │          │
│        │    └─────────────────────────────────────┘              │          │
│        │                      ▲                                  │          │
│        │                      │                                  │          │
│        │            Confidence Threshold                         │          │
│        │                                                         │          │
└────────┴─────────────────────────────────────────────────────────┴──────────┘
```

### 2.2 Self-Improvement Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTINUOUS IMPROVEMENT CYCLE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│     │  WORK    │ ──► │  LEARN   │ ──► │ GENERATE │ ──► │  SHARE   │        │
│     │          │     │          │     │          │     │          │        │
│     │ Complete │     │ Extract  │     │ Create   │     │ Upload   │        │
│     │ tasks    │     │ patterns │     │ reusable │     │ to       │        │
│     │          │     │          │     │ assets   │     │ GitHub   │        │
│     └──────────┘     └──────────┘     └──────────┘     └──────────┘        │
│           ▲                                                   │             │
│           │                                                   │             │
│           └───────────────────────────────────────────────────┘             │
│                         Available for future projects                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Zero Waste Principle

Every piece of work contributes to the system's knowledge:

- **Successful solution** → Extract pattern → Create skill/template
- **Failed attempt** → Record in memory → Avoid in future
- **New API learned** → Generate MCP server → Available to all workers
- **User correction** → Update confidence model → Better decisions

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CLOPUS v3 ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         USER INTERFACE LAYER                                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │    │
│  │  │    CLI      │  │ File-Based  │  │  Webhooks   │  │  Future Adapters    │ │    │
│  │  │  ./clopus   │  │ objectives/ │  │  /api/...   │  │  Slack/Discord/Web  │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                           │
│                                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         ORCHESTRATOR (Python)                                │    │
│  │                                                                              │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐ │    │
│  │  │ Objective  │ │   Task     │ │  Worker    │ │ Confidence │ │  Status   │ │    │
│  │  │  Parser    │ │  Planner   │ │  Manager   │ │  Engine    │ │  Reporter │ │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘ │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐ │    │
│  │  │  Memory    │ │  Skills    │ │    MCP     │ │  Template  │ │  GitHub   │ │    │
│  │  │  Router    │ │  Engine    │ │ Generator  │ │  Extractor │ │   Sync    │ │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘ │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐                              │    │
│  │  │ Validation │ │ Capability │ │   Repo     │                              │    │
│  │  │   Gate     │ │ Installer  │ │  Manager   │                              │    │
│  │  └────────────┘ └────────────┘ └────────────┘                              │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                           │
│                    ┌─────────────────────┼─────────────────────┐                    │
│                    ▼                     ▼                     ▼                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                    WORKER POOL (5 Claude Code Instances)                     │    │
│  │                                                                              │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │    │
│  │  │Worker 1 │  │Worker 2 │  │Worker 3 │  │Worker 4 │  │Worker 5 │           │    │
│  │  │(Dynamic)│  │(Dynamic)│  │(Dynamic)│  │(Dynamic)│  │(Dynamic)│           │    │
│  │  │         │  │         │  │         │  │         │  │         │           │    │
│  │  │ Role:   │  │ Role:   │  │ Role:   │  │ Role:   │  │ Role:   │           │    │
│  │  │ Coder   │  │ Tester  │  │Research │  │Reviewer │  │ Deploy  │           │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                           │
│                                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         SHARED SERVICES LAYER                                │    │
│  │                                                                              │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │    │
│  │  │       MEMORY        │  │       BROWSER       │  │     VALIDATION      │ │    │
│  │  │  ChromaDB + SQLite  │  │  MCP + Container    │  │  8-Stage Pipeline   │ │    │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │    │
│  │  │      DATABASES      │  │       EMAIL         │  │      STORAGE        │ │    │
│  │  │ Postgres/Redis/Mongo│  │   Resend + SMTP     │  │  MinIO (S3-compat)  │ │    │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │    │
│  │  │       PROXY         │  │       QUEUE         │  │     MONITORING      │ │    │
│  │  │  Traefik + SSL      │  │   Redis/RabbitMQ    │  │   Logs + Metrics    │ │    │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                           │
│                                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         CAPABILITY LAYER                                     │    │
│  │                                                                              │    │
│  │  Languages: Python, Node.js, Go, Rust, PHP, Ruby, Java, C#                  │    │
│  │  Media: FFmpeg, ImageMagick, Whisper, Sharp                                 │    │
│  │  Mobile: Expo CLI, React Native, Flutter, Android SDK                       │    │
│  │  Cloud: AWS, GCP, Azure, Vercel, Railway, Fly.io CLIs                       │    │
│  │  DevOps: Docker, Kubernetes, Terraform, Ansible                             │    │
│  │  + On-demand installation of any other tool                                  │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                           │
│                                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         HOST INTEGRATION                                     │    │
│  │                                                                              │    │
│  │  Mounts: ~/Dev, ~/.config/gh, ~/.ssh, ~/.aws, ~/.anthropic                  │    │
│  │  Auth: API Key + Claude Login (dual mode)                                   │    │
│  │  Network: Host network access for local services                            │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. GitHub Repository Strategy

### 4.1 Repository Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           GITHUB REPOSITORY STRATEGY                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  github.com/USERNAME/clopus/                    # MAIN CLOPUS REPOSITORY            │
│  ├── core/                                      # Core system code                  │
│  ├── skills/                                    # Skills library                    │
│  │   ├── core/                                  # Pre-installed skills              │
│  │   └── generated/                             # Auto-generated skills             │
│  ├── mcp-servers/                               # MCP server library                │
│  │   ├── core/                                  # Pre-installed MCPs                │
│  │   └── generated/                             # Auto-generated MCPs               │
│  ├── templates/                                 # Project templates                 │
│  │   ├── core/                                  # Pre-defined templates             │
│  │   └── extracted/                             # Extracted from projects           │
│  ├── tools/                                     # Utility tools                     │
│  │   ├── core/                                  # Pre-installed tools               │
│  │   └── generated/                             # Auto-generated tools              │
│  └── knowledge/                                 # Shared knowledge base             │
│      ├── patterns/                              # Reusable patterns                 │
│      ├── solutions/                             # Common solutions                  │
│      └── mistakes/                              # Anti-patterns to avoid            │
│                                                                                      │
│  github.com/USERNAME/project-alpha/             # Generated project (separate)      │
│  github.com/USERNAME/project-beta/              # Generated project (separate)      │
│  github.com/USERNAME/client-webapp/             # Generated project (separate)      │
│  ...                                                                                 │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Auto-Sync Behavior

```python
# Pseudocode for GitHub sync behavior

class GitHubSync:
    def on_skill_generated(self, skill):
        """When a new skill is created"""
        # 1. Validate skill format
        # 2. Test skill functionality
        # 3. Commit to clopus/skills/generated/
        # 4. Push to GitHub
        # 5. Create PR if significant change

    def on_mcp_generated(self, mcp):
        """When a new MCP server is created"""
        # 1. Validate MCP server
        # 2. Run integration tests
        # 3. Commit to clopus/mcp-servers/generated/
        # 4. Push to GitHub
        # 5. Update MCP registry

    def on_template_extracted(self, template):
        """When a template is extracted from a project"""
        # 1. Anonymize project-specific details
        # 2. Validate template can generate new project
        # 3. Commit to clopus/templates/extracted/
        # 4. Push to GitHub
        # 5. Update template catalog

    def on_project_milestone(self, project, milestone):
        """When a project reaches a milestone"""
        # 1. Commit all changes
        # 2. Create meaningful commit message
        # 3. Push to project repo
        # 4. Update status

    def on_project_complete(self, project):
        """When a project is completed"""
        # 1. Final commit
        # 2. Create release tag
        # 3. Extract template
        # 4. Update CLOPUS knowledge base
```

### 4.3 Repository Creation Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         NEW PROJECT REPOSITORY FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  User: "Build a SaaS invoicing app"                                                 │
│                          │                                                           │
│                          ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  1. PARSE OBJECTIVE                                                          │   │
│  │     → Identify: SaaS, invoicing, web app                                     │   │
│  │     → Suggest repo name: "invoice-saas" or ask user                          │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                          │                                                           │
│                          ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  2. CREATE REPOSITORY                                                        │   │
│  │     → gh repo create USERNAME/invoice-saas --private                         │   │
│  │     → Clone to ~/Dev/invoice-saas                                            │   │
│  │     → Initialize with README, .gitignore, LICENSE                            │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                          │                                                           │
│                          ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  3. CHECK TEMPLATES                                                          │   │
│  │     → Search clopus/templates/ for matching templates                        │   │
│  │     → Found: "saas-starter", "react-dashboard"                               │   │
│  │     → Apply relevant template as base                                        │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                          │                                                           │
│                          ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  4. DEVELOPMENT CYCLE                                                        │   │
│  │     → Workers implement features                                             │   │
│  │     → Commit after each milestone                                            │   │
│  │     → Push regularly                                                         │   │
│  │     → Status updates to user                                                 │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                          │                                                           │
│                          ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  5. COMPLETION                                                               │   │
│  │     → Final validation                                                       │   │
│  │     → Create release v1.0.0                                                  │   │
│  │     → Extract template → push to clopus/templates/extracted/                 │   │
│  │     → Update knowledge base                                                  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Confidence-Based Autonomy

### 5.1 Decision Framework

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        CONFIDENCE-BASED DECISION SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  For each decision point:                                                            │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                     CONFIDENCE SCORE CALCULATION                             │   │
│  │                                                                              │   │
│  │  confidence = weighted_average(                                              │   │
│  │      similar_past_decisions      × 0.25,  # Have we seen this before?       │   │
│  │      past_outcome_success_rate   × 0.25,  # Did similar decisions work?     │   │
│  │      requirement_clarity         × 0.20,  # How clear is what's needed?     │   │
│  │      decision_reversibility      × 0.15,  # Can we undo if wrong?           │   │
│  │      risk_level                  × 0.15   # What's the downside?            │   │
│  │  )                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│                          │                                                           │
│                          ▼                                                           │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                                │ │
│  │   confidence >= 0.7 ───────────────────────► PROCEED AUTONOMOUSLY             │ │
│  │         │                                           │                          │ │
│  │         │                                           ▼                          │ │
│  │         │                                    Log decision                      │ │
│  │         │                                    Send status update                │ │
│  │         │                                    Continue working                  │ │
│  │         │                                                                      │ │
│  │   confidence < 0.7 ────────────────────────► ASK USER                         │ │
│  │         │                                           │                          │ │
│  │         │                                           ▼                          │ │
│  │         │                                    Formulate clear question          │ │
│  │         │                                    Provide options if applicable     │ │
│  │         │                                    Wait for response                 │ │
│  │         │                                    Learn from answer                 │ │
│  │         │                                                                      │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Decision Categories

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DECISION CATEGORY MATRIX                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ALWAYS AUTONOMOUS (Don't ask):                                                      │
│  ├── Code formatting and style                                                       │
│  ├── Variable/function naming (following conventions)                                │
│  ├── File organization within established patterns                                   │
│  ├── Dependency version selection (unless security issue)                            │
│  ├── Test implementation details                                                     │
│  ├── Error message wording                                                           │
│  ├── Documentation content                                                           │
│  └── Commit message formatting                                                       │
│                                                                                      │
│  CONFIDENCE-BASED (Ask if uncertain):                                                │
│  ├── Architecture decisions (database choice, framework selection)                   │
│  ├── Feature scope interpretation                                                    │
│  ├── UI/UX design choices                                                            │
│  ├── Third-party service selection                                                   │
│  ├── Authentication/authorization approach                                           │
│  ├── Data model design                                                               │
│  ├── API design                                                                      │
│  └── Performance vs simplicity tradeoffs                                             │
│                                                                                      │
│  ALWAYS ASK (Never assume):                                                          │
│  ├── Billing/payment integration specifics                                           │
│  ├── External API credentials                                                        │
│  ├── Production deployment targets                                                   │
│  ├── Domain names and branding                                                       │
│  ├── Legal/compliance requirements                                                   │
│  ├── User data handling policies                                                     │
│  └── Cost-incurring decisions (paid services)                                        │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Learning from Decisions

```python
# Pseudocode for decision learning

class DecisionLearner:
    def record_decision(self, decision):
        """Record every decision made"""
        self.memory.store({
            "decision_type": decision.type,
            "context": decision.context,
            "options_considered": decision.options,
            "choice_made": decision.choice,
            "confidence_score": decision.confidence,
            "was_autonomous": decision.confidence >= 0.7,
            "timestamp": now()
        })

    def record_outcome(self, decision_id, outcome):
        """Record the outcome of a decision"""
        decision = self.memory.get(decision_id)
        decision.outcome = outcome
        decision.success = outcome.is_successful

        # Update confidence model
        self.update_confidence_weights(decision)

    def update_confidence_weights(self, decision):
        """Adjust confidence calculation based on outcomes"""
        similar_decisions = self.memory.find_similar(decision)

        # If we were confident and wrong, lower confidence for similar
        if decision.was_autonomous and not decision.success:
            self.lower_confidence_for_pattern(decision.pattern)

        # If user corrected us, learn from their choice
        if decision.user_correction:
            self.learn_preference(decision.context, decision.user_correction)

        # If we asked and user confirmed our suggestion, increase confidence
        if not decision.was_autonomous and decision.user_confirmed_suggestion:
            self.raise_confidence_for_pattern(decision.pattern)
```

### 5.4 Status Update System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           STATUS UPDATE BEHAVIOR                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  STATUS UPDATES (Continuous, non-blocking):                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • Task started/completed                                                    │   │
│  │  • Milestone reached (e.g., "Frontend scaffold complete")                    │   │
│  │  • Worker role changes                                                       │   │
│  │  • Validation stage progress                                                 │   │
│  │  • Skill/MCP/Template generated                                              │   │
│  │  • Commits pushed                                                            │   │
│  │  • Resource utilization updates                                              │   │
│  │                                                                              │   │
│  │  Format: [TIMESTAMP] [LEVEL] [WORKER] Message                                │   │
│  │  Example: [14:32:15] [INFO] [W2:Coder] Completed user authentication module  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  BLOCKING QUESTIONS (Work pauses until answered):                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • Confidence below threshold                                                │   │
│  │  • Ambiguous requirements                                                    │   │
│  │  • Multiple valid approaches with different tradeoffs                        │   │
│  │  • External credentials needed                                               │   │
│  │  • Cost-incurring decisions                                                  │   │
│  │                                                                              │   │
│  │  Format: Structured question with options                                    │   │
│  │  Location: questions/ directory or CLI prompt                                │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Self-Generating Ecosystem

### 6.1 Overview

CLOPUS doesn't just use tools - it creates, improves, and shares them:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        SELF-GENERATING ECOSYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │     SKILLS      │  │  MCP SERVERS    │  │   TEMPLATES     │  │    TOOLS      │  │
│  │                 │  │                 │  │                 │  │               │  │
│  │ Domain-specific │  │ External API    │  │ Project         │  │ Utility       │  │
│  │ instructions    │  │ integrations    │  │ scaffolds       │  │ scripts       │  │
│  │                 │  │                 │  │                 │  │               │  │
│  │ Auto-generated  │  │ Auto-generated  │  │ Auto-extracted  │  │ Auto-created  │  │
│  │ when patterns   │  │ when new APIs   │  │ from completed  │  │ when needed   │  │
│  │ emerge          │  │ encountered     │  │ projects        │  │               │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └───────────────┘  │
│          │                    │                    │                    │          │
│          └────────────────────┴────────────────────┴────────────────────┘          │
│                                        │                                            │
│                                        ▼                                            │
│                         ┌─────────────────────────────┐                            │
│                         │      GITHUB SYNC            │                            │
│                         │                             │                            │
│                         │  All generated assets are   │                            │
│                         │  committed and pushed to    │                            │
│                         │  the CLOPUS repository      │                            │
│                         └─────────────────────────────┘                            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Skills Generation System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           SKILL GENERATION PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  TRIGGER CONDITIONS:                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  1. Pattern Recognition: Same problem solved 3+ times                        │   │
│  │  2. Complex Solution: Multi-step solution that could be documented           │   │
│  │  3. New Domain: First time working in a new technology area                  │   │
│  │  4. User Request: Explicit request to create a skill                         │   │
│  │  5. API Mastery: Deep understanding of an API achieved                       │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  GENERATION PROCESS:                                                                 │
│                                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│  │ Detect  │ ─► │ Analyze │ ─► │ Draft   │ ─► │ Test    │ ─► │ Publish │          │
│  │ Pattern │    │ Context │    │ SKILL.md│    │ Skill   │    │ to GH   │          │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘          │
│       │              │              │              │              │               │
│       ▼              ▼              ▼              ▼              ▼               │
│  Memory shows   Extract key    Generate      Verify skill   Commit to            │
│  recurring     steps, tools,   YAML front-   triggers       clopus/skills/       │
│  solution      patterns        matter +      correctly      generated/           │
│                                instructions  and works                           │
│                                                                                      │
│  SKILL STRUCTURE:                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  skills/generated/{skill-name}/                                              │   │
│  │  ├── SKILL.md           # Main skill definition                              │   │
│  │  ├── examples/          # Usage examples                                     │   │
│  │  ├── scripts/           # Helper scripts                                     │   │
│  │  └── tests/             # Skill validation tests                             │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 MCP Server Generation System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        MCP SERVER GENERATION PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  TRIGGER: Worker needs to interact with external API not currently supported        │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 1: SEARCH EXISTING                                                     │   │
│  │                                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │ CLOPUS Repo │  │   npm/PyPI  │  │   GitHub    │  │ MCP Registry│         │   │
│  │  │ mcp-servers │  │  packages   │  │   search    │  │  (official) │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  │         │               │               │               │                   │   │
│  │         └───────────────┴───────────────┴───────────────┘                   │   │
│  │                                 │                                            │   │
│  │                                 ▼                                            │   │
│  │                    Found existing? ──► YES ──► Install and use              │   │
│  │                         │                                                    │   │
│  │                         NO                                                   │   │
│  │                         ▼                                                    │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 2: RESEARCH API                                                        │   │
│  │                                                                              │   │
│  │  • Fetch API documentation                                                   │   │
│  │  • Identify authentication method                                            │   │
│  │  • List available endpoints                                                  │   │
│  │  • Understand rate limits                                                    │   │
│  │  • Note error handling patterns                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 3: GENERATE MCP SERVER                                                 │   │
│  │                                                                              │   │
│  │  mcp-servers/generated/{api-name}/                                           │   │
│  │  ├── package.json          # Dependencies                                    │   │
│  │  ├── tsconfig.json         # TypeScript config                               │   │
│  │  ├── src/                                                                    │   │
│  │  │   ├── index.ts          # Entry point                                     │   │
│  │  │   ├── tools/            # Tool definitions                                │   │
│  │  │   │   ├── {action1}.ts                                                    │   │
│  │  │   │   └── {action2}.ts                                                    │   │
│  │  │   └── types.ts          # Type definitions                                │   │
│  │  ├── tests/                # Integration tests                               │   │
│  │  └── README.md             # Usage documentation                             │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 4: TEST & VALIDATE                                                     │   │
│  │                                                                              │   │
│  │  • Build TypeScript                                                          │   │
│  │  • Run integration tests (with mock or sandbox API if available)             │   │
│  │  • Verify all tools work                                                     │   │
│  │  • Test error handling                                                       │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 5: PUBLISH                                                             │   │
│  │                                                                              │   │
│  │  • Commit to clopus/mcp-servers/generated/                                   │   │
│  │  • Push to GitHub                                                            │   │
│  │  • Update MCP registry in clopus                                             │   │
│  │  • Make available to all workers                                             │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.4 Template Extraction System

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        TEMPLATE EXTRACTION PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  TRIGGER: Project successfully completed and validated                               │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 1: ANALYZE PROJECT                                                     │   │
│  │                                                                              │   │
│  │  • Identify project type (SaaS, CLI, mobile app, etc.)                       │   │
│  │  • List technologies used                                                    │   │
│  │  • Map directory structure                                                   │   │
│  │  • Identify core vs project-specific code                                    │   │
│  │  • Find configuration patterns                                               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 2: ABSTRACT SPECIFICS                                                  │   │
│  │                                                                              │   │
│  │  Replace:                                                                    │   │
│  │  • Project name → {{PROJECT_NAME}}                                           │   │
│  │  • Domain/URLs → {{DOMAIN}}                                                  │   │
│  │  • Company info → {{COMPANY_NAME}}                                           │   │
│  │  • API keys → {{API_KEY_*}}                                                  │   │
│  │  • Database names → {{DB_NAME}}                                              │   │
│  │  • User-specific paths → relative paths                                      │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 3: CREATE TEMPLATE STRUCTURE                                           │   │
│  │                                                                              │   │
│  │  templates/extracted/{template-name}/                                        │   │
│  │  ├── TEMPLATE.md           # Template metadata and usage                     │   │
│  │  ├── template.json         # Configuration schema                            │   │
│  │  ├── scaffold/             # Template files                                  │   │
│  │  │   ├── {{PROJECT_NAME}}/ # Placeholder directories                        │   │
│  │  │   │   ├── src/                                                            │   │
│  │  │   │   ├── tests/                                                          │   │
│  │  │   │   └── ...                                                             │   │
│  │  └── hooks/                # Post-generation scripts                         │   │
│  │      ├── post-create.sh                                                      │   │
│  │      └── validate.sh                                                         │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 4: VALIDATE TEMPLATE                                                   │   │
│  │                                                                              │   │
│  │  • Generate new project from template                                        │   │
│  │  • Verify all placeholders replaced                                          │   │
│  │  • Run build                                                                 │   │
│  │  • Run tests                                                                 │   │
│  │  • If fails → refine template                                                │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                    │
│                                 ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  STEP 5: PUBLISH                                                             │   │
│  │                                                                              │   │
│  │  • Commit to clopus/templates/extracted/                                     │   │
│  │  • Push to GitHub                                                            │   │
│  │  • Update template catalog                                                   │   │
│  │  • Available for future projects                                             │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  TEMPLATE METADATA (TEMPLATE.md):                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  ---                                                                         │   │
│  │  name: saas-invoicing                                                        │   │
│  │  description: SaaS invoicing app with React, FastAPI, PostgreSQL, Stripe     │   │
│  │  extracted_from: invoice-saas (2025-12-26)                                   │   │
│  │  technologies:                                                               │   │
│  │    - react                                                                   │   │
│  │    - typescript                                                              │   │
│  │    - fastapi                                                                 │   │
│  │    - postgresql                                                              │   │
│  │    - stripe                                                                  │   │
│  │  variables:                                                                  │   │
│  │    - PROJECT_NAME: "Name of the project"                                     │   │
│  │    - DOMAIN: "Production domain"                                             │   │
│  │    - STRIPE_PUBLIC_KEY: "Stripe publishable key"                             │   │
│  │  ---                                                                         │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.5 Core Skills Library

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CORE SKILLS LIBRARY                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  skills/core/                                                                        │
│  │                                                                                   │
│  ├── development/                                                                    │
│  │   ├── react-typescript/          # React + TypeScript best practices             │
│  │   ├── nextjs-fullstack/          # Next.js app development                       │
│  │   ├── python-fastapi/            # FastAPI backend development                   │
│  │   ├── python-django/             # Django web development                        │
│  │   ├── nodejs-express/            # Express.js APIs                               │
│  │   ├── go-api/                    # Go API development                            │
│  │   ├── rust-cli/                  # Rust CLI applications                         │
│  │   ├── expo-mobile/               # React Native + Expo                           │
│  │   ├── flutter-mobile/            # Flutter mobile apps                           │
│  │   ├── wordpress-theme/           # WordPress theme/plugin dev                    │
│  │   ├── shopify-app/               # Shopify app development                       │
│  │   └── chrome-extension/          # Browser extension development                 │
│  │                                                                                   │
│  ├── testing/                                                                        │
│  │   ├── playwright-e2e/            # End-to-end testing                            │
│  │   ├── jest-unit/                 # JavaScript unit testing                       │
│  │   ├── pytest-python/             # Python testing                                │
│  │   ├── cypress-testing/           # Cypress E2E                                   │
│  │   └── load-testing/              # Performance/load testing                      │
│  │                                                                                   │
│  ├── media/                                                                          │
│  │   ├── ffmpeg-video/              # Video processing                              │
│  │   ├── imagemagick-images/        # Image manipulation                            │
│  │   ├── whisper-transcription/     # Audio transcription                           │
│  │   ├── audio-processing/          # Audio editing                                 │
│  │   └── pdf-manipulation/          # PDF generation and editing                    │
│  │                                                                                   │
│  ├── communication/                                                                  │
│  │   ├── email-automation/          # Send/receive/parse emails                     │
│  │   ├── cold-outreach/             # Cold email campaigns                          │
│  │   ├── slack-integration/         # Slack bot/integration                         │
│  │   ├── discord-bot/               # Discord bot development                       │
│  │   └── sms-twilio/                # SMS via Twilio                                │
│  │                                                                                   │
│  ├── data/                                                                           │
│  │   ├── web-scraping/              # Web scraping patterns                         │
│  │   ├── data-analysis/             # Data analysis with pandas                     │
│  │   ├── etl-pipelines/             # ETL pipeline development                      │
│  │   ├── database-design/           # Database schema design                        │
│  │   └── api-integration/           # Third-party API integration                   │
│  │                                                                                   │
│  ├── devops/                                                                         │
│  │   ├── docker-containerization/   # Docker best practices                         │
│  │   ├── kubernetes-deployment/     # K8s deployment                                │
│  │   ├── ci-cd-github-actions/      # GitHub Actions workflows                      │
│  │   ├── terraform-infrastructure/  # Infrastructure as code                        │
│  │   └── monitoring-setup/          # Logging and monitoring                        │
│  │                                                                                   │
│  ├── research/                                                                       │
│  │   ├── web-search/                # Web search and summarization                  │
│  │   ├── documentation-reader/      # Parse and understand docs                     │
│  │   ├── codebase-analysis/         # Analyze existing codebases                    │
│  │   └── competitor-research/       # Competitive analysis                          │
│  │                                                                                   │
│  └── security/                                                                       │
│      ├── security-audit/            # Security review patterns                      │
│      ├── authentication/            # Auth implementation                           │
│      ├── encryption/                # Encryption best practices                     │
│      └── compliance/                # GDPR, SOC2, etc.                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.6 Core MCP Servers Library

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CORE MCP SERVERS LIBRARY                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  mcp-servers/core/                                                                   │
│  │                                                                                   │
│  ├── browser/                       # Playwright browser automation                 │
│  ├── memory/                        # Memory system access                          │
│  ├── validation/                    # Test runner integration                       │
│  ├── email-resend/                  # Resend email API                              │
│  ├── email-smtp/                    # Generic SMTP                                  │
│  ├── database-postgres/             # PostgreSQL operations                         │
│  ├── database-redis/                # Redis operations                              │
│  ├── storage-s3/                    # S3/MinIO operations                           │
│  ├── github/                        # GitHub API operations                         │
│  ├── stripe/                        # Stripe payments                               │
│  ├── twilio/                        # SMS and voice                                 │
│  ├── openai/                        # OpenAI API (for comparison)                   │
│  ├── search/                        # Web search APIs                               │
│  ├── calendar/                      # Google/Outlook calendar                       │
│  └── notifications/                 # Push notifications                            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Shared Services Infrastructure

### 7.1 Service Tiers

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        SHARED SERVICES INFRASTRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 1: ALWAYS RUNNING (Core Services)                                      │   │
│  │                                                                              │   │
│  │  These services start with CLOPUS and remain running:                        │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐  │   │
│  │  │ PostgreSQL │ │   Redis    │ │   MinIO    │ │  Traefik   │ │  Mailhog  │  │   │
│  │  │            │ │            │ │            │ │            │ │           │  │   │
│  │  │ Primary DB │ │ Cache/     │ │ S3-compat  │ │ Reverse    │ │ Email     │  │   │
│  │  │ for all    │ │ Queue/     │ │ object     │ │ proxy +    │ │ testing   │  │   │
│  │  │ projects   │ │ Pub-Sub    │ │ storage    │ │ SSL        │ │ (dev)     │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘  │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐                               │   │
│  │  │  ChromaDB  │ │  Browser   │ │ Prometheus │                               │   │
│  │  │            │ │ Container  │ │  + Grafana │                               │   │
│  │  │ Vector DB  │ │ Chromium   │ │ Monitoring │                               │   │
│  │  │ for memory │ │ + VNC      │ │ & metrics  │                               │   │
│  │  └────────────┘ └────────────┘ └────────────┘                               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 2: ON-DEMAND (Started when needed)                                     │   │
│  │                                                                              │   │
│  │  These services start automatically when a project needs them:               │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐  │   │
│  │  │  MongoDB   │ │   MySQL    │ │   Kafka    │ │ RabbitMQ   │ │  Elastic  │  │   │
│  │  │            │ │            │ │            │ │            │ │  search   │  │   │
│  │  │ Document   │ │ MySQL DB   │ │ Event      │ │ Message    │ │ Full-text │  │   │
│  │  │ store      │ │ if needed  │ │ streaming  │ │ queue      │ │ search    │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘  │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐               │   │
│  │  │  WordPress │ │   Strapi   │ │ Keycloak   │ │  Temporal  │               │   │
│  │  │            │ │            │ │            │ │            │               │   │
│  │  │ CMS if     │ │ Headless   │ │ Auth       │ │ Workflow   │               │   │
│  │  │ needed     │ │ CMS        │ │ server     │ │ engine     │               │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 3: EXTERNAL (Configured via environment)                               │   │
│  │                                                                              │   │
│  │  External services accessed via API credentials:                             │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐  │   │
│  │  │   Resend   │ │   Stripe   │ │   Twilio   │ │  Vercel    │ │  Railway  │  │   │
│  │  │   (email)  │ │ (payments) │ │ (SMS/voice)│ │ (deploy)   │ │ (deploy)  │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘  │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐  │   │
│  │  │    AWS     │ │    GCP     │ │   Azure    │ │ Cloudflare │ │  Fly.io   │  │   │
│  │  │  (cloud)   │ │  (cloud)   │ │  (cloud)   │ │ (CDN/DNS)  │ │ (deploy)  │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘  │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐                               │   │
│  │  │   OpenAI   │ │  Pinecone  │ │  Supabase  │                               │   │
│  │  │   (LLM)    │ │ (vectors)  │ │  (BaaS)    │                               │   │
│  │  └────────────┘ └────────────┘ └────────────┘                               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  TIER 4: AI/ML SERVICES (Local or cloud)                                     │   │
│  │                                                                              │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐               │   │
│  │  │  Whisper   │ │  Ollama    │ │ Embeddings │ │ ComfyUI    │               │   │
│  │  │  (local)   │ │  (local)   │ │  (local)   │ │ (images)   │               │   │
│  │  │            │ │            │ │            │ │            │               │   │
│  │  │ Audio      │ │ Local LLMs │ │ Text       │ │ Image      │               │   │
│  │  │ transcribe │ │ for tasks  │ │ embeddings │ │ generation │               │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Service Discovery & Auto-Provisioning

```python
# Pseudocode for service discovery

class ServiceManager:
    def analyze_project_needs(self, project):
        """Analyze what services a project needs"""
        needs = []

        # Check package.json, requirements.txt, etc.
        if project.uses("prisma") or project.uses("typeorm"):
            needs.append("postgresql")

        if project.uses("mongoose") or project.uses("mongodb"):
            needs.append("mongodb")

        if project.uses("redis") or project.uses("bull"):
            needs.append("redis")

        if project.uses("stripe"):
            needs.append("stripe")
            self.check_credentials("STRIPE_SECRET_KEY")

        if project.uses("resend") or project.has_email_feature():
            needs.append("email")

        return needs

    def provision_services(self, needs):
        """Start required services"""
        for service in needs:
            if service in TIER_1_SERVICES:
                # Already running
                continue
            elif service in TIER_2_SERVICES:
                self.start_container(service)
            elif service in TIER_3_SERVICES:
                self.verify_credentials(service)
```

### 7.3 Docker Compose Configuration

```yaml
# docker-compose.yml (simplified)
version: '3.8'

services:
  # ============================================
  # ORCHESTRATOR
  # ============================================
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile.orchestrator
    volumes:
      - ./:/app
      - ~/Dev:/workspace
      - ~/.config/gh:/root/.config/gh:ro
      - ~/.ssh:/root/.ssh:ro
      - ~/.anthropic:/root/.anthropic
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - AUTH_MODE=${AUTH_MODE:-api}
    depends_on:
      - chromadb
      - postgres
      - redis
      - browser

  # ============================================
  # WORKERS (5 instances)
  # ============================================
  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    deploy:
      replicas: 5
    volumes:
      - ~/Dev:/workspace
      - ~/.config/gh:/root/.config/gh:ro
      - ~/.ssh:/root/.ssh:ro
      - ~/.anthropic:/root/.anthropic
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

  # ============================================
  # TIER 1: CORE SERVICES
  # ============================================
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: clopus

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  chromadb:
    image: chromadb/chroma
    volumes:
      - chromadb_data:/chroma/chroma

  browser:
    build:
      context: .
      dockerfile: Dockerfile.browser
    ports:
      - "6080:6080"  # noVNC web access
    shm_size: '2gb'

  traefik:
    image: traefik:v3.0
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

  mailhog:
    image: mailhog/mailhog
    ports:
      - "8025:8025"  # Web UI

  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"

  # ============================================
  # TIER 2: ON-DEMAND (profiles)
  # ============================================
  mongodb:
    image: mongo:7
    profiles: ["mongodb"]
    volumes:
      - mongodb_data:/data/db

  mysql:
    image: mysql:8
    profiles: ["mysql"]
    environment:
      MYSQL_ROOT_PASSWORD: clopus

  elasticsearch:
    image: elasticsearch:8.11.0
    profiles: ["elasticsearch"]
    environment:
      - discovery.type=single-node

  rabbitmq:
    image: rabbitmq:3-management
    profiles: ["rabbitmq"]

  kafka:
    image: confluentinc/cp-kafka:latest
    profiles: ["kafka"]

  wordpress:
    image: wordpress:latest
    profiles: ["wordpress"]

  keycloak:
    image: quay.io/keycloak/keycloak
    profiles: ["keycloak"]

volumes:
  postgres_data:
  redis_data:
  minio_data:
  chromadb_data:
  mongodb_data:
```

---

## 8. Worker Architecture

### 8.1 Worker Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           WORKER LIFECYCLE                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│  │  INIT   │ ─► │  IDLE   │ ─► │ ASSIGN  │ ─► │  WORK   │ ─► │ REPORT  │ ──┐      │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘   │      │
│       │              ▲              │              │              │         │      │
│       │              │              │              │              │         │      │
│       │              └──────────────┴──────────────┴──────────────┘         │      │
│       │                                                                      │      │
│       │         ┌─────────────────────────────────────────────────────────┐ │      │
│       │         │                    WORK PHASE                           │ │      │
│       │         │                                                         │ │      │
│       │         │  1. Load role-specific system prompt                    │ │      │
│       │         │  2. Load required skills                                │ │      │
│       │         │  3. Query memory for relevant context                   │ │      │
│       │         │  4. Execute task                                        │ │      │
│       │         │  5. Run validation (if applicable)                      │ │      │
│       │         │  6. Record learnings to memory                          │ │      │
│       │         │  7. Report completion to orchestrator                   │ │      │
│       │         └─────────────────────────────────────────────────────────┘ │      │
│       │                                                                      │      │
│       └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Worker Roles

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              WORKER ROLES                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  CODER                                                                       │    │
│  │  Primary implementation role                                                 │    │
│  │                                                                              │    │
│  │  Responsibilities:                                                           │    │
│  │  • Write production code                                                     │    │
│  │  • Implement features                                                        │    │
│  │  • Create components and modules                                             │    │
│  │  • Write inline documentation                                                │    │
│  │                                                                              │    │
│  │  Tools: All code editing, file operations, package managers                  │    │
│  │  Skills: Development skills matching the project stack                       │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  TESTER                                                                      │    │
│  │  Quality assurance role                                                      │    │
│  │                                                                              │    │
│  │  Responsibilities:                                                           │    │
│  │  • Write unit tests                                                          │    │
│  │  • Write integration tests                                                   │    │
│  │  • Write E2E tests                                                           │    │
│  │  • Run validation pipeline                                                   │    │
│  │  • Report failures with context                                              │    │
│  │                                                                              │    │
│  │  Tools: Test runners, browser automation, coverage tools                     │    │
│  │  Skills: Testing skills (jest, pytest, playwright, etc.)                     │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  REVIEWER                                                                    │    │
│  │  Code quality gatekeeper                                                     │    │
│  │                                                                              │    │
│  │  Responsibilities:                                                           │    │
│  │  • Review code for quality                                                   │    │
│  │  • Check architecture decisions                                              │    │
│  │  • Identify potential issues                                                 │    │
│  │  • Approve or reject with feedback                                           │    │
│  │  • Security review                                                           │    │
│  │                                                                              │    │
│  │  Tools: Code analysis, security scanners, read-only access                   │    │
│  │  Skills: Security, architecture, code quality                                │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  RESEARCHER                                                                  │    │
│  │  Information gathering role                                                  │    │
│  │                                                                              │    │
│  │  Responsibilities:                                                           │    │
│  │  • Web search for solutions                                                  │    │
│  │  • Read documentation                                                        │    │
│  │  • Analyze APIs                                                              │    │
│  │  • Investigate issues                                                        │    │
│  │  • Compile findings for other workers                                        │    │
│  │                                                                              │    │
│  │  Tools: Browser, web search, documentation readers                           │    │
│  │  Skills: Research, web-search, documentation-reader                          │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  DEBUGGER                                                                    │    │
│  │  Issue resolution specialist                                                 │    │
│  │                                                                              │    │
│  │  Responsibilities:                                                           │    │
│  │  • Fix failing tests                                                         │    │
│  │  • Debug runtime errors                                                      │    │
│  │  • Resolve build issues                                                      │    │
│  │  • Performance optimization                                                  │    │
│  │                                                                              │    │
│  │  Tools: Debuggers, profilers, log analyzers                                  │    │
│  │  Skills: Debugging, performance optimization                                 │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  DEPLOYER                                                                    │    │
│  │  Infrastructure and deployment role                                          │    │
│  │                                                                              │    │
│  │  Responsibilities:                                                           │    │
│  │  • Configure CI/CD                                                           │    │
│  │  • Deploy to staging/production                                              │    │
│  │  • Manage infrastructure                                                     │    │
│  │  • Monitor deployments                                                       │    │
│  │                                                                              │    │
│  │  Tools: Docker, cloud CLIs, deployment platforms                             │    │
│  │  Skills: DevOps, containerization, cloud deployment                          │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  SPECIALIST                                                                  │    │
│  │  Domain-specific expert (dynamically assigned)                               │    │
│  │                                                                              │    │
│  │  Examples:                                                                   │    │
│  │  • Video Editor: FFmpeg, video processing                                    │    │
│  │  • Email Marketer: Cold outreach, email automation                           │    │
│  │  • Data Analyst: pandas, visualization                                       │    │
│  │  • Mobile Developer: Expo, React Native                                      │    │
│  │                                                                              │    │
│  │  Tools: Domain-specific tools                                                │    │
│  │  Skills: Loaded based on specialization                                      │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Worker Communication Protocol

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        WORKER COMMUNICATION PROTOCOL                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Message Types:                                                                      │
│                                                                                      │
│  ORCHESTRATOR → WORKER:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  {                                                                           │   │
│  │    "type": "TASK_ASSIGN",                                                    │   │
│  │    "task_id": "uuid",                                                        │   │
│  │    "role": "coder",                                                          │   │
│  │    "skills_to_load": ["react-typescript", "fastapi"],                        │   │
│  │    "context": {                                                              │   │
│  │      "project": "invoice-saas",                                              │   │
│  │      "objective": "Implement user authentication",                           │   │
│  │      "relevant_memory": [...],                                               │   │
│  │      "dependent_tasks": [...]                                                │   │
│  │    }                                                                         │   │
│  │  }                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  WORKER → ORCHESTRATOR:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  {                                                                           │   │
│  │    "type": "TASK_COMPLETE" | "TASK_BLOCKED" | "STATUS_UPDATE",               │   │
│  │    "task_id": "uuid",                                                        │   │
│  │    "status": "completed" | "blocked" | "in_progress",                        │   │
│  │    "result": {                                                               │   │
│  │      "files_changed": [...],                                                 │   │
│  │      "tests_added": [...],                                                   │   │
│  │      "learnings": [...],                                                     │   │
│  │      "next_steps": [...]                                                     │   │
│  │    },                                                                        │   │
│  │    "blocking_reason": null | "Need clarification on X"                       │   │
│  │  }                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  WORKER → WORKER (via shared memory):                                               │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  Workers don't communicate directly. Instead:                                │   │
│  │  1. Worker A completes task, records learnings to memory                     │   │
│  │  2. Worker B, when assigned related task, queries memory                     │   │
│  │  3. Worker B sees Worker A's learnings and builds upon them                  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Memory System

### 9.1 Dual Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           MEMORY ARCHITECTURE                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │         SHORT-TERM MEMORY            │  │         LONG-TERM MEMORY             │ │
│  │            (SQLite)                  │  │           (ChromaDB)                 │ │
│  ├──────────────────────────────────────┤  ├──────────────────────────────────────┤ │
│  │                                      │  │                                      │ │
│  │  Purpose: Operational state          │  │  Purpose: Semantic knowledge         │ │
│  │                                      │  │                                      │ │
│  │  Contents:                           │  │  Contents:                           │ │
│  │  • Current tasks & status            │  │  • Learnings from past projects      │ │
│  │  • Worker assignments                │  │  • Successful solutions              │ │
│  │  • Active projects                   │  │  • Patterns discovered               │ │
│  │  • Recent conversation context       │  │  • Mistakes to avoid                 │ │
│  │  • Pending questions                 │  │  • API knowledge                     │ │
│  │  • Validation results                │  │  • Code snippets                     │ │
│  │  • Git commit history                │  │  • User preferences                  │ │
│  │                                      │  │                                      │ │
│  │  Retention: Session-based            │  │  Retention: Permanent                │ │
│  │  Query: SQL (exact match)            │  │  Query: Semantic similarity          │ │
│  │                                      │  │                                      │ │
│  └──────────────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                                      │
│                              MEMORY OPERATIONS                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                              │   │
│  │  STORE:                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  memory.store({                                                        │  │   │
│  │  │    "content": "React useEffect cleanup prevents memory leaks",         │  │   │
│  │  │    "type": "learning",                                                 │  │   │
│  │  │    "context": {"project": "dashboard", "technology": "react"},         │  │   │
│  │  │    "tags": ["react", "hooks", "memory-leak", "best-practice"],         │  │   │
│  │  │    "confidence": 0.95,                                                 │  │   │
│  │  │    "source": "worker-2"                                                │  │   │
│  │  │  })                                                                    │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                              │   │
│  │  QUERY:                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  results = memory.query(                                               │  │   │
│  │  │    "How do I prevent memory leaks in React?",                          │  │   │
│  │  │    filters={"technology": "react"},                                    │  │   │
│  │  │    limit=5                                                             │  │   │
│  │  │  )                                                                     │  │   │
│  │  │  # Returns semantically similar learnings                              │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Memory Categories

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           MEMORY CATEGORIES                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  LEARNINGS                                                                           │
│  ├── Technical insights discovered during work                                       │
│  ├── "FastAPI with SQLAlchemy requires async session handling"                       │
│  └── Confidence score based on validation results                                    │
│                                                                                      │
│  SOLUTIONS                                                                           │
│  ├── Complete solutions to specific problems                                         │
│  ├── Code snippets with context                                                      │
│  └── Tagged with problem type and technologies                                       │
│                                                                                      │
│  PATTERNS                                                                            │
│  ├── Recurring code patterns                                                         │
│  ├── Architecture patterns                                                           │
│  └── May trigger skill generation if frequent                                        │
│                                                                                      │
│  MISTAKES                                                                            │
│  ├── Errors encountered and how they were resolved                                   │
│  ├── Anti-patterns to avoid                                                          │
│  └── Negative examples for learning                                                  │
│                                                                                      │
│  USER_PREFERENCES                                                                    │
│  ├── Learned user preferences from corrections                                       │
│  ├── Coding style preferences                                                        │
│  └── Technology choices                                                              │
│                                                                                      │
│  DECISIONS                                                                           │
│  ├── Every decision made (autonomous or user-guided)                                 │
│  ├── Outcome of each decision                                                        │
│  └── Used to train confidence model                                                  │
│                                                                                      │
│  PROJECT_CONTEXT                                                                     │
│  ├── Project-specific knowledge                                                      │
│  ├── Architecture decisions                                                          │
│  └── Business rules and requirements                                                 │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Validation Pipeline

### 10.1 Eight-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        STRICT VALIDATION PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ALL STAGES MUST PASS - NO EXCEPTIONS                                               │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 1: SYNTAX & FORMAT                                                      │ │
│  │                                                                                │ │
│  │  • Parse files for syntax errors                                               │ │
│  │  • Run formatters (Prettier, Black, etc.)                                      │ │
│  │  • Validate JSON, YAML, config files                                           │ │
│  │                                                                                │ │
│  │  Tools: Language parsers, formatters                                           │ │
│  │  Pass Criteria: Zero syntax errors, consistent formatting                      │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 2: LINTING & STATIC ANALYSIS                                            │ │
│  │                                                                                │ │
│  │  • ESLint / Pylint / RuboCop / etc.                                            │ │
│  │  • TypeScript strict mode                                                      │ │
│  │  • MyPy type checking                                                          │ │
│  │                                                                                │ │
│  │  Tools: Language-specific linters                                              │ │
│  │  Pass Criteria: Zero errors (warnings configurable)                            │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 3: BUILD                                                                │ │
│  │                                                                                │ │
│  │  • Install dependencies                                                        │ │
│  │  • Compile/transpile                                                           │ │
│  │  • Bundle for production                                                       │ │
│  │                                                                                │ │
│  │  Tools: npm, pip, cargo, webpack, vite                                         │ │
│  │  Pass Criteria: Successful build, no dependency conflicts                      │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 4: UNIT TESTS                                                           │ │
│  │                                                                                │ │
│  │  • Run existing test suite                                                     │ │
│  │  • Run new tests written for this change                                       │ │
│  │  • Coverage check (minimum 80%)                                                │ │
│  │                                                                                │ │
│  │  Tools: Jest, Pytest, Go test, etc.                                            │ │
│  │  Pass Criteria: 100% tests pass, coverage threshold met                        │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 5: INTEGRATION TESTS                                                    │ │
│  │                                                                                │ │
│  │  • API endpoint tests                                                          │ │
│  │  • Database integration                                                        │ │
│  │  • Service communication tests                                                 │ │
│  │                                                                                │ │
│  │  Tools: Supertest, pytest-asyncio, testcontainers                              │ │
│  │  Pass Criteria: All integration tests pass                                     │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 6: E2E TESTS                                                            │ │
│  │                                                                                │ │
│  │  • Browser automation tests                                                    │ │
│  │  • User flow testing                                                           │ │
│  │  • Visual regression (optional)                                                │ │
│  │                                                                                │ │
│  │  Tools: Playwright, Cypress                                                    │ │
│  │  Pass Criteria: Critical user paths work                                       │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 7: SECURITY SCAN                                                        │ │
│  │                                                                                │ │
│  │  • Dependency vulnerability check                                              │ │
│  │  • Secret detection                                                            │ │
│  │  • SAST (static application security testing)                                  │ │
│  │  • OWASP Top 10 checks                                                         │ │
│  │                                                                                │ │
│  │  Tools: npm audit, safety, Semgrep, Trivy                                      │ │
│  │  Pass Criteria: No high/critical vulnerabilities                               │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                             │
│                                        ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  STAGE 8: PEER REVIEW (Reviewer Worker)                                        │ │
│  │                                                                                │ │
│  │  • Code quality assessment                                                     │ │
│  │  • Architecture review                                                         │ │
│  │  • Best practices check                                                        │ │
│  │  • Approval or rejection with feedback                                         │ │
│  │                                                                                │ │
│  │  Tools: Dedicated reviewer worker                                              │ │
│  │  Pass Criteria: Reviewer approval                                              │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ON FAILURE:                                                                         │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  1. Record failure details in memory                                           │ │
│  │  2. Assign DEBUGGER worker to fix                                              │ │
│  │  3. Re-run entire pipeline after fix                                           │ │
│  │  4. After 3 failures: escalate to orchestrator                                 │ │
│  │  5. After 5 failures: ask user for guidance                                    │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Browser & Automation

### 11.1 Dual Browser Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        BROWSER ARCHITECTURE                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │      MCP BROWSER SERVER              │  │      BROWSER CONTAINER               │ │
│  │      (Playwright-based)              │  │      (Full Desktop)                  │ │
│  ├──────────────────────────────────────┤  ├──────────────────────────────────────┤ │
│  │                                      │  │                                      │ │
│  │  Purpose:                            │  │  Purpose:                            │ │
│  │  Direct Claude control of browser    │  │  Visual debugging & complex tasks    │ │
│  │                                      │  │                                      │ │
│  │  Capabilities:                       │  │  Capabilities:                       │ │
│  │  • Navigate to URLs                  │  │  • Full Chromium browser             │ │
│  │  • Click elements                    │  │  • VNC access (view what's happening)│ │
│  │  • Type text                         │  │  • noVNC web interface               │ │
│  │  • Take screenshots                  │  │  • Session recording                 │ │
│  │  • Execute JavaScript                │  │  • Multiple browser profiles         │ │
│  │  • Wait for elements                 │  │  • Persistent cookies/auth           │ │
│  │  • Handle downloads                  │  │  • Extension support                 │ │
│  │                                      │  │                                      │ │
│  │  Use when:                           │  │  Use when:                           │ │
│  │  • Automated E2E testing             │  │  • Complex visual interactions       │ │
│  │  • Web scraping                      │  │  • OAuth flows requiring popups      │ │
│  │  • Form filling                      │  │  • Debugging browser issues          │ │
│  │  • Simple web interactions           │  │  • Recording demos                   │ │
│  │                                      │  │  • Tasks requiring auth persistence  │ │
│  └──────────────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                                      │
│                              INTEGRATION                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                              │   │
│  │  Workers can use EITHER browser system based on task:                        │   │
│  │                                                                              │   │
│  │  MCP Browser:                                                                │   │
│  │  - Invoked via MCP tools in Claude Code                                      │   │
│  │  - Headless by default                                                       │   │
│  │  - Fast for automated tasks                                                  │   │
│  │                                                                              │   │
│  │  Browser Container:                                                          │   │
│  │  - Accessed via VNC/noVNC                                                    │   │
│  │  - Visible UI for debugging                                                  │   │
│  │  - Persistent sessions                                                       │   │
│  │                                                                              │   │
│  │  The orchestrator decides which to use based on task requirements.           │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Browser Container Dockerfile

```dockerfile
# Dockerfile.browser
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    chromium-browser \
    firefox \
    x11vnc \
    xvfb \
    fluxbox \
    novnc \
    websockify \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Setup virtual display
ENV DISPLAY=:99
ENV SCREEN_WIDTH=1920
ENV SCREEN_HEIGHT=1080

# Setup noVNC
RUN ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html

# Supervisor config
COPY browser/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Browser profiles directory
RUN mkdir -p /browser-profiles

EXPOSE 6080 5900

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

---

## 12. Authentication System

### 12.1 Dual Authentication Modes

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION SYSTEM                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │         API KEY MODE                 │  │       CLAUDE LOGIN MODE              │ │
│  ├──────────────────────────────────────┤  ├──────────────────────────────────────┤ │
│  │                                      │  │                                      │ │
│  │  Configuration:                      │  │  Configuration:                      │ │
│  │  AUTH_MODE=api                       │  │  AUTH_MODE=login                     │ │
│  │  ANTHROPIC_API_KEY=sk-...            │  │                                      │ │
│  │                                      │  │  First-time setup:                   │ │
│  │  Behavior:                           │  │  ./clopus login                      │ │
│  │  • Uses API directly                 │  │  → Opens browser for OAuth           │ │
│  │  • Metered billing                   │  │  → Stores session                    │ │
│  │  • Full headless operation           │  │                                      │ │
│  │                                      │  │  Behavior:                           │ │
│  │  Best for:                           │  │  • Uses subscription                 │ │
│  │  • Production deployments            │  │  • No per-token costs                │ │
│  │  • CI/CD pipelines                   │  │  • Session refresh as needed         │ │
│  │  • High-volume usage                 │  │                                      │ │
│  │                                      │  │  Best for:                           │ │
│  │                                      │  │  • Personal use                      │ │
│  │                                      │  │  • Development                       │ │
│  │                                      │  │  • Cost-conscious usage              │ │
│  └──────────────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                          HYBRID MODE                                         │   │
│  │                                                                              │   │
│  │  Configuration:                                                              │   │
│  │  AUTH_MODE=hybrid                                                            │   │
│  │  ANTHROPIC_API_KEY=sk-...  (backup)                                          │   │
│  │                                                                              │   │
│  │  Behavior:                                                                   │   │
│  │  1. Try Claude login session first                                           │   │
│  │  2. If session expired → attempt refresh                                     │   │
│  │  3. If refresh fails → fall back to API key                                  │   │
│  │  4. Log which mode is being used                                             │   │
│  │                                                                              │   │
│  │  Best for:                                                                   │   │
│  │  • Maximum reliability                                                       │   │
│  │  • Use subscription when available, API as backup                            │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  Session storage:                                                                    │
│  ~/.anthropic/                                                                       │
│  ├── session.json          # OAuth tokens                                           │
│  ├── session.lock          # Prevent concurrent refresh                             │
│  └── config.json           # User preferences                                       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Interface Layer

### 13.1 Modular Interface Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                      INTERFACE ADAPTERS                                      │   │
│  │                                                                              │   │
│  │  All interfaces implement a common protocol:                                 │   │
│  │                                                                              │   │
│  │  class InterfaceAdapter:                                                     │   │
│  │      def receive_objective(self) -> Objective                                │   │
│  │      def send_status(self, status: Status) -> None                           │   │
│  │      def ask_question(self, question: Question) -> Answer                    │   │
│  │      def receive_answer(self) -> Answer                                      │   │
│  │      def send_completion(self, result: Result) -> None                       │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                     │
│  │   CLI ADAPTER   │  │  FILE ADAPTER   │  │ WEBHOOK ADAPTER │                     │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤                     │
│  │                 │  │                 │  │                 │                     │
│  │ ./clopus        │  │ objectives/*.md │  │ POST /objective │                     │
│  │   objective     │  │ questions/*.md  │  │ GET /status     │                     │
│  │   status        │  │ answers/*.md    │  │ POST /answer    │                     │
│  │   questions     │  │ status.json     │  │ WebSocket for   │                     │
│  │   answer        │  │                 │  │ real-time       │                     │
│  │                 │  │ File watcher    │  │                 │                     │
│  │ Interactive     │  │ for async ops   │  │ REST + WS API   │                     │
│  │ terminal UI     │  │                 │  │                 │                     │
│  │                 │  │                 │  │                 │                     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                     │
│                                                                                      │
│  FUTURE ADAPTERS (easy to add):                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  SLACK ADAPTER  │  │ DISCORD ADAPTER │  │   WEB ADAPTER   │                     │
│  │                 │  │                 │  │                 │                     │
│  │  Slack bot      │  │  Discord bot    │  │  Web dashboard  │                     │
│  │  integration    │  │  integration    │  │  with React UI  │                     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 13.2 CLI Commands

```bash
# CLOPUS CLI Commands

# Start the system
./clopus start                    # Start all containers
./clopus start --workers 3        # Start with specific worker count
./clopus start --profile minimal  # Start with minimal services

# Stop the system
./clopus stop                     # Graceful shutdown
./clopus stop --force             # Force stop all containers

# Authentication
./clopus login                    # OAuth login for subscription mode
./clopus logout                   # Clear session
./clopus auth status              # Show current auth mode

# Objectives
./clopus objective "Build a ..."  # Give a new objective
./clopus objective --file obj.md  # Load objective from file
./clopus objectives               # List all objectives

# Status
./clopus status                   # Current system status
./clopus status --watch           # Live status updates
./clopus status --json            # JSON output

# Questions & Answers
./clopus questions                # List pending questions
./clopus answer <id> "response"   # Answer a specific question
./clopus answer --interactive     # Interactive Q&A mode

# Workers
./clopus workers                  # List workers and status
./clopus workers --detailed       # Detailed worker info

# Projects
./clopus projects                 # List all projects
./clopus project <name> status    # Project-specific status

# Memory
./clopus memory search "query"    # Search memory
./clopus memory stats             # Memory statistics

# Skills
./clopus skills                   # List all skills
./clopus skills sync              # Sync skills to GitHub

# Logs
./clopus logs                     # View recent logs
./clopus logs -f                  # Follow logs
./clopus logs --worker 1          # Logs for specific worker

# Maintenance
./clopus gc                       # Garbage collection
./clopus backup                   # Backup memory and config
./clopus update                   # Update CLOPUS
```

---

## 14. Directory Structure

```
~/Dev/clopus/
│
├── docker-compose.yml              # Main orchestration
├── docker-compose.dev.yml          # Development overrides
├── docker-compose.prod.yml         # Production overrides
├── Dockerfile.base                 # Shared base image
├── Dockerfile.orchestrator         # Orchestrator image
├── Dockerfile.worker               # Worker image
├── Dockerfile.browser              # Browser container
│
├── .env.example                    # Environment template
├── config.yaml                     # System configuration
├── setup.sh                        # One-liner setup
├── install.sh                      # Remote install script
├── clopus                          # Main CLI (bash)
│
├── orchestrator/                   # Python orchestrator
│   ├── __init__.py
│   ├── main.py                     # Entry point
│   ├── config.py                   # Configuration
│   ├── objective_parser.py         # Parse objectives
│   ├── task_planner.py             # Break into tasks
│   ├── worker_pool.py              # Manage workers
│   ├── worker_protocol.py          # Communication protocol
│   ├── confidence_engine.py        # Decision confidence
│   ├── memory_client.py            # Memory interface
│   ├── skills_engine.py            # Skill management
│   ├── mcp_generator.py            # Generate MCP servers
│   ├── template_extractor.py       # Extract templates
│   ├── validation_gate.py          # Validation pipeline
│   ├── github_sync.py              # GitHub operations
│   ├── repo_manager.py             # Repository management
│   ├── service_manager.py          # Service provisioning
│   ├── status_reporter.py          # Status updates
│   └── user_interaction.py         # Questions/answers
│
├── memory/                         # Memory system
│   ├── __init__.py
│   ├── short_term.py               # SQLite operations
│   ├── long_term.py                # ChromaDB operations
│   ├── embeddings.py               # Embedding generation
│   └── schema.sql                  # SQLite schema
│
├── interfaces/                     # Interface adapters
│   ├── __init__.py
│   ├── base.py                     # Base adapter class
│   ├── cli_adapter.py              # CLI interface
│   ├── file_adapter.py             # File-based interface
│   └── webhook_adapter.py          # HTTP webhook interface
│
├── mcp-servers/                    # MCP server library
│   ├── core/                       # Pre-installed
│   │   ├── browser/
│   │   │   ├── package.json
│   │   │   ├── tsconfig.json
│   │   │   └── src/
│   │   │       └── index.ts
│   │   ├── memory/
│   │   ├── validation/
│   │   ├── email-resend/
│   │   ├── email-smtp/
│   │   ├── database-postgres/
│   │   ├── database-redis/
│   │   ├── storage-s3/
│   │   ├── github/
│   │   ├── stripe/
│   │   ├── twilio/
│   │   └── search/
│   └── generated/                  # Auto-generated
│       └── .gitkeep
│
├── skills/                         # Skills library
│   ├── core/                       # Pre-installed
│   │   ├── development/
│   │   │   ├── react-typescript/
│   │   │   │   └── SKILL.md
│   │   │   ├── nextjs-fullstack/
│   │   │   ├── python-fastapi/
│   │   │   ├── expo-mobile/
│   │   │   └── wordpress-theme/
│   │   ├── testing/
│   │   │   ├── playwright-e2e/
│   │   │   ├── jest-unit/
│   │   │   └── pytest-python/
│   │   ├── media/
│   │   │   ├── ffmpeg-video/
│   │   │   ├── imagemagick-images/
│   │   │   └── whisper-transcription/
│   │   ├── communication/
│   │   │   ├── email-automation/
│   │   │   ├── cold-outreach/
│   │   │   └── slack-integration/
│   │   ├── data/
│   │   │   ├── web-scraping/
│   │   │   └── data-analysis/
│   │   ├── devops/
│   │   │   ├── docker-containerization/
│   │   │   └── ci-cd-github-actions/
│   │   └── research/
│   │       ├── web-search/
│   │       └── documentation-reader/
│   └── generated/                  # Auto-generated
│       └── .gitkeep
│
├── templates/                      # Project templates
│   ├── core/                       # Pre-defined
│   │   ├── saas-starter/
│   │   │   ├── TEMPLATE.md
│   │   │   ├── template.json
│   │   │   └── scaffold/
│   │   ├── react-dashboard/
│   │   ├── python-api/
│   │   ├── expo-app/
│   │   └── cli-tool/
│   └── extracted/                  # Extracted from projects
│       └── .gitkeep
│
├── tools/                          # Utility tools
│   ├── core/
│   │   ├── project-analyzer/       # Analyze project structure
│   │   ├── dependency-updater/     # Update dependencies
│   │   └── code-formatter/         # Format code
│   └── generated/
│       └── .gitkeep
│
├── knowledge/                      # Shared knowledge base
│   ├── patterns/                   # Reusable patterns
│   ├── solutions/                  # Common solutions
│   └── mistakes/                   # Anti-patterns
│
├── workers/                        # Worker configuration
│   ├── system-prompts/
│   │   ├── base.md                 # Shared context
│   │   ├── coder.md
│   │   ├── tester.md
│   │   ├── reviewer.md
│   │   ├── researcher.md
│   │   ├── debugger.md
│   │   └── deployer.md
│   └── hooks/                      # Claude Code hooks
│       ├── pre-tool.sh
│       ├── post-tool.sh
│       └── memory-sync.sh
│
├── validation/                     # Validation system
│   ├── pipeline.py                 # Orchestrate stages
│   ├── stages/
│   │   ├── syntax.py
│   │   ├── lint.py
│   │   ├── build.py
│   │   ├── unit_tests.py
│   │   ├── integration_tests.py
│   │   ├── e2e_tests.py
│   │   ├── security.py
│   │   └── review.py
│   ├── linters/                    # Linter configs
│   │   ├── .eslintrc.js
│   │   ├── .prettierrc
│   │   └── pyproject.toml
│   └── runners/                    # Test runner configs
│
├── browser/                        # Browser container
│   ├── supervisord.conf
│   └── profiles/                   # Browser profiles
│
├── monitoring/                     # Monitoring config
│   ├── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   └── alerts/
│
├── data/                           # Persistent data (gitignored)
│   ├── chromadb/
│   ├── sqlite/
│   ├── postgres/
│   ├── redis/
│   └── minio/
│
├── workspace/                      # Project workspace (mount ~/Dev)
├── objectives/                     # Drop objectives here
├── questions/                      # Questions from CLOPUS
├── answers/                        # User answers
├── output/                         # Completed work
└── logs/                           # System logs
```

---

## 15. Deployment & Operations

### 15.1 Installation

```bash
# ONE-LINER INSTALL (recommended)
curl -sSL https://raw.githubusercontent.com/USERNAME/clopus/main/install.sh | bash

# MANUAL INSTALL
git clone https://github.com/USERNAME/clopus.git ~/Dev/clopus
cd ~/Dev/clopus
./setup.sh

# SETUP.SH DOES:
# 1. Check prerequisites (Docker, git, gh CLI)
# 2. Install missing dependencies
# 3. Copy .env.example to .env
# 4. Prompt for ANTHROPIC_API_KEY
# 5. Pull Docker images
# 6. Initialize databases
# 7. Clone skills/templates from GitHub
```

### 15.2 Configuration

```yaml
# config.yaml

system:
  name: "clopus"
  version: "3.0.0"
  log_level: "INFO"

auth:
  mode: "hybrid"  # api | login | hybrid
  api_key_env: "ANTHROPIC_API_KEY"
  session_path: "~/.anthropic"

workers:
  count: 5
  roles:
    - coder
    - tester
    - reviewer
    - researcher
    - debugger
  max_concurrent_tasks: 3

memory:
  short_term:
    type: "sqlite"
    path: "./data/sqlite/clopus.db"
    max_entries: 1000
  long_term:
    type: "chromadb"
    host: "chromadb"
    port: 8000
    collection: "clopus_memory"

validation:
  strict: true
  coverage_threshold: 80
  max_failures: 5
  stages:
    - syntax
    - lint
    - build
    - unit_tests
    - integration_tests
    - e2e_tests
    - security
    - review

confidence:
  threshold: 0.7
  learning_enabled: true

github:
  auto_push: true
  create_repos: true
  default_visibility: "private"
  sync_skills: true
  sync_templates: true
  sync_mcps: true

services:
  tier1:  # Always running
    - postgres
    - redis
    - minio
    - chromadb
    - browser
    - traefik
    - mailhog
  tier2:  # On-demand
    - mongodb
    - mysql
    - elasticsearch
    - rabbitmq

email:
  provider: "resend"  # resend | smtp
  resend_api_key_env: "RESEND_API_KEY"
  smtp:
    host: "smtp.example.com"
    port: 587
    user_env: "SMTP_USER"
    password_env: "SMTP_PASSWORD"

browser:
  mcp_enabled: true
  container_enabled: true
  vnc_port: 6080
  profiles_path: "./browser/profiles"

interfaces:
  cli:
    enabled: true
  file:
    enabled: true
    watch_interval: 1000
  webhook:
    enabled: false
    port: 8080
```

### 15.3 Usage Examples

```bash
# EXAMPLE 1: Build a SaaS application
./clopus start
./clopus objective "Build a SaaS invoicing application with:
- React TypeScript frontend
- FastAPI Python backend
- PostgreSQL database
- Stripe payment integration
- Email notifications via Resend
- User authentication with JWT
- Deploy to Railway"

# CLOPUS will:
# 1. Create github.com/USERNAME/invoice-saas repo
# 2. Apply saas-starter template
# 3. Implement all features
# 4. Run validation pipeline
# 5. Deploy to Railway
# 6. Extract template for future use
# 7. Push template to github.com/USERNAME/clopus

# EXAMPLE 2: Video processing pipeline
./clopus objective "Create a video processing pipeline that:
- Accepts video uploads
- Transcribes audio with Whisper
- Generates subtitles
- Creates thumbnail images
- Outputs processed video"

# EXAMPLE 3: Cold outreach system
./clopus objective "Build a cold email outreach system:
- Lead scraping from LinkedIn
- Email personalization
- Automated follow-ups
- Response tracking
- CRM integration"

# EXAMPLE 4: Mobile app
./clopus objective "Build a React Native Expo app for:
- Task management
- Push notifications
- Offline support
- Sync with backend API
- Deploy to App Store and Play Store"
```

### 15.4 Operations

```bash
# MONITORING
./clopus status --watch           # Real-time status
open http://localhost:3000        # Grafana dashboard
open http://localhost:6080        # Browser VNC

# DEBUGGING
./clopus logs -f                  # Follow all logs
./clopus logs --worker 2          # Specific worker
./clopus memory search "error"    # Search memory for errors

# MAINTENANCE
./clopus gc                       # Clean up old data
./clopus backup                   # Backup to S3/local
./clopus restore backup.tar.gz    # Restore from backup

# SCALING
./clopus scale workers 10         # Increase workers
./clopus scale down               # Scale down to minimum

# UPDATES
./clopus update                   # Update CLOPUS
./clopus skills pull              # Pull latest skills
./clopus templates pull           # Pull latest templates
```

---

## 16. Security Considerations

### 16.1 Security Model

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY MODEL                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  CREDENTIAL MANAGEMENT                                                               │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • API keys stored in .env (gitignored)                                      │   │
│  │  • Claude session in ~/.anthropic/ (gitignored)                              │   │
│  │  • No credentials in code or logs                                            │   │
│  │  • Credentials passed via environment variables                               │   │
│  │  • Support for external secret managers (Vault, AWS Secrets)                 │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  CONTAINER ISOLATION                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • Each worker runs in isolated container                                    │   │
│  │  • Limited host filesystem access (only ~/Dev, credentials)                  │   │
│  │  • Network isolation between services                                        │   │
│  │  • Resource limits (CPU, memory) configurable                                │   │
│  │  • Read-only mounts where possible                                           │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  CODE VALIDATION                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • All generated code passes security scan (Stage 7)                         │   │
│  │  • Dependency vulnerability checking                                         │   │
│  │  • Secret detection in code                                                  │   │
│  │  • OWASP Top 10 checks                                                       │   │
│  │  • Reviewer worker security assessment                                       │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  DATA PROTECTION                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • Memory database encrypted at rest (optional)                              │   │
│  │  • No PII stored in memory unless explicitly required                        │   │
│  │  • Template extraction anonymizes sensitive data                             │   │
│  │  • GitHub repos default to private                                           │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ACCESS CONTROL                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  • Single-user system (your machine)                                         │   │
│  │  • GitHub access via gh CLI (your auth)                                      │   │
│  │  • External services use your credentials                                    │   │
│  │  • No shared access or multi-tenancy                                         │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 16.2 Best Practices

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY BEST PRACTICES                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  DO:                                                                                 │
│  ✓ Keep .env out of version control                                                 │
│  ✓ Regularly rotate API keys                                                        │
│  ✓ Review generated code before deploying to production                             │
│  ✓ Use private repos for sensitive projects                                         │
│  ✓ Enable security scanning in validation pipeline                                  │
│  ✓ Keep CLOPUS and dependencies updated                                             │
│  ✓ Use HTTPS for all external communications                                        │
│  ✓ Monitor logs for unusual activity                                                │
│                                                                                      │
│  DON'T:                                                                              │
│  ✗ Store production credentials in CLOPUS                                           │
│  ✗ Give CLOPUS access to production databases directly                              │
│  ✗ Deploy generated code without review for critical systems                        │
│  ✗ Share your CLOPUS installation with untrusted users                              │
│  ✗ Disable security validation stages                                               │
│  ✗ Expose CLOPUS services to the internet without protection                        │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Quick Reference

### A.1 Key Commands

| Command | Description |
|---------|-------------|
| `./clopus start` | Start CLOPUS |
| `./clopus stop` | Stop CLOPUS |
| `./clopus objective "..."` | Give new objective |
| `./clopus status` | Check status |
| `./clopus questions` | View pending questions |
| `./clopus answer <id> "..."` | Answer question |
| `./clopus logs -f` | Follow logs |

### A.2 Key Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables |
| `config.yaml` | System configuration |
| `objectives/*.md` | Drop objectives here |
| `questions/*.md` | Questions appear here |
| `answers/*.md` | Put answers here |

### A.3 Key Ports

| Port | Service |
|------|---------|
| 3000 | Grafana |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 6080 | Browser VNC |
| 8025 | Mailhog |
| 8080 | Traefik |

---

## Appendix B: Comparison with Clopus-02

| Feature | Clopus-02 | CLOPUS v3 |
|---------|-----------|-----------|
| Workers | 1 | 5 (configurable) |
| Memory | SQLite + Qdrant | SQLite + ChromaDB |
| Validation | None | 8-stage strict |
| Skills | Static | Self-generating |
| MCPs | Fixed | Auto-generating |
| Templates | None | Auto-extracting |
| Browser | Chromium only | MCP + Container |
| Auth | API only | API + Claude Login |
| Output | Local only | GitHub synced |
| Guidance | Autonomous only | Confidence-based |
| Deployment | Manual | One-liner |

---

*Document Version: 3.0.0*
*Last Updated: 2025-12-26*

