---
name: python-fastapi
description: Build APIs with Python and FastAPI
version: 1.0.0
author: CLOPUS
model: claude-sonnet-4-20250514
tags:
  - development
  - backend
  - python
  - api
tools:
  - Bash
  - Read
  - Write
  - Glob
---

# Python FastAPI Development

Expert skill for building REST APIs with FastAPI.

## Capabilities

- Create FastAPI applications with proper structure
- Define Pydantic models for validation
- Implement CRUD endpoints
- Set up database with SQLAlchemy or async databases
- Add authentication (JWT, OAuth)
- Write comprehensive API tests with pytest

## Project Structure

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── routers/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── database.py
├── tests/
│   └── __init__.py
├── requirements.txt
└── pyproject.toml
```

## Example Patterns

### Main Application

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="My API",
    description="API description",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Pydantic Models

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

### Router with CRUD

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=list[User])
async def get_users(db: Session = Depends(get_db)):
    return db.query(UserModel).all()

@router.post("/", response_model=User, status_code=201)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserModel(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```

## Best Practices

1. Use Pydantic for all request/response validation
2. Implement proper error handling with HTTPException
3. Use dependency injection for database sessions
4. Add OpenAPI documentation
5. Write async code where possible
6. Use environment variables for configuration
7. Add comprehensive logging
