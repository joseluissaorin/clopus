---
name: test-strategies
description: Comprehensive testing patterns for different languages and frameworks. Use when writing or reviewing tests.
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Test Strategies Skill

Comprehensive testing patterns and best practices for CLOPUS projects.

## Python Testing (pytest)

### Unit Tests
```python
import pytest
from app.services.calculator import Calculator

class TestCalculator:
    def setup_method(self):
        self.calc = Calculator()

    def test_add_positive_numbers(self):
        assert self.calc.add(2, 3) == 5

    def test_add_negative_numbers(self):
        assert self.calc.add(-1, -1) == -2

    def test_add_zero(self):
        assert self.calc.add(0, 5) == 5

    @pytest.mark.parametrize("a,b,expected", [
        (1, 1, 2),
        (0, 0, 0),
        (-1, 1, 0),
    ])
    def test_add_parametrized(self, a, b, expected):
        assert self.calc.add(a, b) == expected
```

### API Tests (FastAPI)
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

class TestUserAPI:
    def test_create_user(self, client):
        response = client.post(
            "/api/v1/users",
            json={"email": "test@example.com", "name": "Test"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data

    def test_create_user_invalid_email(self, client):
        response = client.post(
            "/api/v1/users",
            json={"email": "invalid", "name": "Test"}
        )
        assert response.status_code == 422

    def test_get_user(self, client):
        # Create user first
        create_response = client.post(
            "/api/v1/users",
            json={"email": "test@example.com", "name": "Test"}
        )
        user_id = create_response.json()["id"]

        # Get user
        response = client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_get_user_not_found(self, client):
        response = client.get("/api/v1/users/nonexistent-id")
        assert response.status_code == 404
```

## JavaScript/TypeScript Testing

### Vitest Unit Tests
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Calculator } from './calculator'

describe('Calculator', () => {
  let calc: Calculator

  beforeEach(() => {
    calc = new Calculator()
  })

  it('adds positive numbers', () => {
    expect(calc.add(2, 3)).toBe(5)
  })

  it('handles negative numbers', () => {
    expect(calc.add(-1, -1)).toBe(-2)
  })
})
```

### React Component Tests
```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TodoList } from './TodoList'

describe('TodoList', () => {
  it('renders empty state', () => {
    render(<TodoList todos={[]} onAdd={vi.fn()} />)
    expect(screen.getByText(/no todos/i)).toBeInTheDocument()
  })

  it('renders todos', () => {
    const todos = [
      { id: '1', text: 'First todo', completed: false },
      { id: '2', text: 'Second todo', completed: true },
    ]
    render(<TodoList todos={todos} onAdd={vi.fn()} />)
    expect(screen.getByText('First todo')).toBeInTheDocument()
    expect(screen.getByText('Second todo')).toBeInTheDocument()
  })

  it('calls onAdd when form is submitted', () => {
    const onAdd = vi.fn()
    render(<TodoList todos={[]} onAdd={onAdd} />)

    const input = screen.getByPlaceholderText(/add todo/i)
    fireEvent.change(input, { target: { value: 'New todo' } })
    fireEvent.submit(screen.getByRole('form'))

    expect(onAdd).toHaveBeenCalledWith('New todo')
  })
})
```

## E2E Testing (Playwright)

```typescript
import { test, expect } from '@playwright/test'

test.describe('Todo App', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3142')
  })

  test('shows empty state initially', async ({ page }) => {
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible()
  })

  test('can add a todo', async ({ page }) => {
    await page.fill('[data-testid="todo-input"]', 'New todo item')
    await page.click('[data-testid="add-button"]')

    await expect(page.locator('[data-testid="todo-item"]')).toContainText('New todo item')
    await page.screenshot({ path: 'screenshots/todo-added.png' })
  })

  test('can complete a todo', async ({ page }) => {
    // Add a todo first
    await page.fill('[data-testid="todo-input"]', 'Complete me')
    await page.click('[data-testid="add-button"]')

    // Complete it
    await page.click('[data-testid="todo-checkbox"]')
    await expect(page.locator('[data-testid="todo-item"]')).toHaveClass(/completed/)
  })

  test('can delete a todo', async ({ page }) => {
    // Add a todo first
    await page.fill('[data-testid="todo-input"]', 'Delete me')
    await page.click('[data-testid="add-button"]')

    // Delete it
    await page.click('[data-testid="delete-button"]')
    await expect(page.locator('[data-testid="todo-item"]')).not.toBeVisible()
  })
})
```

## Running Tests

### Python
```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_users.py -v

# Run specific test
pytest tests/test_users.py::TestUserAPI::test_create_user -v
```

### JavaScript/TypeScript
```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific file
npm test -- todo.test.ts

# Watch mode
npm test -- --watch
```

### Playwright E2E
```bash
# Run all E2E tests
npx playwright test

# Run with UI
npx playwright test --ui

# Run specific test
npx playwright test tests/todo.spec.ts

# Generate report
npx playwright show-report
```
