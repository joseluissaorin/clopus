# Nexus - Personal Knowledge Operating System

Build **NEXUS**, an ambitious full-stack web application that combines three powerful systems into one cohesive personal operating system:

## 1. Knowledge Graph (Core Foundation)

A visual, interconnected knowledge base where everything connects:

- **Nodes**: Notes, ideas, concepts, people, projects, resources, decisions, learnings
- **Edges**: Typed relationships (relates-to, depends-on, inspired-by, contradicts, supports, led-to)
- **Visual Canvas**: Interactive graph visualization with:
  - Zoom, pan, drag nodes
  - Cluster detection (auto-group related concepts)
  - Path finding (how does X connect to Y?)
  - Heat maps (frequently accessed vs dormant knowledge)
- **Smart Linking**: Auto-suggest connections based on content similarity
- **Bi-directional Links**: Every link works both ways
- **Quick Capture**: Cmd+K to quickly add a new node from anywhere
- **Tags & Namespaces**: Organize into domains (work, personal, learning, etc.)

## 2. Decision Journal (Decision Intelligence)

Track and learn from every significant decision:

- **Decision Records**:
  - What decision was made?
  - What were the options considered?
  - What was the rationale?
  - What assumptions were made?
  - What's the expected outcome?
  - What's the review date?
- **Outcome Tracking**:
  - Did the decision work out?
  - What actually happened vs expected?
  - What would you do differently?
  - Link to relevant knowledge graph nodes
- **Decision Patterns**:
  - Visualize decision quality over time
  - Identify biases (do you always avoid risk? always choose familiar?)
  - Track domains (am I better at tech decisions vs people decisions?)
- **Decision Templates**: Quick templates for different types (hiring, technical, investment, life)
- **Integration with Knowledge Graph**: Decisions become nodes, outcomes inform future decisions

## 3. Work Command Center (Freelancer Hub)

Manage freelance/consulting work like a pro:

- **Client Management**:
  - Client profiles with history
  - Communication log (emails, calls, meetings)
  - Project history
  - Satisfaction tracking
  - Client health score
- **Project Tracking**:
  - Kanban boards per project
  - Milestones and deliverables
  - Status updates
  - Blockers and risks
  - Link to relevant knowledge graph nodes
- **Time Tracking**:
  - Timer with project/task selection
  - Manual time entry
  - Weekly/monthly summaries
  - Billable vs non-billable
  - Productivity insights
- **Invoicing**:
  - Generate invoices from time entries
  - Invoice templates
  - Payment tracking
  - Send reminders
  - Revenue dashboard
- **Financial Overview**:
  - Revenue by client, project, month
  - Outstanding invoices
  - Cash flow projection
  - Tax estimation

## Technical Requirements

### Frontend
- React 18 with TypeScript (strict mode)
- Tailwind CSS for styling
- D3.js or Vis.js for the knowledge graph visualization
- Framer Motion for smooth animations
- React Query for data fetching
- Zustand for state management

### Backend API
- Express.js API or Next.js API routes
- JWT authentication
- SQLite with better-sqlite3 for persistence
- Full CRUD for all entities

### Design System
- Create a distinctive, professional design system
- Dark mode by default (with light mode toggle)
- Consistent spacing, typography, and color palette
- Micro-interactions and transitions
- Responsive (desktop-first, but mobile-usable)

### Key Features
- **Unified Search**: Search across all three systems (Cmd+K)
- **Dashboard**: Overview of knowledge graph stats, pending decisions, active projects, revenue
- **Cross-Linking**: Everything can link to everything (clients to knowledge, decisions to projects, etc.)
- **Export**: Export knowledge graph, decisions, or financial reports
- **Keyboard Navigation**: Power-user friendly with extensive keyboard shortcuts

## Success Criteria

1. Knowledge graph renders smoothly with 100+ nodes
2. Can create, link, and navigate between nodes visually
3. Decision journal captures and tracks decisions with outcomes
4. Client/project management is fully functional
5. Time tracking and basic invoicing works
6. Unified search finds content across all systems
7. All validation stages pass (lint, tests, build)
8. Professional, cohesive design throughout
9. Dev server runs and all features are accessible

This is intentionally ambitious. It will test planning, coordination between workers, design consistency, and the ability to deliver a complex, interconnected system.
