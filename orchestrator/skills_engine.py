# =============================================================================
# CLOPUS v3 Skills Engine
# =============================================================================
"""
Manages skill discovery, generation, validation, and synchronization.
Skills are Claude Code capabilities that can be invoked.
"""

import asyncio
import json
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("clopus.skills_engine")


class SkillsEngine:
    """Manage CLOPUS skills."""

    def __init__(
        self,
        memory_client,
        github_sync,
        skills_path: str = "/app/skills"
    ):
        self.memory = memory_client
        self.github_sync = github_sync
        self.skills_path = Path(skills_path)
        self.core_path = self.skills_path / "core"
        self.generated_path = self.skills_path / "generated"

        # Ensure directories exist
        self.core_path.mkdir(parents=True, exist_ok=True)
        self.generated_path.mkdir(parents=True, exist_ok=True)

        # Cache of loaded skills
        self._skills_cache: Dict[str, Dict] = {}

    async def discover_skills(self) -> List[Dict]:
        """Discover all available skills."""
        skills = []

        # Scan core skills
        for category_dir in self.core_path.iterdir():
            if category_dir.is_dir():
                for skill_dir in category_dir.iterdir():
                    if skill_dir.is_dir():
                        skill = await self._load_skill(skill_dir)
                        if skill:
                            skill["source"] = "core"
                            skill["category"] = category_dir.name
                            skills.append(skill)

        # Scan generated skills
        for skill_dir in self.generated_path.iterdir():
            if skill_dir.is_dir():
                skill = await self._load_skill(skill_dir)
                if skill:
                    skill["source"] = "generated"
                    skills.append(skill)

        logger.info(f"Discovered {len(skills)} skills")
        return skills

    async def _load_skill(self, skill_dir: Path) -> Optional[Dict]:
        """Load a skill from its directory."""
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None

        try:
            content = skill_file.read_text()

            # Parse YAML frontmatter
            frontmatter = {}
            body = content

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()

            skill = {
                "name": frontmatter.get("name", skill_dir.name),
                "description": frontmatter.get("description", ""),
                "version": frontmatter.get("version", "1.0.0"),
                "author": frontmatter.get("author", "CLOPUS"),
                "tags": frontmatter.get("tags", []),
                "tools": frontmatter.get("tools", []),
                "path": str(skill_dir),
                "body": body
            }

            self._skills_cache[skill["name"]] = skill
            return skill

        except Exception as e:
            logger.error(f"Error loading skill {skill_dir}: {e}")
            return None

    async def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name."""
        if name in self._skills_cache:
            return self._skills_cache[name]

        # Search in directories
        for skill_dir in self.core_path.rglob(name):
            if skill_dir.is_dir():
                return await self._load_skill(skill_dir)

        for skill_dir in self.generated_path.iterdir():
            if skill_dir.name == name:
                return await self._load_skill(skill_dir)

        return None

    async def search_skills(self, query: str) -> List[Dict]:
        """Search skills by name, description, or tags."""
        all_skills = await self.discover_skills()
        query_lower = query.lower()

        matches = []
        for skill in all_skills:
            score = 0

            # Check name
            if query_lower in skill["name"].lower():
                score += 3

            # Check description
            if query_lower in skill.get("description", "").lower():
                score += 2

            # Check tags
            for tag in skill.get("tags", []):
                if query_lower in tag.lower():
                    score += 1

            if score > 0:
                matches.append((skill, score))

        # Sort by score
        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]

    async def generate_skill(
        self,
        name: str,
        description: str,
        based_on: Optional[str] = None,
        examples: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """Generate a new skill based on patterns or examples."""
        logger.info(f"Generating skill: {name}")

        # Create skill directory
        skill_dir = self.generated_path / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Generate skill content
        skill_content = await self._generate_skill_content(
            name=name,
            description=description,
            based_on=based_on,
            examples=examples
        )

        # Write SKILL.md
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content)

        # Validate skill
        is_valid = await self._validate_skill(skill_dir)
        if not is_valid:
            logger.warning(f"Generated skill {name} failed validation")

        # Load and cache
        skill = await self._load_skill(skill_dir)

        if skill:
            # Store in memory
            await self.memory.long_term.store(
                memory_type="skill",
                content=f"Generated skill: {name}\n{description}",
                metadata={
                    "skill_name": name,
                    "version": "1.0.0",
                    "generated": True
                }
            )

            # Sync to GitHub
            if self.github_sync:
                await self.github_sync.sync_skills()

        return skill

    async def _generate_skill_content(
        self,
        name: str,
        description: str,
        based_on: Optional[str] = None,
        examples: Optional[List[str]] = None
    ) -> str:
        """Generate SKILL.md content."""
        # Build frontmatter
        frontmatter = {
            "name": name,
            "description": description,
            "version": "1.0.0",
            "author": "CLOPUS",
            "tags": self._infer_tags(name, description),
            "model": "claude-sonnet-4-20250514",
            "tools": self._infer_tools(description)
        }

        # Build body
        body_parts = [
            f"# {name}",
            "",
            description,
            "",
            "## Instructions",
            "",
        ]

        # Add base skill content if based on another
        if based_on:
            base_skill = await self.get_skill(based_on)
            if base_skill:
                body_parts.append(f"Based on: {based_on}")
                body_parts.append("")
                body_parts.append(base_skill.get("body", "")[:500])
                body_parts.append("")

        # Add examples if provided
        if examples:
            body_parts.append("## Examples")
            body_parts.append("")
            for example in examples:
                body_parts.append(f"- {example}")
            body_parts.append("")

        # Assemble content
        yaml_front = yaml.dump(frontmatter, default_flow_style=False)
        body = "\n".join(body_parts)

        return f"---\n{yaml_front}---\n\n{body}"

    def _infer_tags(self, name: str, description: str) -> List[str]:
        """Infer tags from name and description."""
        text = f"{name} {description}".lower()
        tags = []

        tag_patterns = {
            "development": ["code", "develop", "build", "implement"],
            "testing": ["test", "spec", "validation"],
            "data": ["data", "database", "sql", "csv"],
            "web": ["web", "http", "api", "rest"],
            "automation": ["automat", "script", "batch"],
            "devops": ["deploy", "docker", "kubernetes", "ci/cd"],
        }

        for tag, patterns in tag_patterns.items():
            if any(p in text for p in patterns):
                tags.append(tag)

        return tags[:5]

    def _infer_tools(self, description: str) -> List[str]:
        """Infer required tools from description."""
        tools = []
        text = description.lower()

        tool_patterns = {
            "Bash": ["run", "execute", "script", "command"],
            "Read": ["read", "file", "content"],
            "Write": ["write", "create", "save"],
            "Glob": ["find", "search", "pattern"],
            "Grep": ["grep", "search", "match"],
        }

        for tool, patterns in tool_patterns.items():
            if any(p in text for p in patterns):
                tools.append(tool)

        return tools or ["Bash", "Read", "Write"]

    async def _validate_skill(self, skill_dir: Path) -> bool:
        """Validate a skill structure."""
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return False

        try:
            content = skill_file.read_text()

            # Check for frontmatter
            if not content.startswith("---"):
                return False

            # Parse frontmatter
            parts = content.split("---", 2)
            if len(parts) < 3:
                return False

            frontmatter = yaml.safe_load(parts[1])

            # Required fields
            required = ["name", "description"]
            for field in required:
                if field not in frontmatter:
                    return False

            return True

        except Exception:
            return False

    async def extract_skill_from_task(
        self,
        task_description: str,
        task_result: Dict,
        success: bool
    ) -> Optional[Dict]:
        """Extract a reusable skill from a completed task."""
        if not success:
            return None

        # Check if this pattern is worth extracting
        similar = await self.memory.search_memories(
            task_description,
            n_results=3
        )

        if len(similar) < 2:
            # Not enough similar tasks to warrant a skill
            return None

        # Generate skill name from task
        name = self._generate_skill_name(task_description)

        # Check if skill already exists
        existing = await self.get_skill(name)
        if existing:
            return existing

        # Generate the skill
        return await self.generate_skill(
            name=name,
            description=f"Extracted from task: {task_description[:200]}",
            examples=[task_description]
        )

    def _generate_skill_name(self, description: str) -> str:
        """Generate a skill name from description."""
        # Extract key words
        words = re.findall(r'\b[a-zA-Z]+\b', description.lower())

        # Filter common words
        stopwords = {"a", "an", "the", "to", "for", "with", "and", "or", "in", "on", "at"}
        words = [w for w in words if w not in stopwords][:3]

        return "-".join(words) or "extracted-skill"

    async def list_by_category(self) -> Dict[str, List[Dict]]:
        """List skills grouped by category."""
        all_skills = await self.discover_skills()
        categorized = {}

        for skill in all_skills:
            category = skill.get("category", "uncategorized")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(skill)

        return categorized
