---
title: "JWT Access + Refresh Token Authentication"
type: solution
technologies: [typescript, node, jwt, express, fastapi]
confidence: 0.94
created: 2025-12-26
last_used: 2025-12-26
use_count: 0
---

# JWT Access + Refresh Token Authentication

Complete solution for secure JWT authentication with token refresh.

## Problem

- Access tokens need to be short-lived for security
- Users shouldn't have to re-login frequently
- Tokens need to be revocable for compromised accounts

## Solution

Use two tokens:
- **Access Token**: Short-lived (15 min), used for API requests
- **Refresh Token**: Long-lived (7 days), used only to get new access tokens

## Implementation (Node.js/Express)

### Token Generation

```typescript
import jwt from "jsonwebtoken";
import { v4 as uuidv4 } from "uuid";

interface TokenPayload {
  userId: string;
  email: string;
}

const ACCESS_SECRET = process.env.JWT_ACCESS_SECRET!;
const REFRESH_SECRET = process.env.JWT_REFRESH_SECRET!;

function generateTokens(payload: TokenPayload) {
  const accessToken = jwt.sign(payload, ACCESS_SECRET, {
    expiresIn: "15m",
  });

  const refreshTokenId = uuidv4();
  const refreshToken = jwt.sign(
    { ...payload, tokenId: refreshTokenId },
    REFRESH_SECRET,
    { expiresIn: "7d" }
  );

  return { accessToken, refreshToken, refreshTokenId };
}
```

### Store Refresh Tokens

```typescript
// Store refresh token ID in database for revocation
async function storeRefreshToken(
  userId: string,
  tokenId: string,
  expiresAt: Date
) {
  await db.refreshToken.create({
    data: {
      id: tokenId,
      userId,
      expiresAt,
    },
  });
}
```

### Login Endpoint

```typescript
app.post("/auth/login", async (req, res) => {
  const { email, password } = req.body;

  const user = await verifyCredentials(email, password);
  if (!user) {
    return res.status(401).json({ error: "Invalid credentials" });
  }

  const { accessToken, refreshToken, refreshTokenId } = generateTokens({
    userId: user.id,
    email: user.email,
  });

  await storeRefreshToken(
    user.id,
    refreshTokenId,
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
  );

  res.cookie("refreshToken", refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    maxAge: 7 * 24 * 60 * 60 * 1000,
  });

  res.json({ accessToken });
});
```

### Refresh Endpoint

```typescript
app.post("/auth/refresh", async (req, res) => {
  const refreshToken = req.cookies.refreshToken;

  if (!refreshToken) {
    return res.status(401).json({ error: "No refresh token" });
  }

  try {
    const payload = jwt.verify(refreshToken, REFRESH_SECRET) as any;

    // Check if token is revoked
    const storedToken = await db.refreshToken.findUnique({
      where: { id: payload.tokenId },
    });

    if (!storedToken) {
      return res.status(401).json({ error: "Token revoked" });
    }

    // Generate new tokens (rotate refresh token)
    const { accessToken, refreshToken: newRefresh, refreshTokenId } =
      generateTokens({ userId: payload.userId, email: payload.email });

    // Delete old, store new
    await db.refreshToken.delete({ where: { id: payload.tokenId } });
    await storeRefreshToken(payload.userId, refreshTokenId,
      new Date(Date.now() + 7 * 24 * 60 * 60 * 1000));

    res.cookie("refreshToken", newRefresh, {
      httpOnly: true,
      secure: true,
      sameSite: "strict",
      maxAge: 7 * 24 * 60 * 60 * 1000,
    });

    res.json({ accessToken });
  } catch (error) {
    res.status(401).json({ error: "Invalid refresh token" });
  }
});
```

### Logout (Revoke Tokens)

```typescript
app.post("/auth/logout", async (req, res) => {
  const refreshToken = req.cookies.refreshToken;

  if (refreshToken) {
    try {
      const payload = jwt.verify(refreshToken, REFRESH_SECRET) as any;
      await db.refreshToken.delete({ where: { id: payload.tokenId } });
    } catch {}
  }

  res.clearCookie("refreshToken");
  res.json({ success: true });
});
```

## Security Considerations

1. **Store refresh tokens in httpOnly cookies** - Prevents XSS attacks
2. **Rotate refresh tokens** - Each use generates a new one
3. **Short access token lifetime** - Limits damage from stolen tokens
4. **Revocation support** - Can invalidate all sessions for a user
5. **Secure flag in production** - Cookies only sent over HTTPS
