# NEXUS Web Frontend

Build the **React frontend** for NEXUS - a visual, interconnected knowledge base.

## Project Name
nexus-web

## Project Type
dashboard

## Related Projects
- **nexus-api**: Backend API at `/workspace/nexus-api`
  - OpenAPI spec: `http://localhost:8000/api/v1/openapi.json`
  - API docs: `http://localhost:8000/api/v1/docs`
  - Base URL: `http://localhost:8000/api/v1`

## Technology Stack
- React 18 with TypeScript
- Vite for build tooling
- TailwindCSS for styling
- React Query (TanStack Query) for API state management
- React Flow or Cytoscape.js for graph visualization
- Zustand for local state management

## Core Features

### 1. Visual Canvas (Priority 1)
Interactive graph visualization where:
- **Nodes** represent: notes, ideas, concepts, people, projects, resources
- **Edges** represent: typed relationships (relates-to, depends-on, inspired-by, contradicts, supports)
- Canvas interactions: zoom, pan, drag nodes, select, multi-select
- Cluster detection and visual grouping
- Mini-map for navigation

### 2. Node Management
- Quick node creation (keyboard shortcut: Cmd/Ctrl+K)
- Node types with distinct visual styles
- Rich text content editing
- Tags and metadata
- Search and filter

### 3. Edge Management
- Click-and-drag edge creation
- Typed edge relationships with labels
- Bi-directional link awareness
- Edge strength/weight visualization

### 4. Smart Features
- Auto-suggest connections based on content similarity
- Quick capture sidebar
- Full-text search across all nodes
- Filter by node type, tags, relationships

## API Integration

Connect to the nexus-api backend:
- Fetch OpenAPI spec for type generation
- Use the generated types for type-safe API calls
- Implement all CRUD operations for nodes and edges
- Handle optimistic updates with React Query

## Design Requirements
- Dark mode support (default: dark)
- Responsive layout (but optimized for desktop)
- Smooth animations for graph transitions
- Clear visual hierarchy
- Keyboard navigation support

## File Structure
```
nexus-web/
├── src/
│   ├── api/              # API client and types (from OpenAPI)
│   ├── components/       # React components
│   │   ├── canvas/       # Graph visualization components
│   │   ├── nodes/        # Node-related components
│   │   ├── edges/        # Edge-related components
│   │   └── ui/           # Shared UI components
│   ├── hooks/            # Custom React hooks
│   ├── stores/           # Zustand stores
│   ├── types/            # TypeScript types
│   └── utils/            # Utility functions
├── public/
└── index.html
```

## Validation Requirements
- All code must pass linting (ESLint)
- TypeScript strict mode
- Unit tests for critical components
- E2E tests for main user flows
- Build must succeed without errors

## Notes
- The API is running at http://localhost:8000
- Use proxy in vite.config.ts to avoid CORS issues in development
- The frontend should work even if the API is not running (show appropriate error states)
