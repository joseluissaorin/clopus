# =============================================================================
# CLOPUS v3 Objective Parser
# =============================================================================
"""
Parses user objectives into structured, actionable components.
Uses Claude to understand and decompose complex objectives.
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


class ObjectiveParser:
    """Parse and analyze user objectives."""

    def __init__(self, memory_client, confidence_engine):
        self.memory = memory_client
        self.confidence = confidence_engine

        # Common project patterns for quick parsing
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

        # Technology detection patterns
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

    async def parse(self, objective_text: str) -> Dict[str, Any]:
        """Parse an objective into structured components."""
        logger.info(f"Parsing objective: {objective_text[:100]}...")

        # Quick pattern matching for common cases
        quick_result = self._quick_parse(objective_text)

        # Get relevant context from memory
        context = await self.memory.get_relevant_context(objective_text)

        # Build parsed result
        parsed = ParsedObjective(
            original=objective_text,
            summary=self._extract_summary(objective_text),
            project_type=quick_result.get("type", "custom"),
            technologies=self._detect_technologies(objective_text, quick_result),
            features=self._extract_features(objective_text),
            constraints=self._extract_constraints(objective_text),
            success_criteria=self._extract_success_criteria(objective_text),
            unclear_points=self._find_unclear_points(objective_text),
            estimated_complexity=self._estimate_complexity(objective_text),
            suggested_approach=self._suggest_approach(objective_text, quick_result),
            requires_clarification=False
        )

        # Check if clarification needed
        parsed.requires_clarification = len(parsed.unclear_points) > 0

        # Store parsed objective in memory for learning
        await self.memory.store_learning(
            f"Parsed objective: {parsed.summary}\nType: {parsed.project_type}\nTech: {', '.join(parsed.technologies)}",
            tags=["objective_parsing", parsed.project_type]
        )

        return self._to_dict(parsed)

    def _quick_parse(self, text: str) -> Dict[str, Any]:
        """Quick pattern-based parsing."""
        text_lower = text.lower()

        for pattern, result in self.project_patterns.items():
            if re.search(pattern, text_lower):
                return result

        return {"type": "custom", "tech": []}

    def _detect_technologies(self, text: str, quick_result: Dict) -> List[str]:
        """Detect mentioned technologies."""
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

    def _extract_features(self, text: str) -> List[Dict[str, Any]]:
        """Extract feature requirements."""
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
        return {
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
