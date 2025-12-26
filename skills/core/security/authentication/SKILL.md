---
name: authentication
description: Authentication and authorization implementation
version: 1.0.0
category: security
technologies: [jwt, oauth, session, passkeys, mfa]
triggers:
  - authentication
  - login
  - authorization
  - jwt
  - oauth
  - session management
---

# Authentication & Authorization

Implementing secure authentication and authorization.

## JWT Authentication

```python
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## FastAPI Authentication

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user

async def require_role(required_roles: list):
    async def role_checker(user = Depends(get_current_user)):
        if user.role not in required_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@app.get("/admin")
async def admin_only(user = Depends(require_role(["admin"]))):
    return {"message": "Welcome, admin"}
```

## OAuth 2.0 Integration

```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.environ['GOOGLE_CLIENT_ID'],
    client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')

    # Find or create user
    user = await get_or_create_user(
        email=user_info['email'],
        name=user_info.get('name'),
        provider='google',
        provider_id=user_info['sub']
    )

    access_token = create_access_token(data={"sub": str(user.id)})

    return RedirectResponse(
        url=f"/auth/success?token={access_token}",
        status_code=302
    )
```

## Session-Based Authentication

```python
from starlette.middleware.sessions import SessionMiddleware
from itsdangerous import URLSafeTimedSerializer

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_session_token(user_id: str) -> str:
    return serializer.dumps(user_id, salt='session')

def verify_session_token(token: str, max_age: int = 86400) -> str:
    try:
        return serializer.loads(token, salt='session', max_age=max_age)
    except:
        return None

@app.post("/login")
async def login(request: Request, form_data: LoginForm):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session['user_id'] = str(user.id)
    request.session['authenticated'] = True

    return {"message": "Logged in"}

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}
```

## Multi-Factor Authentication

```python
import pyotp
import qrcode
from io import BytesIO

class MFAManager:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, email: str, issuer: str = "MyApp") -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def generate_qr_code(uri: str) -> bytes:
        qr = qrcode.make(uri)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        return buffer.getvalue()

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

@app.post("/mfa/setup")
async def setup_mfa(user = Depends(get_current_user)):
    secret = MFAManager.generate_secret()
    uri = MFAManager.get_totp_uri(secret, user.email)
    qr_code = MFAManager.generate_qr_code(uri)

    # Store secret temporarily until verified
    await store_pending_mfa_secret(user.id, secret)

    return Response(content=qr_code, media_type="image/png")

@app.post("/mfa/verify")
async def verify_mfa(code: str, user = Depends(get_current_user)):
    secret = await get_pending_mfa_secret(user.id)

    if MFAManager.verify_totp(secret, code):
        await enable_mfa(user.id, secret)
        return {"message": "MFA enabled"}

    raise HTTPException(status_code=400, detail="Invalid code")
```

## Password Reset

```python
from datetime import datetime, timedelta
import secrets

async def initiate_password_reset(email: str):
    user = await get_user_by_email(email)
    if not user:
        # Don't reveal if email exists
        return {"message": "If email exists, reset link sent"}

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)

    await store_reset_token(user.id, token, expires)
    await send_reset_email(email, token)

    return {"message": "If email exists, reset link sent"}

async def reset_password(token: str, new_password: str):
    reset_request = await get_reset_token(token)

    if not reset_request or reset_request.expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    hashed = hash_password(new_password)
    await update_user_password(reset_request.user_id, hashed)
    await invalidate_reset_token(token)

    return {"message": "Password updated"}
```

## Best Practices

1. Use bcrypt or Argon2 for passwords
2. Implement rate limiting on auth endpoints
3. Use short-lived access tokens
4. Store refresh tokens securely
5. Implement MFA for sensitive operations
6. Log authentication events
7. Use HTTPS everywhere
8. Implement account lockout
