---
name: nodejs-express
description: Express.js API development
version: 1.0.0
category: development
technologies: [node, express, typescript, prisma]
triggers:
  - express
  - express.js
  - node api
  - node backend
---

# Node.js Express Development

Expert-level Express.js API development with TypeScript.

## Capabilities

- RESTful API design
- Middleware development
- Authentication (JWT, Passport)
- Database integration (Prisma, TypeORM)
- Input validation (Zod, Joi)
- Error handling
- Rate limiting
- API documentation (Swagger)

## Project Structure

```
project/
├── src/
│   ├── config/
│   │   └── index.ts
│   ├── controllers/
│   ├── middleware/
│   │   ├── auth.ts
│   │   ├── error.ts
│   │   └── validate.ts
│   ├── models/
│   ├── routes/
│   │   └── index.ts
│   ├── services/
│   ├── utils/
│   ├── types/
│   └── app.ts
├── prisma/
│   └── schema.prisma
├── tests/
├── package.json
└── tsconfig.json
```

## Setup

```bash
# Initialize
npm init -y
npm install express cors helmet morgan
npm install -D typescript @types/node @types/express tsx

# Prisma
npm install @prisma/client
npx prisma init

# Validation
npm install zod

# Auth
npm install jsonwebtoken bcryptjs
```

## Middleware Pattern

```typescript
import { Request, Response, NextFunction } from "express";

export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  console.error(err.stack);
  res.status(500).json({ error: "Internal Server Error" });
};
```

## Best Practices

1. Use TypeScript for type safety
2. Validate all inputs with Zod
3. Use async/await with proper error handling
4. Implement rate limiting
5. Use Helmet for security headers
6. Structure routes with versioning (/api/v1)
7. Write integration tests
