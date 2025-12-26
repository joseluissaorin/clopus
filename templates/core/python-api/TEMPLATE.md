# Python API Template

Production-ready FastAPI backend with database, auth, and testing.

## Project Type

python

## Technologies

Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, Docker

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| PROJECT_NAME | Project name | my-api |
| DESCRIPTION | Project description | A FastAPI backend |
| DATABASE_URL | Database connection string | postgresql://localhost/mydb |

## Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── users.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py
│   └── utils/
│       ├── __init__.py
│       └── security.py
├── alembic/
│   └── versions/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_users.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── alembic.ini
```

## Features

- FastAPI with async support
- SQLAlchemy ORM with migrations
- JWT authentication
- Pydantic validation
- Comprehensive testing
- Docker ready
- OpenAPI documentation

## Usage

```bash
clopus template use python-api my-new-api
cd my-new-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

---
CLOPUS Core Template
