---
title: "React Hook Form with Zod Validation"
type: pattern
technologies: [react, typescript, zod, react-hook-form]
confidence: 0.95
created: 2025-12-26
last_used: 2025-12-26
use_count: 0
---

# React Hook Form with Zod Validation

A reusable pattern for type-safe form handling in React applications.

## Context

Use this pattern when:
- Building forms in React/Next.js applications
- Need type-safe form validation
- Want to avoid manual validation logic
- Building forms with complex validation rules

## Implementation

### 1. Define Schema

```typescript
import { z } from "zod";

const formSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type FormData = z.infer<typeof formSchema>;
```

### 2. Create Form Component

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

function MyForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  });

  const onSubmit = async (data: FormData) => {
    // Handle form submission
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("email")} />
      {errors.email && <span>{errors.email.message}</span>}

      <input type="password" {...register("password")} />
      {errors.password && <span>{errors.password.message}</span>}

      <input type="password" {...register("confirmPassword")} />
      {errors.confirmPassword && <span>{errors.confirmPassword.message}</span>}

      <button type="submit" disabled={isSubmitting}>
        Submit
      </button>
    </form>
  );
}
```

## Dependencies

```json
{
  "react-hook-form": "^7.0.0",
  "zod": "^3.0.0",
  "@hookform/resolvers": "^3.0.0"
}
```

## Benefits

- Full TypeScript support with inferred types
- Declarative validation rules
- Efficient re-renders (only invalid fields)
- Easy to test and maintain
