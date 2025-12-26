---
name: cypress-testing
description: Cypress E2E testing
version: 1.0.0
category: testing
technologies: [cypress, javascript, typescript]
triggers:
  - cypress
  - cypress testing
  - e2e cypress
---

# Cypress E2E Testing

End-to-end testing with Cypress.

## Capabilities

- E2E test automation
- Component testing
- API testing
- Visual testing
- Network stubbing
- Custom commands
- CI/CD integration

## Project Structure

```
cypress/
├── e2e/
│   ├── auth/
│   │   ├── login.cy.ts
│   │   └── signup.cy.ts
│   └── dashboard/
│       └── dashboard.cy.ts
├── fixtures/
│   └── users.json
├── support/
│   ├── commands.ts
│   └── e2e.ts
└── cypress.config.ts
```

## Configuration

```typescript
// cypress.config.ts
import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    viewportWidth: 1280,
    viewportHeight: 720,
    video: true,
    screenshotOnRunFailure: true,
  },
  component: {
    devServer: {
      framework: "react",
      bundler: "vite",
    },
  },
});
```

## Test Example

```typescript
describe("Authentication", () => {
  beforeEach(() => {
    cy.visit("/login");
  });

  it("should login successfully", () => {
    cy.get('[data-testid="email"]').type("user@example.com");
    cy.get('[data-testid="password"]').type("password123");
    cy.get('[data-testid="submit"]').click();

    cy.url().should("include", "/dashboard");
    cy.contains("Welcome back").should("be.visible");
  });

  it("should show error for invalid credentials", () => {
    cy.get('[data-testid="email"]').type("wrong@example.com");
    cy.get('[data-testid="password"]').type("wrongpass");
    cy.get('[data-testid="submit"]').click();

    cy.contains("Invalid credentials").should("be.visible");
  });
});
```

## Custom Commands

```typescript
// support/commands.ts
Cypress.Commands.add("login", (email: string, password: string) => {
  cy.session([email, password], () => {
    cy.visit("/login");
    cy.get('[data-testid="email"]').type(email);
    cy.get('[data-testid="password"]').type(password);
    cy.get('[data-testid="submit"]').click();
    cy.url().should("include", "/dashboard");
  });
});
```

## Best Practices

1. Use data-testid attributes
2. Implement custom commands
3. Use fixtures for test data
4. Mock API calls for speed
5. Run in CI with video
6. Use cy.session for auth
7. Keep tests independent
