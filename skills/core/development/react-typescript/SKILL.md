---
name: react-typescript
description: Build React applications with TypeScript
version: 1.0.0
author: CLOPUS
model: claude-sonnet-4-20250514
tags:
  - development
  - frontend
  - react
  - typescript
tools:
  - Bash
  - Read
  - Write
  - Glob
---

# React TypeScript Development

Expert skill for building React applications with TypeScript.

## Capabilities

- Create new React/TypeScript projects with Vite or Next.js
- Build functional components with proper typing
- Implement React hooks (useState, useEffect, useContext, custom hooks)
- Set up state management (Context, Zustand, Redux)
- Create reusable component libraries
- Implement responsive layouts with Tailwind CSS
- Write unit tests with Jest and React Testing Library

## Project Setup

When creating a new React TypeScript project:

```bash
# Vite (recommended for SPAs)
npm create vite@latest my-app -- --template react-ts

# Next.js (recommended for SSR/SSG)
npx create-next-app@latest my-app --typescript --tailwind --eslint
```

## Component Patterns

### Functional Component with Props

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
  onClick?: () => void;
}

export function Button({ variant = 'primary', children, onClick }: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
```

### Custom Hook

```typescript
function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}
```

## Best Practices

1. Use TypeScript strictly - no `any` types
2. Prefer functional components and hooks
3. Keep components small and focused
4. Use proper prop types and interfaces
5. Implement error boundaries
6. Optimize with useMemo and useCallback where needed
7. Write tests for critical paths
