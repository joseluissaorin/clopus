# CLOPUS Core Tools

Utility scripts and tools used by CLOPUS for various automation tasks.

## Available Tools

| Tool | Description |
|------|-------------|
| `project-init.sh` | Initialize a new project with CLOPUS conventions |
| `validate.sh` | Run the full validation pipeline |
| `sync-github.sh` | Sync skills, templates, and MCPs to GitHub |
| `backup.sh` | Backup CLOPUS data and configurations |
| `clean-workspace.sh` | Clean temporary files and build artifacts |

## Usage

All tools are executable and can be run from the CLOPUS root directory:

```bash
./tools/core/project-init.sh my-project react-typescript
./tools/core/validate.sh /workspace/my-project
```

## Generated Tools

Tools created by CLOPUS during operation are stored in `tools/generated/`.
