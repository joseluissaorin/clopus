---
name: ci-cd-github-actions
description: CI/CD pipelines with GitHub Actions
version: 1.0.0
category: devops
technologies: [github-actions, ci-cd, automation]
triggers:
  - github actions
  - ci/cd
  - continuous integration
  - continuous deployment
  - pipeline
---

# CI/CD with GitHub Actions

Automated testing, building, and deployment pipelines.

## Basic CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Lint
      run: npm run lint

    - name: Type check
      run: npm run type-check

    - name: Test
      run: npm test -- --coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        token: ${{ secrets.CODECOV_TOKEN }}
```

## Build and Deploy

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
    - uses: actions/checkout@v4

    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=sha,prefix=
          type=ref,event=branch

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production

    steps:
    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v4
      with:
        manifests: k8s/
        images: ${{ needs.build.outputs.image-tag }}
```

## Matrix Testing

```yaml
name: Test Matrix

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [18, 20, 22]
        exclude:
          - os: windows-latest
            node: 18

    steps:
    - uses: actions/checkout@v4

    - name: Setup Node.js ${{ matrix.node }}
      uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node }}

    - run: npm ci
    - run: npm test
```

## Release Workflow

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        registry-url: 'https://registry.npmjs.org'

    - run: npm ci
    - run: npm run build

    - name: Publish to npm
      run: npm publish
      env:
        NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

    - name: Create GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        generate_release_notes: true
        files: |
          dist/*.js
          dist/*.d.ts
```

## Reusable Workflow

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      deploy-key:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}

    steps:
    - uses: actions/checkout@v4

    - name: Deploy
      run: ./deploy.sh ${{ inputs.environment }}
      env:
        DEPLOY_KEY: ${{ secrets.deploy-key }}

# Usage in another workflow:
# jobs:
#   deploy:
#     uses: ./.github/workflows/reusable-deploy.yml
#     with:
#       environment: production
#     secrets:
#       deploy-key: ${{ secrets.DEPLOY_KEY }}
```

## Scheduled Jobs

```yaml
name: Scheduled Tasks

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  workflow_dispatch:  # Manual trigger

jobs:
  cleanup:
    runs-on: ubuntu-latest

    steps:
    - name: Cleanup old artifacts
      uses: actions/github-script@v7
      with:
        script: |
          const days = 30;
          const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

          const artifacts = await github.rest.actions.listArtifactsForRepo({
            owner: context.repo.owner,
            repo: context.repo.repo,
          });

          for (const artifact of artifacts.data.artifacts) {
            if (new Date(artifact.created_at) < cutoff) {
              await github.rest.actions.deleteArtifact({
                owner: context.repo.owner,
                repo: context.repo.repo,
                artifact_id: artifact.id,
              });
            }
          }
```

## Best Practices

1. Use caching for dependencies
2. Run jobs in parallel when possible
3. Use environment protection rules
4. Store secrets securely
5. Use reusable workflows
6. Implement branch protection
7. Add status checks
8. Use concurrency controls
