---
name: docker-containerization
description: Docker containerization and orchestration
version: 1.0.0
author: CLOPUS
model: claude-sonnet-4-20250514
tags:
  - devops
  - docker
  - containers
  - deployment
tools:
  - Bash
  - Read
  - Write
  - Glob
---

# Docker Containerization

Expert skill for containerizing applications with Docker.

## Capabilities

- Write optimized Dockerfiles
- Create multi-stage builds
- Set up Docker Compose for development
- Configure production deployments
- Implement health checks
- Manage volumes and networks

## Dockerfile Patterns

### Node.js Application

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Python Application

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

## Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/app
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "user"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

## Best Practices

1. Use multi-stage builds to reduce image size
2. Run as non-root user in production
3. Use .dockerignore to exclude unnecessary files
4. Pin base image versions
5. Add health checks
6. Use COPY instead of ADD
7. Order Dockerfile commands for optimal caching
8. Scan images for vulnerabilities

## Common Commands

```bash
# Build image
docker build -t myapp:latest .

# Run container
docker run -d -p 3000:3000 myapp:latest

# View logs
docker logs -f container_id

# Shell into container
docker exec -it container_id sh

# Clean up
docker system prune -a
```
