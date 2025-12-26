---
name: pytest-python
description: Write comprehensive Python tests with pytest
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
  - Glob
triggers:
  - pytest
  - python test
  - python testing
  - unit test python
---

# Python Testing with pytest

## Context

You are an expert in testing Python applications using:
- pytest framework
- pytest-cov for coverage
- pytest-asyncio for async tests
- unittest.mock for mocking
- Factory Boy for test data

## Test Structure

```
project/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── services/
│       │   └── user_service.py
│       └── models/
│           └── user.py
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── unit/
│   │   ├── test_user_service.py
│   │   └── test_models.py
│   ├── integration/
│   │   └── test_api.py
│   └── factories.py          # Test data factories
├── pytest.ini
└── pyproject.toml
```

## Instructions

### 1. pytest Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
asyncio_mode = auto
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
omit = ["*/__init__.py", "*/tests/*"]

[tool.coverage.report]
fail_under = 80
```

### 2. Basic Unit Tests

```python
# tests/unit/test_calculator.py
import pytest
from myapp.calculator import Calculator


class TestCalculator:
    def test_add_positive_numbers(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5

    def test_add_negative_numbers(self):
        calc = Calculator()
        assert calc.add(-2, -3) == -5

    def test_divide_by_zero_raises_error(self):
        calc = Calculator()
        with pytest.raises(ZeroDivisionError):
            calc.divide(10, 0)

    @pytest.mark.parametrize("a,b,expected", [
        (1, 1, 2),
        (0, 0, 0),
        (-1, 1, 0),
        (100, 200, 300),
    ])
    def test_add_parametrized(self, a, b, expected):
        calc = Calculator()
        assert calc.add(a, b) == expected
```

### 3. Fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from myapp.database import Base
from myapp.models import User


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine):
    """Create a new database session for each test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for tests."""
    user = User(email="test@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(sample_user):
    """Generate auth headers for API tests."""
    token = create_access_token(sample_user.id)
    return {"Authorization": f"Bearer {token}"}
```

### 4. Mocking

```python
# tests/unit/test_user_service.py
from unittest.mock import Mock, patch, AsyncMock
import pytest
from myapp.services.user_service import UserService


class TestUserService:
    @patch("myapp.services.user_service.send_email")
    def test_create_user_sends_welcome_email(self, mock_send_email):
        service = UserService()

        user = service.create_user("test@example.com", "password")

        mock_send_email.assert_called_once_with(
            to="test@example.com",
            template="welcome"
        )

    @patch("myapp.services.user_service.ExternalAPI")
    def test_sync_with_external_api(self, MockAPI):
        mock_api = Mock()
        mock_api.get_user_data.return_value = {"id": 1, "status": "active"}
        MockAPI.return_value = mock_api

        service = UserService()
        result = service.sync_user(1)

        assert result["status"] == "active"
        mock_api.get_user_data.assert_called_with(user_id=1)


class TestAsyncUserService:
    @pytest.mark.asyncio
    async def test_async_fetch_user(self):
        service = UserService()

        with patch.object(service, "fetch_from_api", new_callable=AsyncMock) as mock:
            mock.return_value = {"id": 1, "name": "John"}

            result = await service.async_get_user(1)

            assert result["name"] == "John"
```

### 5. Factory Boy for Test Data

```python
# tests/factories.py
import factory
from myapp.models import User, Post


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    email = factory.LazyAttribute(lambda o: f"user{o.id}@example.com")
    name = factory.Faker("name")
    is_active = True


class PostFactory(factory.Factory):
    class Meta:
        model = Post

    id = factory.Sequence(lambda n: n)
    title = factory.Faker("sentence")
    content = factory.Faker("paragraph")
    author = factory.SubFactory(UserFactory)


# Usage in tests
def test_user_factory():
    user = UserFactory()
    assert user.email.endswith("@example.com")

    users = UserFactory.build_batch(5)
    assert len(users) == 5
```

### 6. Integration Tests

```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from myapp.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestUserAPI:
    def test_create_user(self, client, db_session):
        response = client.post("/users/", json={
            "email": "new@example.com",
            "password": "securepass"
        })

        assert response.status_code == 201
        assert response.json()["email"] == "new@example.com"

    def test_get_user_requires_auth(self, client):
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_get_user_with_auth(self, client, auth_headers):
        response = client.get("/users/me", headers=auth_headers)
        assert response.status_code == 200
```

## Best Practices

1. **Use fixtures** - Share setup code efficiently
2. **Parametrize tests** - Test multiple inputs
3. **Mock external dependencies** - Isolate units
4. **Use factories** - Generate realistic test data
5. **Organize by type** - Separate unit/integration tests
6. **Run fast tests first** - Use pytest-ordering
7. **Check coverage** - Aim for 80%+ coverage

## Running Tests

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Run specific file
pytest tests/unit/test_user_service.py

# Run specific test
pytest tests/unit/test_user_service.py::TestUserService::test_create_user

# Run with coverage
pytest --cov=src --cov-report=html

# Run marked tests
pytest -m "not slow"
pytest -m integration

# Run in parallel
pytest -n auto
```
