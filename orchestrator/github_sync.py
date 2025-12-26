# =============================================================================
# CLOPUS v3 GitHub Sync
# =============================================================================
"""
Synchronizes skills, templates, and MCPs to GitHub.
Manages the CLOPUS shared repository.
"""

import asyncio
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import json

logger = logging.getLogger("clopus.github_sync")


class GitHubSync:
    """Synchronize assets to GitHub."""

    def __init__(
        self,
        config,
        skills_path: Path,
        templates_path: Path,
        mcp_path: Path
    ):
        self.config = config
        self.skills_path = skills_path
        self.templates_path = templates_path
        self.mcp_path = mcp_path
        self.commit_prefix = config.commit_prefix

    async def sync_all(self) -> Dict[str, int]:
        """Sync all asset types to GitHub."""
        results = {
            "skills": 0,
            "templates": 0,
            "mcps": 0
        }

        if self.config.sync_skills:
            results["skills"] = await self.sync_skills()

        if self.config.sync_templates:
            results["templates"] = await self.sync_templates()

        if self.config.sync_mcps:
            results["mcps"] = await self.sync_mcps()

        return results

    async def sync_skills(self) -> int:
        """Sync generated skills to GitHub."""
        generated_dir = self.skills_path / "generated"
        if not generated_dir.exists():
            return 0

        count = 0
        for skill_dir in generated_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                if await self._sync_asset("skill", skill_dir):
                    count += 1

        return count

    async def sync_templates(self) -> int:
        """Sync extracted templates to GitHub."""
        extracted_dir = self.templates_path / "extracted"
        if not extracted_dir.exists():
            return 0

        count = 0
        for template_dir in extracted_dir.iterdir():
            if template_dir.is_dir() and (template_dir / "TEMPLATE.md").exists():
                if await self._sync_asset("template", template_dir):
                    count += 1

        return count

    async def sync_mcps(self) -> int:
        """Sync generated MCP servers to GitHub."""
        generated_dir = self.mcp_path / "generated"
        if not generated_dir.exists():
            return 0

        count = 0
        for mcp_dir in generated_dir.iterdir():
            if mcp_dir.is_dir() and (mcp_dir / "package.json").exists():
                if await self._sync_asset("mcp", mcp_dir):
                    count += 1

        return count

    async def _sync_asset(self, asset_type: str, asset_dir: Path) -> bool:
        """Sync a single asset to GitHub."""
        try:
            asset_name = asset_dir.name

            # Check if already synced (marker file)
            marker_file = asset_dir / ".github_synced"
            if marker_file.exists():
                # Check if files changed since last sync
                last_sync = datetime.fromisoformat(marker_file.read_text().strip())
                newest_file = max(
                    (f.stat().st_mtime for f in asset_dir.rglob("*") if f.is_file()),
                    default=0
                )
                if datetime.fromtimestamp(newest_file) <= last_sync:
                    return False  # No changes

            # Run git add and commit
            await self._run_git_command(
                ["git", "add", str(asset_dir)],
                cwd=asset_dir.parent.parent
            )

            commit_message = f"{self.commit_prefix} Add/update {asset_type}: {asset_name}"
            await self._run_git_command(
                ["git", "commit", "-m", commit_message],
                cwd=asset_dir.parent.parent
            )

            # Push to remote
            await self._run_git_command(
                ["git", "push"],
                cwd=asset_dir.parent.parent
            )

            # Update sync marker
            marker_file.write_text(datetime.now().isoformat())

            logger.info(f"Synced {asset_type}: {asset_name}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git error syncing {asset_type} {asset_dir.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error syncing {asset_type} {asset_dir.name}: {e}")
            return False

    async def _run_git_command(
        self,
        command: List[str],
        cwd: Optional[Path] = None
    ) -> str:
        """Run a git command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                command,
                stdout,
                stderr
            )

        return stdout.decode()

    async def create_project_repo(
        self,
        project_name: str,
        description: str,
        private: bool = False,
        local_path: Optional[Path] = None
    ) -> Optional[str]:
        """Create a new GitHub repository for a project."""
        try:
            # Create repo using gh CLI
            visibility = "--private" if private else "--public"
            result = await self._run_gh_command([
                "repo", "create", project_name,
                visibility,
                "--description", description,
                "--confirm"
            ])

            # Get repo URL
            repo_url = result.strip()

            # Initialize local repo if path provided
            if local_path and local_path.exists():
                await self._run_git_command(["git", "init"], cwd=local_path)
                await self._run_git_command(
                    ["git", "remote", "add", "origin", repo_url],
                    cwd=local_path
                )

            logger.info(f"Created repository: {repo_url}")
            return repo_url

        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            return None

    async def _run_gh_command(self, args: List[str]) -> str:
        """Run a gh CLI command."""
        command = ["gh"] + args
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                command,
                stdout,
                stderr
            )

        return stdout.decode()

    async def push_project(
        self,
        local_path: Path,
        commit_message: Optional[str] = None
    ) -> bool:
        """Push project changes to GitHub."""
        try:
            # Stage all changes
            await self._run_git_command(["git", "add", "."], cwd=local_path)

            # Check if there are changes to commit
            result = await self._run_git_command(
                ["git", "status", "--porcelain"],
                cwd=local_path
            )

            if not result.strip():
                logger.info("No changes to commit")
                return True

            # Commit
            message = commit_message or f"{self.commit_prefix} Update project"
            await self._run_git_command(
                ["git", "commit", "-m", message],
                cwd=local_path
            )

            # Push
            await self._run_git_command(["git", "push"], cwd=local_path)

            logger.info(f"Pushed project: {local_path}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error pushing project: {e}")
            return False

    async def clone_repo(
        self,
        repo_url: str,
        local_path: Path
    ) -> bool:
        """Clone a repository."""
        try:
            await self._run_git_command(
                ["git", "clone", repo_url, str(local_path)]
            )
            logger.info(f"Cloned {repo_url} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return False

    async def create_pull_request(
        self,
        local_path: Path,
        title: str,
        body: str,
        base: str = "main",
        head: Optional[str] = None
    ) -> Optional[str]:
        """Create a pull request."""
        try:
            # Get current branch if head not specified
            if head is None:
                head = await self._run_git_command(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=local_path
                )
                head = head.strip()

            # Create PR
            result = await self._run_gh_command([
                "pr", "create",
                "--title", title,
                "--body", body,
                "--base", base,
                "--head", head,
                "--repo", "."
            ])

            pr_url = result.strip()
            logger.info(f"Created PR: {pr_url}")
            return pr_url

        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return None

    async def get_repo_info(self, repo_name: str) -> Optional[Dict]:
        """Get information about a repository."""
        try:
            result = await self._run_gh_command([
                "repo", "view", repo_name, "--json",
                "name,description,url,defaultBranchRef,isPrivate"
            ])

            return json.loads(result)
        except Exception as e:
            logger.error(f"Error getting repo info: {e}")
            return None
