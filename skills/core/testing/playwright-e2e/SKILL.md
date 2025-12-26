---
name: playwright-e2e
description: End-to-end testing with Playwright
version: 1.0.0
author: CLOPUS
model: claude-sonnet-4-20250514
tags:
  - testing
  - e2e
  - playwright
  - automation
tools:
  - Bash
  - Read
  - Write
  - Glob
---

# Playwright E2E Testing

Expert skill for end-to-end testing with Playwright.

## Capabilities

- Write comprehensive E2E tests
- Test across Chromium, Firefox, and WebKit
- Handle authentication flows
- Test responsive designs
- Capture screenshots and videos
- Generate test reports

## Setup

```bash
# Install Playwright
npm init playwright@latest

# Install browsers
npx playwright install
```

## Test Patterns

### Basic Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('should display welcome message', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading')).toContainText('Welcome');
  });

  test('should navigate to about page', async ({ page }) => {
    await page.goto('/');

    await page.click('text=About');

    await expect(page).toHaveURL('/about');
  });
});
```

### Authentication Test

```typescript
test.describe('Authentication', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[name="email"]', 'user@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByText('Welcome back')).toBeVisible();
  });
});
```

### Form Submission

```typescript
test('should submit contact form', async ({ page }) => {
  await page.goto('/contact');

  await page.fill('#name', 'John Doe');
  await page.fill('#email', 'john@example.com');
  await page.fill('#message', 'Hello, this is a test message');

  await page.click('button[type="submit"]');

  await expect(page.getByText('Thank you')).toBeVisible();
});
```

## Configuration

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
```

## Best Practices

1. Use role-based selectors (getByRole, getByText)
2. Avoid hardcoded waits - use auto-waiting
3. Keep tests independent
4. Use fixtures for common setup
5. Generate visual regression baselines
6. Run tests in CI/CD pipeline
