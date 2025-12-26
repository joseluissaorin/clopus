---
name: nextjs-fullstack
description: Build full-stack Next.js applications with App Router, Server Components, and API routes
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
  - Glob
  - Grep
triggers:
  - nextjs
  - next.js
  - fullstack
  - app router
  - server components
  - react server
---

# Next.js Full-Stack Development

## Context

You are an expert Next.js developer building modern full-stack applications using:
- Next.js 14+ with App Router
- React Server Components
- Server Actions
- TypeScript
- Tailwind CSS
- Prisma ORM (optional)

## Project Structure

```
src/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx             # Home page
│   ├── globals.css          # Global styles
│   ├── api/                 # API routes
│   │   └── [route]/route.ts
│   ├── (auth)/              # Auth route group
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── dashboard/
│       ├── layout.tsx
│       └── page.tsx
├── components/
│   ├── ui/                  # Reusable UI components
│   └── forms/               # Form components
├── lib/
│   ├── db.ts                # Database client
│   ├── auth.ts              # Auth utilities
│   └── utils.ts             # Helper functions
├── actions/                 # Server Actions
│   └── user.ts
└── types/
    └── index.ts
```

## Instructions

### 1. Project Initialization

```bash
npx create-next-app@latest my-app --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd my-app
```

### 2. Server Components (Default)

Server Components are the default in App Router:

```tsx
// app/users/page.tsx
import { db } from '@/lib/db'

export default async function UsersPage() {
  const users = await db.user.findMany()

  return (
    <div>
      {users.map(user => (
        <div key={user.id}>{user.name}</div>
      ))}
    </div>
  )
}
```

### 3. Client Components

Add 'use client' directive for interactivity:

```tsx
'use client'

import { useState } from 'react'

export function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>
}
```

### 4. Server Actions

```tsx
// actions/user.ts
'use server'

import { db } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function createUser(formData: FormData) {
  const name = formData.get('name') as string

  await db.user.create({ data: { name } })
  revalidatePath('/users')
}
```

### 5. API Routes

```tsx
// app/api/users/route.ts
import { NextResponse } from 'next/server'

export async function GET() {
  const users = await db.user.findMany()
  return NextResponse.json(users)
}

export async function POST(request: Request) {
  const body = await request.json()
  const user = await db.user.create({ data: body })
  return NextResponse.json(user, { status: 201 })
}
```

### 6. Middleware

```tsx
// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*']
}
```

## Best Practices

1. **Use Server Components by default** - Only add 'use client' when needed
2. **Colocate data fetching** - Fetch data where it's used
3. **Use Server Actions for mutations** - Simpler than API routes
4. **Implement proper error boundaries** - error.tsx files
5. **Add loading states** - loading.tsx files
6. **Use route groups** - (group) folders for organization
7. **Validate with Zod** - Type-safe form validation
8. **Use Suspense boundaries** - For streaming and loading states

## Common Patterns

### Authentication with NextAuth.js

```bash
npm install next-auth @auth/prisma-adapter
```

### Database with Prisma

```bash
npm install prisma @prisma/client
npx prisma init
```

### Form Handling with React Hook Form

```bash
npm install react-hook-form @hookform/resolvers zod
```

## Validation

- All pages should export proper metadata
- Use TypeScript strict mode
- Implement proper error handling
- Add loading and error states
- Test with Playwright for E2E
