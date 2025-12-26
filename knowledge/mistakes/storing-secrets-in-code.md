---
title: "Storing Secrets in Code"
type: mistake
technologies: [all]
confidence: 1.0
created: 2025-12-26
last_used: 2025-12-26
use_count: 0
---

# Storing Secrets in Code

Never hardcode sensitive credentials in source code.

## The Mistake

```python
# BAD: Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://admin:password123@prod-db.example.com/myapp"

stripe = Stripe(api_key="sk_live_xxxxx")
```

## Why It's Dangerous

1. **Git history is permanent** - Even if deleted, secrets remain in history
2. **Accidental exposure** - Public repos, backups, logs
3. **Shared access** - Everyone with code access has credentials
4. **No rotation** - Changing secrets requires code changes

## Correct Approaches

### Environment Variables

```python
import os

API_KEY = os.environ["API_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]

# With default for development
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
```

### .env Files (Development Only)

```bash
# .env (NEVER commit this file)
API_KEY=sk-1234567890abcdef
DATABASE_URL=postgresql://user:pass@localhost/dev
```

```python
from dotenv import load_dotenv
load_dotenv()
```

### Secret Managers (Production)

```python
# AWS Secrets Manager
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# HashiCorp Vault
import hvac

client = hvac.Client(url='https://vault.example.com')
secret = client.secrets.kv.v2.read_secret_version(path='myapp/prod')
```

## Prevention

### .gitignore

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Credentials
*.pem
*.key
credentials.json
service-account.json
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
```

### Git-secrets

```bash
# Install git-secrets
git secrets --install
git secrets --register-aws

# Scan for secrets
git secrets --scan
```

## If You Accidentally Commit Secrets

1. **Rotate immediately** - Generate new credentials
2. **Remove from history** - Use git-filter-repo or BFG
3. **Check for exposure** - GitHub secret scanning alerts
4. **Audit access** - Review who might have seen them

```bash
# Remove sensitive file from all history
git filter-repo --path secrets.json --invert-paths
```

## Checklist

- [ ] No hardcoded credentials in any file
- [ ] .env in .gitignore
- [ ] Pre-commit hooks for secret detection
- [ ] Environment variables in CI/CD
- [ ] Secret manager for production
