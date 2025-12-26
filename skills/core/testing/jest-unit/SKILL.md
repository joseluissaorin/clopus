---
name: jest-unit
description: Write comprehensive unit tests with Jest for JavaScript/TypeScript
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
  - Glob
triggers:
  - jest
  - unit test
  - javascript test
  - typescript test
  - testing
---

# Jest Unit Testing

## Context

You are an expert in testing JavaScript/TypeScript applications using:
- Jest test framework
- Testing Library (React, DOM)
- Mock functions and modules
- Code coverage analysis

## Test Structure

```
src/
├── components/
│   ├── Button.tsx
│   └── Button.test.tsx      # Component test
├── utils/
│   ├── format.ts
│   └── format.test.ts       # Unit test
├── hooks/
│   ├── useAuth.ts
│   └── useAuth.test.ts      # Hook test
├── services/
│   ├── api.ts
│   └── api.test.ts          # Service test
└── __mocks__/               # Manual mocks
    └── axios.ts
```

## Instructions

### 1. Jest Configuration

```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/src'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss)$': 'identity-obj-proxy',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/index.tsx',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

### 2. Basic Unit Test

```typescript
// utils/format.test.ts
import { formatCurrency, formatDate } from './format';

describe('formatCurrency', () => {
  it('formats positive numbers correctly', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56');
  });

  it('handles zero', () => {
    expect(formatCurrency(0)).toBe('$0.00');
  });

  it('formats negative numbers with parentheses', () => {
    expect(formatCurrency(-100)).toBe('($100.00)');
  });

  it.each([
    [1000, '$1,000.00'],
    [1000000, '$1,000,000.00'],
    [0.99, '$0.99'],
  ])('formatCurrency(%d) returns %s', (input, expected) => {
    expect(formatCurrency(input)).toBe(expected);
  });
});
```

### 3. Mocking Functions

```typescript
// services/api.test.ts
import { fetchUsers, createUser } from './api';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchUsers', () => {
    it('returns users on success', async () => {
      const users = [{ id: 1, name: 'John' }];
      mockedAxios.get.mockResolvedValueOnce({ data: users });

      const result = await fetchUsers();

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/users');
      expect(result).toEqual(users);
    });

    it('throws error on failure', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));

      await expect(fetchUsers()).rejects.toThrow('Network error');
    });
  });
});
```

### 4. Testing React Components

```typescript
// components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    await userEvent.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows loading spinner when loading', () => {
    render(<Button loading>Click me</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByTestId('spinner')).toBeInTheDocument();
  });
});
```

### 5. Testing Hooks

```typescript
// hooks/useCounter.test.ts
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('starts with initial value', () => {
    const { result } = renderHook(() => useCounter(10));
    expect(result.current.count).toBe(10);
  });

  it('increments the count', () => {
    const { result } = renderHook(() => useCounter(0));

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });

  it('decrements the count', () => {
    const { result } = renderHook(() => useCounter(5));

    act(() => {
      result.current.decrement();
    });

    expect(result.current.count).toBe(4);
  });
});
```

### 6. Async Testing

```typescript
// utils/async.test.ts
describe('async operations', () => {
  it('waits for promise resolution', async () => {
    const result = await fetchData();
    expect(result).toBeDefined();
  });

  it('handles async errors', async () => {
    await expect(fetchWithError()).rejects.toThrow('Error message');
  });

  it('uses fake timers', () => {
    jest.useFakeTimers();

    const callback = jest.fn();
    setTimeout(callback, 1000);

    jest.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalled();

    jest.useRealTimers();
  });
});
```

## Best Practices

1. **Arrange-Act-Assert** - Clear test structure
2. **Test behavior, not implementation** - Focus on outcomes
3. **One assertion per test** - When practical
4. **Descriptive test names** - Explain what's being tested
5. **Use test.each** - For parameterized tests
6. **Mock at boundaries** - External services, APIs
7. **Maintain test isolation** - Clean up between tests

## Running Tests

```bash
# Run all tests
npm test

# Watch mode
npm test -- --watch

# Coverage report
npm test -- --coverage

# Specific file
npm test -- Button.test.tsx

# Update snapshots
npm test -- -u
```
