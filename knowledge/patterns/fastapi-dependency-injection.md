---
title: "FastAPI Dependency Injection Pattern"
type: pattern
technologies: [python, fastapi, sqlalchemy]
confidence: 0.92
created: 2025-12-26
last_used: 2025-12-26
use_count: 0
---

# FastAPI Dependency Injection Pattern

A pattern for managing database sessions and other dependencies in FastAPI.

## Context

Use this pattern when:
- Building FastAPI applications with database access
- Need clean dependency management
- Want testable, modular code
- Using SQLAlchemy with async support

## Implementation

### 1. Database Setup

```python
# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()
```

### 2. Dependency Function

```python
# dependencies.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 3. Use in Routes

```python
# routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .dependencies import get_db
from .models import User
from .schemas import UserCreate, UserResponse

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = User(**user_data.model_dump())
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
```

### 4. Authentication Dependency

```python
# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from .dependencies import get_db

security = HTTPBearer()

async def get_current_user(
    credentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    user = await verify_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )
    return user
```

## Testing

```python
# test_routes.py
import pytest
from httpx import AsyncClient

@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture
def app_with_db(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield app
    app.dependency_overrides.clear()
```

## Benefits

- Clean separation of concerns
- Easy testing with dependency overrides
- Automatic session management
- Type-safe with full IDE support
