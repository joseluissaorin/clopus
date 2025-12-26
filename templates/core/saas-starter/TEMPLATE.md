# SaaS Starter Template

A complete SaaS application scaffold with authentication, billing, and dashboard.

## Project Type

nextjs

## Technologies

Next.js 14, TypeScript, Tailwind CSS, Prisma, Stripe, NextAuth.js

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| PROJECT_NAME | Project name | my-saas |
| DESCRIPTION | Project description | A modern SaaS application |
| DATABASE_URL | Database connection string | postgresql://localhost/myapp |

## Structure

```
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/
│   │   │   ├── dashboard/
│   │   │   ├── settings/
│   │   │   └── billing/
│   │   ├── api/
│   │   │   ├── auth/
│   │   │   ├── stripe/
│   │   │   └── users/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/
│   │   ├── forms/
│   │   └── layout/
│   ├── lib/
│   │   ├── auth.ts
│   │   ├── db.ts
│   │   └── stripe.ts
│   └── types/
├── prisma/
│   └── schema.prisma
├── public/
├── package.json
└── tailwind.config.ts
```

## Features

- User authentication with NextAuth.js
- Email/password and OAuth providers
- Stripe subscription management
- Responsive dashboard layout
- Dark mode support
- Database with Prisma ORM
- Form validation with Zod
- Toast notifications

## Usage

```bash
clopus template use saas-starter my-new-saas
cd my-new-saas
npm install
npx prisma migrate dev
npm run dev
```

---
CLOPUS Core Template
