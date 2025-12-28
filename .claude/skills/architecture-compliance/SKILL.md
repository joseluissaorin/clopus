---
name: architecture-compliance
description: Ensures code follows CLOPUS architectural patterns. Use proactively when writing or reviewing API endpoints, database operations, or service layers.
allowed-tools: Read, Grep, Glob
---

# Architecture Compliance Skill

This skill ensures code follows CLOPUS architectural standards and patterns.

## Critical Requirements

### 1. Database Integration (API Projects)

When CLAUDE.md specifies PostgreSQL/database:

**REQUIRED:**
```python
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.{resource} import {Resource}

@router.post("", response_model={Resource}Response)
async def create_{resource}(
    data: {Resource}Create,
    db: Session = Depends(get_db)  # <-- ALWAYS REQUIRED
):
    db_obj = {Resource}(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
```

**FORBIDDEN:**
```python
# NEVER DO THIS:
_db: dict = {}  # In-memory storage
_storage = {}   # In-memory storage
_users: list = []  # In-memory list

# NEVER SKIP DATABASE DEPENDENCY:
@router.post("/users")
async def create_user(user: UserCreate):  # WRONG - missing db dependency
    _users.append(user)  # WRONG - using in-memory storage
```

### 2. Layered Architecture

```
┌─────────────────────┐
│     API Layer       │  ← FastAPI routers, request/response handling
├─────────────────────┤
│   Service Layer     │  ← Business logic, orchestration
├─────────────────────┤
│  Repository Layer   │  ← Database operations
├─────────────────────┤
│    Model Layer      │  ← SQLAlchemy models, Pydantic schemas
├─────────────────────┤
│   Database Layer    │  ← Connection, sessions, migrations
└─────────────────────┘
```

### 3. File Organization

```
app/
├── api/
│   └── v1/
│       └── endpoints/
│           ├── __init__.py
│           ├── users.py      # User endpoints
│           └── items.py      # Item endpoints
├── models/
│   ├── __init__.py
│   ├── user.py               # User SQLAlchemy model
│   └── item.py               # Item SQLAlchemy model
├── schemas/
│   ├── __init__.py
│   ├── user.py               # User Pydantic schemas
│   └── item.py               # Item Pydantic schemas
├── db/
│   ├── __init__.py
│   ├── base.py               # SQLAlchemy Base
│   └── session.py            # Database session
├── core/
│   ├── __init__.py
│   └── config.py             # Configuration
└── main.py                   # FastAPI app
```

## Validation Commands

Check for in-memory storage anti-patterns:
!`grep -rn "_db\s*:\s*dict\|_storage\s*=\|_db\s*=\s*{}" --include="*.py" /workspace/app/`

Check for missing Depends(get_db):
!`grep -rn "@router\." --include="*.py" -A5 /workspace/app/api/ | grep -v "Depends(get_db)"`

## Before You Code

1. Read CLAUDE.md to understand project requirements
2. Check if database integration is required
3. Follow the patterns above
4. Never use in-memory storage for persistent data
