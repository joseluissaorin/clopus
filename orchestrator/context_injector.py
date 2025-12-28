# =============================================================================
# CLOPUS v3 Context Injector
# =============================================================================
"""
Injects relevant context from memory into tasks before dispatch.
Also extracts learnings from completed tasks and stores them.

NEW IN v3.2: AI-First Context and Learning
- Uses Claude intelligence for semantic context relevance
- Uses AI for intelligent learning extraction
- Falls back to keyword/regex matching when AI unavailable
"""

import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .ai_first import AIFirstEngine

logger = logging.getLogger("clopus.context_injector")


class ContextInjector:
    """
    Injects context into tasks and extracts learnings from results.

    Pre-Task Injection:
    - Search long-term memory for relevant patterns
    - Load design system if applicable
    - Get shared context from other workers

    Post-Task Extraction:
    - Extract patterns, solutions, and warnings from results
    - Store in long-term memory with role tags
    - Update shared memory cache

    NEW IN v3.2: AI-First Context and Learning
    - Uses AI intelligence for semantic context relevance
    - Uses AI for intelligent learning extraction
    - Falls back to keyword/regex matching when AI unavailable
    """

    def __init__(
        self,
        memory_client,
        ipc_path: str = "/app/ipc"
    ):
        self.memory = memory_client
        self.ipc_path = Path(ipc_path)
        self.shared_path = self.ipc_path / "memory" / "shared"

        # AI-First Engine (set by orchestrator, NEW in v3.2)
        self.ai_engine: Optional["AIFirstEngine"] = None

        # Keywords that trigger context searches (deprecated, used as fallback)
        self.context_triggers = {
            "design": ["color", "style", "ui", "ux", "design", "theme", "visual"],
            "api": ["api", "endpoint", "fetch", "request", "http"],
            "pattern": ["pattern", "approach", "best practice", "example"],
            "error": ["error", "bug", "fix", "issue", "problem"],
        }

        # Keywords for learning extraction (deprecated, used as fallback)
        self.learning_patterns = {
            "solution": [
                r"solved by",
                r"fixed by",
                r"the solution is",
                r"this works because",
                r"resolved by",
            ],
            "pattern": [
                r"best practice",
                r"always use",
                r"never use",
                r"pattern for",
                r"approach for",
            ],
            "warning": [
                r"be careful",
                r"watch out",
                r"warning",
                r"gotcha",
                r"avoid",
                r"don't forget",
            ],
        }

    def set_ai_engine(self, ai_engine: "AIFirstEngine") -> None:
        """Set the AI-first engine for intelligent context and learning."""
        self.ai_engine = ai_engine
        logger.info("AI-First Engine connected to context injector")

    async def inject_context(
        self,
        task: Dict[str, Any],
        worker_role: str,
        project_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inject relevant context into a task before dispatch.

        NEW IN v3.2: AI-First approach
        Priority:
        1. AI-First Engine (semantic relevance)
        2. Keyword-based selection (deprecated fallback)

        Args:
            task: Task dictionary with at least 'prompt' or 'description'
            worker_role: Role of the worker that will receive this task
            project_path: Path to the project (for design system lookup)

        Returns:
            Modified task with context injected into prompt/description
        """
        task_text = task.get("prompt", task.get("description", ""))

        if not task_text:
            return task

        # Try AI-First Engine for intelligent context selection
        if self.ai_engine:
            try:
                # Gather available context
                available_context = await self._gather_available_context(project_path)

                result = await self.ai_engine.determine_relevant_context(
                    task_description=task_text,
                    worker_role=worker_role,
                    available_context=available_context
                )

                if result.success and result.result:
                    relevant_sections = result.result.get("relevant_context", [])
                    if relevant_sections:
                        context_block = "\n\n---\n## Relevant Context (AI-Selected)\n\n" + "\n\n".join(relevant_sections)

                        if "prompt" in task:
                            task["prompt"] = task["prompt"] + context_block
                        elif "description" in task:
                            task["description"] = task["description"] + context_block

                        logger.info(f"AI-first injected {len(relevant_sections)} context sections")
                        return task

            except Exception as e:
                logger.debug(f"AI-first context injection failed: {e}")

        # Fallback to keyword-based context selection (deprecated)
        return await self._keyword_inject_context(task, task_text, worker_role, project_path)

    async def _gather_available_context(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Gather all available context for AI to select from."""
        context = {}

        # Get design system
        if project_path:
            design_context = await self._get_design_context(project_path)
            if design_context:
                context["design_system"] = design_context

        # Get shared learnings
        shared_context = await self._get_shared_context("")
        if shared_context:
            context["shared_learnings"] = shared_context

        # Get API endpoints
        api_context = await self._get_api_context()
        if api_context:
            context["api_endpoints"] = api_context

        return context

    async def _keyword_inject_context(
        self,
        task: Dict[str, Any],
        task_text: str,
        worker_role: str,
        project_path: Optional[str]
    ) -> Dict[str, Any]:
        """DEPRECATED: Keyword-based context injection. Use AI-first instead."""
        # Collect context to inject
        context_sections = []

        # 1. Search long-term memory for relevant patterns
        memory_context = await self._get_memory_context(task_text, worker_role)
        if memory_context:
            context_sections.append(memory_context)

        # 2. Get design system if this is a UI-related task
        if self._is_design_related(task_text):
            design_context = await self._get_design_context(project_path)
            if design_context:
                context_sections.append(design_context)

        # 3. Get recent learnings from shared cache
        shared_context = await self._get_shared_context(task_text)
        if shared_context:
            context_sections.append(shared_context)

        # 4. Get API endpoints if this is an API-related task
        if self._is_api_related(task_text):
            api_context = await self._get_api_context()
            if api_context:
                context_sections.append(api_context)

        # Inject context into task
        if context_sections:
            context_block = "\n\n---\n## Relevant Context\n\n" + "\n\n".join(context_sections)

            if "prompt" in task:
                task["prompt"] = task["prompt"] + context_block
            elif "description" in task:
                task["description"] = task["description"] + context_block

            logger.info(f"Injected {len(context_sections)} context sections into task")

        return task

    async def _get_memory_context(
        self,
        task_text: str,
        worker_role: str
    ) -> Optional[str]:
        """Search long-term memory for relevant context."""
        try:
            # Search for patterns related to the task
            results = await self.memory.long_term.search(
                query=task_text[:500],  # Limit query length
                limit=3,
                filters={"role": worker_role} if worker_role else None
            )

            if not results:
                return None

            context_items = []
            for result in results:
                if isinstance(result, dict):
                    content = result.get("content", "")
                    memory_type = result.get("type", "pattern")
                    context_items.append(f"**{memory_type.upper()}**: {content[:300]}")

            if context_items:
                return "### From Past Experience\n" + "\n\n".join(context_items)

        except Exception as e:
            logger.debug(f"Could not get memory context: {e}")

        return None

    async def _get_design_context(
        self,
        project_path: Optional[str] = None
    ) -> Optional[str]:
        """Get design system context."""
        # Try project-specific design system first
        if project_path:
            design_file = Path(project_path) / ".clopus" / "design" / "DESIGN_SYSTEM.md"
            if design_file.exists():
                try:
                    content = design_file.read_text()
                    # Extract key sections (colors, typography)
                    return self._extract_design_essentials(content)
                except Exception:
                    pass

        # Fall back to shared cache
        cached_design = self.shared_path / "design_system.json"
        if cached_design.exists():
            try:
                data = json.loads(cached_design.read_text())
                return "### Design System\n```json\n" + json.dumps(data, indent=2)[:500] + "\n```"
            except Exception:
                pass

        return None

    def _extract_design_essentials(self, content: str) -> str:
        """Extract essential design info (colors, typography) from full design system."""
        lines = content.split("\n")
        essential_lines = []
        in_essential_section = False
        essential_keywords = ["color", "typography", "spacing", "primary", "secondary"]

        for line in lines:
            lower = line.lower()

            # Check if entering an essential section
            if any(kw in lower for kw in essential_keywords):
                in_essential_section = True

            # Check if leaving section (new ## heading)
            if line.startswith("## ") and not any(kw in lower for kw in essential_keywords):
                in_essential_section = False

            if in_essential_section:
                essential_lines.append(line)

            # Limit size
            if len("\n".join(essential_lines)) > 500:
                break

        if essential_lines:
            return "### Design System (Key Elements)\n" + "\n".join(essential_lines[:30])
        return None

    async def _get_shared_context(self, task_text: str) -> Optional[str]:
        """Get recent learnings from shared cache."""
        recent_file = self.shared_path / "recent_learnings.json"

        if not recent_file.exists():
            return None

        try:
            learnings = json.loads(recent_file.read_text())

            # Simple keyword matching for relevance
            task_words = set(task_text.lower().split())
            relevant = []

            for learning in learnings[:10]:  # Check last 10
                content = learning.get("content", "").lower()
                overlap = len(task_words & set(content.split()))
                if overlap >= 2:  # At least 2 words in common
                    relevant.append(learning)

            if relevant:
                items = [f"- **{l.get('type', 'tip')}** ({l.get('from_role', 'unknown')}): {l.get('content', '')[:200]}" for l in relevant[:3]]
                return "### Recent Team Learnings\n" + "\n".join(items)

        except Exception as e:
            logger.debug(f"Could not get shared context: {e}")

        return None

    async def _get_api_context(self) -> Optional[str]:
        """Get discovered API endpoints from cache."""
        api_file = self.shared_path / "api_endpoints.json"

        if not api_file.exists():
            return None

        try:
            data = json.loads(api_file.read_text())
            endpoints = data.get("endpoints", [])

            if endpoints:
                items = [f"- `{e.get('method', 'GET')} {e.get('path', '')}` - {e.get('description', '')}" for e in endpoints[:5]]
                return "### Available API Endpoints\n" + "\n".join(items)

        except Exception:
            pass

        return None

    def _is_design_related(self, text: str) -> bool:
        """Check if task is design-related."""
        lower = text.lower()
        return any(kw in lower for kw in self.context_triggers["design"])

    def _is_api_related(self, text: str) -> bool:
        """Check if task is API-related."""
        lower = text.lower()
        return any(kw in lower for kw in self.context_triggers["api"])

    async def extract_learnings(
        self,
        task_result: Dict[str, Any],
        task: Dict[str, Any],
        worker_role: str
    ) -> List[Dict[str, Any]]:
        """
        Extract learnings from a completed task result.

        NEW IN v3.2: AI-First approach
        Priority:
        1. AI-First Engine (semantic extraction)
        2. Regex pattern matching (deprecated fallback)

        Args:
            task_result: Result from the worker
            task: Original task
            worker_role: Role of the worker that completed the task

        Returns:
            List of extracted learnings
        """
        result_text = task_result.get("result", task_result.get("output", ""))

        if not result_text or len(result_text) < 50:
            return []

        # Try AI-First Engine for intelligent learning extraction
        if self.ai_engine:
            try:
                result = await self.ai_engine.extract_learnings(
                    task_result=result_text,
                    task_description=task.get("prompt", task.get("description", "")),
                    worker_role=worker_role
                )

                if result.success and result.result:
                    ai_learnings = result.result.get("learnings", [])
                    if ai_learnings:
                        # Format AI learnings
                        formatted_learnings = []
                        for learning in ai_learnings[:5]:
                            formatted = {
                                "type": learning.get("type", "pattern"),
                                "content": learning.get("content", ""),
                                "from_role": worker_role,
                                "task_id": task.get("id", "unknown"),
                                "extracted_at": datetime.now().isoformat(),
                                "confidence": learning.get("confidence", 0.8),
                            }
                            formatted_learnings.append(formatted)

                        # Store in memory
                        for learning in formatted_learnings:
                            try:
                                await self.memory.long_term.store(
                                    content=learning["content"],
                                    memory_type=learning["type"],
                                    metadata={
                                        "from_role": worker_role,
                                        "task_id": task.get("id"),
                                        "extracted_at": learning["extracted_at"],
                                        "ai_extracted": True,
                                    }
                                )
                            except Exception as e:
                                logger.debug(f"Could not store learning: {e}")

                        logger.info(f"AI-first extracted {len(formatted_learnings)} learnings")
                        return formatted_learnings

            except Exception as e:
                logger.debug(f"AI-first learning extraction failed: {e}")

        # Fallback to regex pattern matching (deprecated)
        return await self._regex_extract_learnings(result_text, task, worker_role)

    async def _regex_extract_learnings(
        self,
        result_text: str,
        task: Dict[str, Any],
        worker_role: str
    ) -> List[Dict[str, Any]]:
        """DEPRECATED: Regex-based learning extraction. Use AI-first instead."""
        learnings = []

        # Extract based on patterns
        for learning_type, patterns in self.learning_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, result_text, re.IGNORECASE)
                for match in matches:
                    # Extract surrounding context (100 chars before and after)
                    start = max(0, match.start() - 100)
                    end = min(len(result_text), match.end() + 100)
                    context = result_text[start:end].strip()

                    if len(context) > 30:  # Meaningful content
                        learnings.append({
                            "type": learning_type,
                            "content": context,
                            "from_role": worker_role,
                            "task_id": task.get("id", "unknown"),
                            "extracted_at": datetime.now().isoformat(),
                        })

        # Deduplicate similar learnings
        unique_learnings = []
        seen_content = set()

        for learning in learnings:
            content_key = learning["content"][:50].lower()
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_learnings.append(learning)

        # Store in memory
        for learning in unique_learnings[:5]:  # Max 5 per task
            try:
                await self.memory.long_term.store(
                    content=learning["content"],
                    memory_type=learning["type"],
                    metadata={
                        "from_role": worker_role,
                        "task_id": task.get("id"),
                        "extracted_at": learning["extracted_at"],
                    }
                )
            except Exception as e:
                logger.debug(f"Could not store learning: {e}")

        if unique_learnings:
            logger.info(f"Extracted {len(unique_learnings)} learnings from task result")

        return unique_learnings

    async def update_shared_cache(
        self,
        cache_type: str,
        data: Any
    ) -> None:
        """
        Update the shared memory cache.

        Args:
            cache_type: Type of cache ('design_system', 'api_endpoints', etc.)
            data: Data to cache
        """
        self.shared_path.mkdir(parents=True, exist_ok=True)
        cache_file = self.shared_path / f"{cache_type}.json"

        try:
            cache_file.write_text(json.dumps(data, indent=2))
            logger.info(f"Updated shared cache: {cache_type}")
        except Exception as e:
            logger.error(f"Failed to update cache {cache_type}: {e}")

    async def add_api_endpoint(
        self,
        method: str,
        path: str,
        description: str = ""
    ) -> None:
        """
        Add a discovered API endpoint to the cache.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            description: Optional description
        """
        api_file = self.shared_path / "api_endpoints.json"

        try:
            if api_file.exists():
                data = json.loads(api_file.read_text())
            else:
                data = {"endpoints": [], "updated_at": ""}

            # Check for duplicate
            for ep in data["endpoints"]:
                if ep["method"] == method and ep["path"] == path:
                    return  # Already exists

            data["endpoints"].append({
                "method": method,
                "path": path,
                "description": description,
                "discovered_at": datetime.now().isoformat(),
            })

            data["updated_at"] = datetime.now().isoformat()
            api_file.write_text(json.dumps(data, indent=2))

        except Exception as e:
            logger.debug(f"Could not add API endpoint: {e}")
