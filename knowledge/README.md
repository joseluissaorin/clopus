# CLOPUS Knowledge Base

This directory contains learned knowledge from CLOPUS operations. It serves as a persistent memory of patterns, solutions, and mistakes that inform future decisions.

## Structure

```
knowledge/
├── patterns/      # Reusable code and architecture patterns
├── solutions/     # Complete solutions to specific problems
└── mistakes/      # Anti-patterns and errors to avoid
```

## How Knowledge is Used

1. **During Task Planning**: The orchestrator queries this knowledge base to find relevant patterns and solutions
2. **During Implementation**: Workers consult solutions for similar problems
3. **During Review**: The reviewer checks against known mistakes

## Knowledge Entry Format

Each knowledge entry is a Markdown file with YAML frontmatter:

```markdown
---
title: "Knowledge Entry Title"
type: pattern | solution | mistake
technologies: [react, typescript, fastapi]
confidence: 0.95
created: 2025-12-26
last_used: 2025-12-26
use_count: 5
---

# Description

Detailed description of the pattern, solution, or mistake.

## Context

When this applies.

## Implementation

How to apply (for patterns/solutions) or avoid (for mistakes).

## Examples

Code examples if applicable.
```

## Auto-Population

CLOPUS automatically populates this knowledge base:

- **Patterns**: Extracted when the same code structure is used 3+ times
- **Solutions**: Recorded when a problem is successfully solved
- **Mistakes**: Added when an error is encountered and fixed

## Syncing

All knowledge is synced to the GitHub repository for:
- Version control
- Sharing across CLOPUS instances
- Manual review and curation
