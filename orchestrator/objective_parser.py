# =============================================================================
# CLOPUS v3 Objective Parser
# =============================================================================
"""
Parses user objectives into structured, actionable components.

NEW IN v3.1: AI-First Parsing
- Uses Claude Code intelligence to analyze ANY objective
- NO pattern matching as the primary approach
- Pattern matching is DEPRECATED and only used as fallback

The goal is to be a UNIVERSAL agent, not limited to predefined patterns.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("clopus.objective_parser")


@dataclass
class ParsedObjective:
    """Structured representation of a parsed objective."""
    original: str
    summary: str
    project_type: str
    technologies: List[str]
    features: List[Dict[str, Any]]
    constraints: List[str]
    success_criteria: List[str]
    unclear_points: List[str]
    estimated_complexity: str  # low, medium, high, very_high
    suggested_approach: str
    requires_clarification: bool
    # NEW: Multi-project support
    projects: List[Dict[str, Any]] = None  # AI-generated project definitions
    ai_analysis: Dict[str, Any] = None  # Full AI analysis result


class ObjectiveParser:
    """
    Parse and analyze user objectives.

    AI-FIRST APPROACH:
    This parser now primarily uses Claude Code intelligence to:
    1. Understand ANY type of objective
    2. Determine appropriate project structure
    3. Identify technologies and features
    4. Support multi-project objectives

    Pattern matching is DEPRECATED and only used as fallback.
    """

    def __init__(self, memory_client, confidence_engine):
        self.memory = memory_client
        self.confidence = confidence_engine

        # AI Planner for intelligent analysis (set by orchestrator)
        self.ai_planner = None
        self.worker_pool = None

        # AI-First Engine for intelligent parsing (set by orchestrator, NEW in v3.2)
        self.ai_engine = None

        # DEPRECATED: Pattern-based parsing (kept for fallback only)
        self.project_patterns = {
            r"todo\s*app": {"type": "todo_app", "tech": ["react", "typescript"]},
            r"api|backend|server": {"type": "api", "tech": ["python", "fastapi"]},
            r"dashboard": {"type": "dashboard", "tech": ["react", "typescript", "charts"]},
            r"mobile\s*app": {"type": "mobile", "tech": ["expo", "react-native"]},
            r"cli|command.line": {"type": "cli", "tech": ["python", "click"]},
            r"website|landing": {"type": "website", "tech": ["nextjs", "tailwind"]},
            r"e-?commerce|shop|store": {"type": "ecommerce", "tech": ["nextjs", "stripe"]},
            r"blog": {"type": "blog", "tech": ["nextjs", "mdx"]},
            r"wordpress": {"type": "wordpress", "tech": ["php", "wordpress"]},
            r"scrape|scraping|crawler": {"type": "scraper", "tech": ["python", "playwright"]},
        }

        # DEPRECATED: Technology detection patterns
        self.tech_patterns = {
            r"\breact\b": "react",
            r"\bvue\b": "vue",
            r"\bangular\b": "angular",
            r"\bnext\.?js\b": "nextjs",
            r"\bpython\b": "python",
            r"\bfastapi\b": "fastapi",
            r"\bdjango\b": "django",
            r"\bflask\b": "flask",
            r"\bnode\.?js\b": "nodejs",
            r"\bexpress\b": "express",
            r"\btypescript\b": "typescript",
            r"\brust\b": "rust",
            r"\bgo\b": "go",
            r"\bpostgres": "postgresql",
            r"\bmongodb\b": "mongodb",
            r"\bredis\b": "redis",
            r"\bdocker\b": "docker",
            r"\bkubernetes\b|k8s": "kubernetes",
            r"\btailwind\b": "tailwind",
            r"\bexpo\b": "expo",
            r"\breact.native\b": "react-native",
        }

    def set_worker_pool(self, worker_pool) -> None:
        """Set worker pool for AI analysis."""
        self.worker_pool = worker_pool
        logger.info("Worker pool connected to objective parser")

    def set_ai_planner(self, ai_planner) -> None:
        """Set the AI planner for intelligent parsing."""
        self.ai_planner = ai_planner
        logger.info("AI Planner connected to objective parser - using AI-first parsing")

    def set_ai_engine(self, ai_engine) -> None:
        """Set the AI-first engine for intelligent analysis."""
        self.ai_engine = ai_engine
        logger.info("AI-First Engine connected to objective parser")

    async def parse(self, objective_text: str) -> Dict[str, Any]:
        """
        Parse an objective into structured components.

        PRIMARY: Uses AI Planner for intelligent analysis
        FALLBACK: Uses pattern matching only when AI is unavailable
        """
        logger.info(f"Parsing objective: {objective_text[:100]}...")

        # =====================================================================
        # AI-FIRST PARSING (PRIMARY APPROACH)
        # =====================================================================
        if self.ai_planner or self.worker_pool:
            try:
                logger.info("Using AI-first objective parsing")
                result = await self._parse_with_ai(objective_text)
                if result:
                    logger.info("AI parsing completed successfully")
                    return result
                logger.warning("AI parsing returned no result, falling back to patterns")
            except Exception as e:
                logger.error(f"AI parsing failed: {e}, falling back to patterns")

        # =====================================================================
        # FALLBACK: Pattern-based parsing (DEPRECATED)
        # =====================================================================
        logger.warning("Using DEPRECATED pattern-based parsing - AI unavailable")
        return await self._parse_with_patterns(objective_text)

    async def _parse_with_ai(self, objective_text: str) -> Optional[Dict[str, Any]]:
        """
        Use AI Planner for intelligent objective analysis.

        This is the PRIMARY approach that uses Claude Code intelligence.
        """
        # Initialize AI planner if needed
        if not self.ai_planner and self.worker_pool:
            from .ai_planner import AIPlanner
            self.ai_planner = AIPlanner(self.worker_pool, self.memory)
            logger.info("Initialized AI Planner on-demand for parsing")

        if not self.ai_planner:
            return None

        # Get AI analysis
        analysis = await self.ai_planner.analyze_objective(objective_text)

        if not analysis:
            return None

        # Extract primary project (for backward compatibility)
        projects = analysis.get("projects", [])
        primary_project = projects[0] if projects else {}

        # Build parsed result from AI analysis
        parsed = ParsedObjective(
            original=objective_text,
            summary=analysis.get("analysis", {}).get("summary", objective_text[:200]),
            project_type=primary_project.get("type", "custom"),
            technologies=primary_project.get("technologies", []),
            features=self._extract_features_from_ai(analysis),
            constraints=[],
            success_criteria=self._generate_success_criteria_from_ai(analysis),
            unclear_points=analysis.get("clarifications_needed", []),
            estimated_complexity=analysis.get("analysis", {}).get("complexity", "medium"),
            suggested_approach=analysis.get("analysis", {}).get("estimated_scope", ""),
            requires_clarification=len(analysis.get("clarifications_needed", [])) > 0,
            projects=projects,
            ai_analysis=analysis
        )

        # Store in memory for learning
        await self.memory.store_learning(
            f"AI-Parsed objective: {parsed.summary}\n"
            f"Projects: {len(projects)}\n"
            f"Tech: {', '.join(parsed.technologies)}",
            tags=["objective_parsing", "ai_parsed", parsed.project_type]
        )

        return self._to_dict(parsed)

    def _extract_features_from_ai(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Extract features from AI analysis."""
        features = []
        for project in analysis.get("projects", []):
            arch = project.get("architecture", {})
            for component in arch.get("key_components", []):
                features.append({
                    "description": component,
                    "priority": "medium"
                })
        return features

    def _generate_success_criteria_from_ai(self, analysis: Dict) -> List[str]:
        """Generate success criteria from AI analysis."""
        criteria = [
            "All code passes linting",
            "All tests pass",
            "Build completes successfully"
        ]

        for project in analysis.get("projects", []):
            criteria.append(f"{project.get('name', 'Project')} works as described")

        return criteria

    async def _parse_with_patterns(self, objective_text: str) -> Dict[str, Any]:
        """
        DEPRECATED: Pattern-based parsing.

        Only used as fallback when AI is unavailable.
        NOTE: Still uses AI-First Engine for tech/feature detection when available.
        """
        # Quick pattern matching for common cases
        quick_result = self._quick_parse(objective_text)

        # Get relevant context from memory
        context = await self.memory.get_relevant_context(objective_text)

        # Use async versions to leverage AI-First Engine when available
        technologies = await self._detect_technologies_async(objective_text, quick_result)
        features = await self._extract_features_async(objective_text)

        # Build parsed result
        parsed = ParsedObjective(
            original=objective_text,
            summary=self._extract_summary(objective_text),
            project_type=quick_result.get("type", "custom"),
            technologies=technologies,
            features=features,
            constraints=self._extract_constraints(objective_text),
            success_criteria=self._extract_success_criteria(objective_text),
            unclear_points=self._find_unclear_points(objective_text),
            estimated_complexity=self._estimate_complexity(objective_text),
            suggested_approach=self._suggest_approach(objective_text, quick_result),
            requires_clarification=False,
            projects=None,
            ai_analysis=None
        )

        # Check if clarification needed
        parsed.requires_clarification = len(parsed.unclear_points) > 0

        # Store parsed objective in memory for learning
        await self.memory.store_learning(
            f"Pattern-Parsed objective: {parsed.summary}\nType: {parsed.project_type}\nTech: {', '.join(parsed.technologies)}",
            tags=["objective_parsing", "pattern_parsed", parsed.project_type]
        )

        return self._to_dict(parsed)

    def _quick_parse(self, text: str) -> Dict[str, Any]:
        """Quick pattern-based parsing."""
        text_lower = text.lower()

        for pattern, result in self.project_patterns.items():
            if re.search(pattern, text_lower):
                return result

        return {"type": "custom", "tech": []}

    async def _detect_technologies_async(self, text: str, quick_result: Dict) -> List[str]:
        """
        AI-first technology detection.

        Priority:
        1. AI-First Engine (semantic understanding)
        2. Regex patterns (deprecated fallback)
        """
        # Try AI-First Engine
        if self.ai_engine:
            try:
                result = await self.ai_engine.detect_technologies(text)
                if result.success and result.result:
                    techs = result.result.get("technologies", [])
                    tech_names = [t.get("name", "").lower() for t in techs if t]
                    if tech_names:
                        logger.debug(f"AI-first detected {len(tech_names)} technologies")
                        return tech_names
            except Exception as e:
                logger.debug(f"AI-first tech detection failed: {e}")

        # Fallback to regex (deprecated)
        return self._regex_detect_technologies(text, quick_result)

    def _detect_technologies(self, text: str, quick_result: Dict) -> List[str]:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._regex_detect_technologies(text, quick_result)
            return loop.run_until_complete(
                self._detect_technologies_async(text, quick_result)
            )
        except RuntimeError:
            return self._regex_detect_technologies(text, quick_result)

    def _regex_detect_technologies(self, text: str, quick_result: Dict) -> List[str]:
        """DEPRECATED: Regex-based technology detection. Use AI-first instead."""
        text_lower = text.lower()
        detected = set(quick_result.get("tech", []))

        for pattern, tech in self.tech_patterns.items():
            if re.search(pattern, text_lower):
                detected.add(tech)

        return list(detected)

    def _extract_summary(self, text: str) -> str:
        """Extract a concise summary."""
        # Take first sentence or first 100 chars
        sentences = text.split(".")
        if sentences:
            summary = sentences[0].strip()
            if len(summary) > 150:
                summary = summary[:147] + "..."
            return summary
        return text[:100]

    async def _extract_features_async(self, text: str) -> List[Dict[str, Any]]:
        """
        AI-first feature extraction.

        Priority:
        1. AI-First Engine (semantic understanding)
        2. Regex patterns (deprecated fallback)
        """
        # Try AI-First Engine
        if self.ai_engine:
            try:
                result = await self.ai_engine.extract_features(text)
                if result.success and result.result:
                    ai_features = result.result.get("features", [])
                    features = []
                    for f in ai_features:
                        features.append({
                            "description": f.get("name", ""),
                            "priority": f.get("priority", "medium"),
                            "subfeatures": f.get("subfeatures", [])
                        })
                    if features:
                        logger.debug(f"AI-first extracted {len(features)} features")
                        return features
            except Exception as e:
                logger.debug(f"AI-first feature extraction failed: {e}")

        # Fallback to regex (deprecated)
        return self._regex_extract_features(text)

    def _extract_features(self, text: str) -> List[Dict[str, Any]]:
        """Sync wrapper for backward compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._regex_extract_features(text)
            return loop.run_until_complete(
                self._extract_features_async(text)
            )
        except RuntimeError:
            return self._regex_extract_features(text)

    def _regex_extract_features(self, text: str) -> List[Dict[str, Any]]:
        """DEPRECATED: Regex-based feature extraction. Use AI-first instead."""
        features = []

        # Look for bullet points or numbered lists
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # Match bullet points or numbers
            if re.match(r"^[-*•]\s+", line) or re.match(r"^\d+[.)]\s+", line):
                feature_text = re.sub(r"^[-*•\d.)]+\s*", "", line).strip()
                if feature_text:
                    features.append({
                        "description": feature_text,
                        "priority": self._infer_priority(feature_text)
                    })

        # Look for "should", "must", "need" patterns
        patterns = [
            r"should\s+(.+?)(?:\.|$)",
            r"must\s+(.+?)(?:\.|$)",
            r"needs?\s+to\s+(.+?)(?:\.|$)",
            r"want\s+(.+?)(?:\.|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) > 10:  # Ignore very short matches
                    features.append({
                        "description": match.strip(),
                        "priority": "medium"
                    })

        return features

    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints and limitations."""
        constraints = []

        # Patterns indicating constraints
        patterns = [
            r"(?:no|without|don't|avoid)\s+(.+?)(?:\.|,|$)",
            r"must\s+not\s+(.+?)(?:\.|,|$)",
            r"limit(?:ed)?\s+to\s+(.+?)(?:\.|,|$)",
            r"only\s+(.+?)(?:\.|,|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            constraints.extend([m.strip() for m in matches if len(m) > 5])

        return constraints

    def _extract_success_criteria(self, text: str) -> List[str]:
        """Extract success criteria."""
        criteria = []

        # Look for explicit success indicators
        patterns = [
            r"success(?:ful)?\s+(?:if|when)\s+(.+?)(?:\.|$)",
            r"complete(?:d)?\s+when\s+(.+?)(?:\.|$)",
            r"done\s+when\s+(.+?)(?:\.|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            criteria.extend([m.strip() for m in matches])

        # Default criteria based on project type
        if not criteria:
            criteria = [
                "All code passes linting",
                "All tests pass",
                "Build completes successfully",
                "Core functionality works as described"
            ]

        return criteria

    def _find_unclear_points(self, text: str) -> List[str]:
        """Identify unclear or ambiguous points."""
        unclear = []

        # Very short objectives are unclear
        if len(text) < 50:
            unclear.append("Objective is very brief - more details would help")

        # Questions indicate uncertainty
        if "?" in text:
            unclear.append("Objective contains questions that need answers")

        # Vague terms
        vague_terms = ["something", "somehow", "maybe", "possibly", "etc", "various"]
        for term in vague_terms:
            if term in text.lower():
                unclear.append(f"Vague term '{term}' needs clarification")

        # Missing key details for certain project types
        text_lower = text.lower()
        if "api" in text_lower and "endpoint" not in text_lower:
            unclear.append("API mentioned but no endpoints specified")
        if "database" in text_lower and not any(
            db in text_lower for db in ["postgres", "mysql", "mongo", "sqlite"]
        ):
            unclear.append("Database mentioned but type not specified")

        return unclear

    def _estimate_complexity(self, text: str) -> str:
        """Estimate project complexity."""
        score = 0

        # Length indicates complexity
        if len(text) > 500:
            score += 2
        elif len(text) > 200:
            score += 1

        # Feature count
        features = self._extract_features(text)
        score += len(features) // 3

        # Technology count
        text_lower = text.lower()
        tech_count = sum(1 for p in self.tech_patterns if re.search(p, text_lower))
        score += tech_count // 2

        # Keywords indicating complexity
        complex_keywords = [
            "authentication", "payment", "real-time", "websocket",
            "microservices", "kubernetes", "ai", "ml", "machine learning"
        ]
        for keyword in complex_keywords:
            if keyword in text_lower:
                score += 1

        if score <= 2:
            return "low"
        elif score <= 5:
            return "medium"
        elif score <= 8:
            return "high"
        else:
            return "very_high"

    def _suggest_approach(self, text: str, quick_result: Dict) -> str:
        """Suggest an implementation approach."""
        project_type = quick_result.get("type", "custom")

        approaches = {
            "todo_app": "Start with data model, then CRUD API, then UI components",
            "api": "Design endpoints first, implement with FastAPI, add tests",
            "dashboard": "Set up data fetching, create chart components, build layout",
            "mobile": "Initialize Expo project, create navigation, build screens",
            "cli": "Define commands with Click, implement core logic, add help text",
            "website": "Create pages, add components, style with Tailwind",
            "ecommerce": "Set up product catalog, cart, checkout flow with Stripe",
            "blog": "Configure MDX, create post templates, build listing pages",
            "wordpress": "Set up theme structure, create templates, add customizer",
            "scraper": "Analyze target site, implement scraping logic, handle data"
        }

        return approaches.get(project_type, "Analyze requirements, design architecture, implement incrementally")

    def _infer_priority(self, feature_text: str) -> str:
        """Infer priority from feature text."""
        text_lower = feature_text.lower()

        high_indicators = ["must", "critical", "essential", "required", "core"]
        low_indicators = ["nice to have", "optional", "could", "might", "bonus"]

        for indicator in high_indicators:
            if indicator in text_lower:
                return "high"

        for indicator in low_indicators:
            if indicator in text_lower:
                return "low"

        return "medium"

    def _to_dict(self, parsed: ParsedObjective) -> Dict[str, Any]:
        """Convert ParsedObjective to dictionary."""
        result = {
            "original": parsed.original,
            "summary": parsed.summary,
            "project_type": parsed.project_type,
            "technologies": parsed.technologies,
            "features": parsed.features,
            "constraints": parsed.constraints,
            "success_criteria": parsed.success_criteria,
            "unclear_points": parsed.unclear_points,
            "estimated_complexity": parsed.estimated_complexity,
            "suggested_approach": parsed.suggested_approach,
            "requires_clarification": parsed.requires_clarification
        }

        # Add AI-specific fields if available
        if parsed.projects is not None:
            result["projects"] = parsed.projects
            result["is_multi_project"] = len(parsed.projects) > 1
            # Extract project_name from first project for backward compatibility
            # This ensures main.py gets the AI-generated project name
            if parsed.projects and parsed.projects[0].get("name"):
                result["project_name"] = parsed.projects[0]["name"]

        if parsed.ai_analysis is not None:
            result["ai_analysis"] = parsed.ai_analysis
            result["ai_parsed"] = True
        else:
            result["ai_parsed"] = False

        return result
