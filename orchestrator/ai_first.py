# =============================================================================
# CLOPUS AI-First Intelligence Layer
# =============================================================================
"""
Replaces ALL regex/pattern matching with Claude Code intelligence.

PHILOSOPHY:
- Every decision point is a potential Claude call
- Regex is NEVER the primary approach, only emergency fallback
- Claude understands context, intent, and semantics - regex doesn't

This module provides AI-first alternatives to common operations:
1. Artifact inference (what files should a task create?)
2. Project path detection (where should this task run?)
3. Duplicate detection (are these tasks semantically the same?)
4. Technology detection (what stack is this project using?)
5. Feature extraction (what features are being requested?)
6. Skill matching (which skills are relevant for this task?)
7. Entity extraction (what models, components, endpoints are mentioned?)
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# AI-FIRST INFERENCE ENGINE
# =============================================================================

@dataclass
class AIInferenceResult:
    """Result from an AI inference operation."""
    success: bool
    result: Any
    confidence: float  # 0.0 - 1.0
    reasoning: str
    fallback_used: bool = False


class AIFirstEngine:
    """
    Central AI-first intelligence engine for CLOPUS.

    Replaces all regex/pattern matching with Claude Code intelligence.
    Uses worker pool to dispatch inference tasks to available workers.
    """

    def __init__(self, worker_pool, memory_client=None):
        self.worker_pool = worker_pool
        self.memory = memory_client

        # Cache for repeated queries (reduces API calls)
        self._cache: Dict[str, AIInferenceResult] = {}
        self._cache_ttl = 300  # 5 minutes

    # =========================================================================
    # ARTIFACT INFERENCE
    # =========================================================================

    async def infer_artifacts(
        self,
        task_title: str,
        task_description: str,
        project_context: Optional[Dict] = None
    ) -> AIInferenceResult:
        """
        AI-first artifact inference.

        Instead of regex patterns like:
            r'create\s+(?:file\s+)?["\']?([a-z0-9_/.-]+\.py)["\']?'

        We ask Claude: "What files should this task create?"

        Claude understands:
        - "Implement user authentication" → auth.py, middleware/auth.py, tests/test_auth.py
        - "Add dark mode toggle" → ThemeToggle.tsx, theme.css, useTheme.ts
        - Context from project structure
        """
        prompt = f"""TASK: Infer Expected Artifacts

Given this task, what files, endpoints, or other artifacts should it create?

Task Title: {task_title}
Task Description: {task_description}
{f'Project Context: {json.dumps(project_context, indent=2)}' if project_context else ''}

RESPOND WITH JSON ONLY:
{{
    "artifacts": [
        {{"type": "file", "path": "path/to/file.py", "purpose": "why this file"}},
        {{"type": "endpoint", "path": "/api/users", "method": "POST", "purpose": "why"}},
        {{"type": "component", "name": "UserProfile", "path": "src/components/UserProfile.tsx"}}
    ],
    "confidence": 0.85,
    "reasoning": "Based on the task description..."
}}"""

        return await self._dispatch_inference("ARTIFACT_INFERENCE", prompt)

    # =========================================================================
    # PROJECT PATH DETECTION
    # =========================================================================

    async def detect_project_path(
        self,
        task_title: str,
        task_description: str,
        available_projects: List[str],
        task_result: Optional[str] = None
    ) -> AIInferenceResult:
        """
        AI-first project path detection.

        Instead of regex like:
            r'(?:Project Path:|Project:)\s*(/workspace/[\w\-]+)'

        We ask Claude: "Which project does this task belong to?"

        Claude understands:
        - "Fix the API endpoint" + projects=[nexus-api, nexus-web] → nexus-api
        - "Update the React component" → web project
        - Context from task results
        """
        prompt = f"""TASK: Detect Project Path

Which project should this task run in?

Task Title: {task_title}
Task Description: {task_description}
{f'Task Result: {task_result[:500]}...' if task_result else ''}

Available Projects: {json.dumps(available_projects)}

RESPOND WITH JSON ONLY:
{{
    "project_path": "/workspace/project-name",
    "confidence": 0.9,
    "reasoning": "This task mentions X which is in project Y"
}}"""

        return await self._dispatch_inference("PROJECT_DETECTION", prompt)

    # =========================================================================
    # DUPLICATE DETECTION
    # =========================================================================

    async def check_duplicate(
        self,
        task1_title: str,
        task1_description: str,
        task2_title: str,
        task2_description: str
    ) -> AIInferenceResult:
        """
        AI-first duplicate detection.

        Instead of Jaccard similarity on word sets:
            intersection = len(words1 & words2)
            similarity = intersection / union

        We ask Claude: "Are these semantically the same task?"

        Claude understands:
        - "Create user model" vs "Implement User SQLAlchemy model" → DUPLICATE
        - "Add login endpoint" vs "Create user registration" → NOT DUPLICATE
        - Intent, not just word overlap
        """
        prompt = f"""TASK: Check for Semantic Duplicates

Are these two tasks semantically the same (doing the same work)?

Task 1:
  Title: {task1_title}
  Description: {task1_description}

Task 2:
  Title: {task2_title}
  Description: {task2_description}

RESPOND WITH JSON ONLY:
{{
    "is_duplicate": true/false,
    "similarity": 0.95,
    "reasoning": "Both tasks are creating the same...",
    "differences": ["Task 1 also includes X", "Task 2 focuses on Y"]
}}"""

        return await self._dispatch_inference("DUPLICATE_CHECK", prompt)

    # =========================================================================
    # TECHNOLOGY DETECTION
    # =========================================================================

    async def detect_technologies(
        self,
        objective_text: str,
        project_files: Optional[List[str]] = None
    ) -> AIInferenceResult:
        """
        AI-first technology detection.

        Instead of regex patterns like:
            r'\breact\b': "react"
            r'\bfastapi\b': "fastapi"

        We ask Claude: "What technologies does this project use?"

        Claude understands:
        - "Modern web app" → React, TypeScript, Tailwind (inferred)
        - package.json contents → actual dependencies
        - Context clues like "fast API" meaning FastAPI
        """
        prompt = f"""TASK: Detect Technologies

What technologies, frameworks, and tools should this project use?

Objective: {objective_text}
{f'Existing Files: {json.dumps(project_files[:20])}' if project_files else ''}

Consider:
- Explicit mentions in the objective
- Implied technologies (e.g., "web app" implies a frontend framework)
- Best practices for the type of project
- Compatibility between technologies

RESPOND WITH JSON ONLY:
{{
    "technologies": [
        {{"name": "React", "category": "frontend", "confidence": 0.95, "reason": "explicitly mentioned"}},
        {{"name": "TypeScript", "category": "language", "confidence": 0.8, "reason": "implied by React + modern"}}
    ],
    "stack_summary": "React + TypeScript frontend with FastAPI backend",
    "recommendations": ["Consider adding Tailwind for styling"]
}}"""

        return await self._dispatch_inference("TECH_DETECTION", prompt)

    # =========================================================================
    # FEATURE EXTRACTION
    # =========================================================================

    async def extract_features(
        self,
        objective_text: str
    ) -> AIInferenceResult:
        """
        AI-first feature extraction.

        Instead of regex like:
            r"^[-*•]\s+" for bullet points
            r"^\d+[.)]\s+" for numbered lists

        We ask Claude: "What features are being requested?"

        Claude understands:
        - "with dark mode and user auth" → [dark mode, user authentication]
        - Implicit features (login implies signup, logout, password reset)
        - Priority based on mention order and emphasis
        """
        prompt = f"""TASK: Extract Features

What features are being requested in this objective?

Objective: {objective_text}

Extract BOTH:
1. Explicitly mentioned features
2. Implied/necessary features (e.g., login implies logout)

RESPOND WITH JSON ONLY:
{{
    "features": [
        {{"name": "User Authentication", "explicit": true, "priority": "high", "subfeatures": ["login", "logout", "signup"]}},
        {{"name": "Dark Mode", "explicit": true, "priority": "medium", "subfeatures": ["theme toggle", "system preference detection"]}}
    ],
    "total_scope": "medium",
    "missing_clarifications": ["Which OAuth providers to support?"]
}}"""

        return await self._dispatch_inference("FEATURE_EXTRACTION", prompt)

    # =========================================================================
    # SKILL MATCHING
    # =========================================================================

    async def match_skills(
        self,
        task_description: str,
        available_skills: List[Dict]
    ) -> AIInferenceResult:
        """
        AI-first skill matching.

        Instead of word overlap:
            words = re.findall(r'\b[a-zA-Z]+\b', description.lower())

        We ask Claude: "Which skills are relevant for this task?"

        Claude understands:
        - "Implement REST API" → [fastapi, api-design, testing]
        - Semantic relevance, not just keyword matching
        """
        skill_summaries = [
            {"name": s.get("name"), "description": s.get("description", "")[:100]}
            for s in available_skills
        ]

        prompt = f"""TASK: Match Relevant Skills

Which skills should be loaded for this task?

Task: {task_description}

Available Skills:
{json.dumps(skill_summaries, indent=2)}

RESPOND WITH JSON ONLY:
{{
    "matched_skills": [
        {{"name": "fastapi", "relevance": 0.95, "reason": "Task involves API development"}},
        {{"name": "testing", "relevance": 0.7, "reason": "APIs should have tests"}}
    ],
    "skill_load_order": ["fastapi", "api-design", "testing"]
}}"""

        return await self._dispatch_inference("SKILL_MATCHING", prompt)

    # =========================================================================
    # ENTITY EXTRACTION
    # =========================================================================

    async def extract_entities(
        self,
        text: str,
        entity_types: List[str] = None
    ) -> AIInferenceResult:
        """
        AI-first entity extraction.

        Instead of regex like:
            r'(?:create|implement|add)\s+(\w+)\s+(?:model|component)'

        We ask Claude: "What entities are mentioned?"

        Claude understands:
        - "User profile with avatar" → User (model), Avatar (component)
        - Context-dependent entity types
        - Relationships between entities
        """
        entity_types = entity_types or ["model", "component", "endpoint", "service", "table"]

        prompt = f"""TASK: Extract Entities

What entities (models, components, endpoints, etc.) are mentioned?

Text: {text}

Entity Types to Look For: {json.dumps(entity_types)}

RESPOND WITH JSON ONLY:
{{
    "entities": [
        {{"name": "User", "type": "model", "context": "user profile", "attributes": ["name", "email", "avatar"]}},
        {{"name": "UserProfile", "type": "component", "context": "display user info"}},
        {{"name": "/users", "type": "endpoint", "methods": ["GET", "POST", "PUT"]}}
    ],
    "relationships": [
        {{"from": "UserProfile", "to": "User", "type": "displays"}}
    ]
}}"""

        return await self._dispatch_inference("ENTITY_EXTRACTION", prompt)

    # =========================================================================
    # CONFIDENCE EVALUATION
    # =========================================================================

    async def evaluate_decision_confidence(
        self,
        decision_type: str,
        context: Dict[str, Any],
        past_decisions: Optional[List[Dict]] = None
    ) -> AIInferenceResult:
        """
        AI-first confidence evaluation.

        Instead of weighted formulas:
            score = complexity * 0.2 + past_success * 0.25 + ...

        We ask Claude: "How confident should we be about this decision?"

        Claude understands:
        - "Billing integration" → ALWAYS ASK (high risk)
        - "Similar to 5 past successes" → HIGH CONFIDENCE
        - "Vague requirements" → ASK FOR CLARIFICATION
        """
        past_summary = ""
        if past_decisions:
            recent = past_decisions[-5:]
            past_summary = f"\nRecent similar decisions: {json.dumps(recent, indent=2)}"

        prompt = f"""TASK: Evaluate Decision Confidence

Should we proceed autonomously or ask the user?

Decision Type: {decision_type}
Context: {json.dumps(context, indent=2)}
{past_summary}

CRITICAL RULES:
- Billing/payment decisions → ALWAYS ASK
- Production deployments → ALWAYS ASK
- Architecture changes → Usually ask unless simple
- Code style/formatting → NEVER ask
- Similar past successes → Proceed with high confidence

RESPOND WITH JSON ONLY:
{{
    "confidence": 0.75,
    "should_ask": false,
    "reasoning": "This is similar to past successful implementations...",
    "risk_factors": ["None significant"],
    "suggested_question": null
}}"""

        return await self._dispatch_inference("CONFIDENCE_EVALUATION", prompt)

    # =========================================================================
    # WORKER ROUTING
    # =========================================================================

    async def select_best_worker(
        self,
        task_description: str,
        available_workers: List[Dict],
        worker_history: Optional[Dict] = None
    ) -> AIInferenceResult:
        """
        AI-first worker selection.

        Instead of keyword matching:
            if "debug" in task → debugger
            if "test" in task → tester

        We ask Claude: "Which worker is best for this task?"

        Claude understands:
        - "CSS layout issue" → designer might help, not just debugger
        - "Complex state management bug" → debugger > coder
        - Worker past performance
        """
        workers_info = json.dumps(available_workers, indent=2)
        history_info = ""
        if worker_history:
            history_info = f"\nWorker Performance History: {json.dumps(worker_history, indent=2)}"

        prompt = f"""TASK: Select Best Worker

Which worker should handle this task?

Task: {task_description}

Available Workers:
{workers_info}
{history_info}

Consider:
- Task requirements and complexity
- Worker specializations
- Current worker load (prefer idle workers)
- Past performance on similar tasks

RESPOND WITH JSON ONLY:
{{
    "selected_worker": "debugger",
    "worker_id": 5,
    "confidence": 0.9,
    "reasoning": "This debugging task requires investigation skills",
    "fallback_worker": "coder",
    "parallel_candidates": []
}}"""

        return await self._dispatch_inference("WORKER_SELECTION", prompt)

    # =========================================================================
    # PROJECT ANALYSIS
    # =========================================================================

    async def analyze_project_requirements(
        self,
        objective: str,
        existing_files: Optional[List[str]] = None
    ) -> AIInferenceResult:
        """
        AI-first project type and stack detection.

        Instead of keyword matching:
            if "react" in objective → react-typescript

        We ask Claude: "What type of project is this and what stack?"

        Claude understands:
        - "Real-time collaborative" → WebSocket, Redis, specific architecture
        - "Admin panel" → Dashboard patterns, auth, RBAC
        - Context from existing files
        """
        files_info = ""
        if existing_files:
            files_info = f"\nExisting Files: {json.dumps(existing_files[:30])}"

        prompt = f"""TASK: Analyze Project Requirements

What type of project is this and what technologies should it use?

Objective: {objective}
{files_info}

Analyze:
1. Project type (web app, API, CLI, mobile, etc.)
2. Recommended technology stack
3. Architecture patterns needed
4. Key features to implement

RESPOND WITH JSON ONLY:
{{
    "project_type": "real-time-web-app",
    "category": "collaborative",
    "recommended_stack": {{
        "frontend": ["React", "TypeScript", "TailwindCSS"],
        "backend": ["FastAPI", "WebSocket", "Redis"],
        "database": ["PostgreSQL"],
        "infrastructure": ["Docker"]
    }},
    "architecture_patterns": ["event-driven", "pub-sub"],
    "key_features": ["real-time sync", "collaboration", "presence"],
    "complexity": "high",
    "estimated_components": 15,
    "confidence": 0.85,
    "reasoning": "Real-time collaborative features require..."
}}"""

        return await self._dispatch_inference("PROJECT_ANALYSIS", prompt)

    async def analyze_project_completeness(
        self,
        project_path: str,
        objective: str,
        file_summary: Dict[str, Any]
    ) -> AIInferenceResult:
        """
        AI-first project state/completeness analysis.

        Instead of file existence checks:
            if dist_dir.exists() → completed

        We ask Claude: "How complete is this project?"

        Claude understands:
        - "3/5 endpoints implemented"
        - "Tests exist but coverage is low"
        - "Missing error handling"
        """
        prompt = f"""TASK: Analyze Project Completeness

How complete is this project relative to its objective?

Objective: {objective}
Project Path: {project_path}
File Summary: {json.dumps(file_summary, indent=2)}

Analyze:
1. What percentage of features are implemented?
2. What's missing or incomplete?
3. What's the quality of existing implementation?
4. What should be prioritized next?

RESPOND WITH JSON ONLY:
{{
    "completion_percentage": 65,
    "implemented_features": ["user auth", "basic CRUD"],
    "missing_features": ["real-time sync", "error handling"],
    "incomplete_features": ["tests (low coverage)", "documentation"],
    "quality_assessment": {{
        "code_quality": "good",
        "test_coverage": "low",
        "documentation": "minimal"
    }},
    "next_priorities": ["Add error handling", "Increase test coverage"],
    "blockers": [],
    "confidence": 0.8,
    "reasoning": "Based on file analysis..."
}}"""

        return await self._dispatch_inference("PROJECT_COMPLETENESS", prompt)

    # =========================================================================
    # DESIGN ANALYSIS
    # =========================================================================

    async def analyze_design_system(
        self,
        design_doc: str,
        project_context: Optional[str] = None
    ) -> AIInferenceResult:
        """
        AI-first design system analysis.

        Instead of regex for hex colors:
            re.findall(r'#[0-9A-Fa-f]{6}', doc)

        We ask Claude: "Extract and understand the design system"

        Claude understands:
        - Color semantic meanings (primary for CTAs)
        - Spacing system logic (8px base)
        - Design intent and consistency
        """
        context_info = ""
        if project_context:
            context_info = f"\nProject Context: {project_context}"

        prompt = f"""TASK: Analyze Design System

Extract and understand this design system.

Design Document:
{design_doc[:3000]}
{context_info}

Extract:
1. Color palette with semantic meanings
2. Typography scale and usage
3. Spacing system
4. Component patterns
5. Design intent and principles

RESPOND WITH JSON ONLY:
{{
    "colors": {{
        "primary": {{"hex": "#3B82F6", "usage": "CTAs, links, emphasis"}},
        "secondary": {{"hex": "#6366F1", "usage": "Supporting elements"}},
        "background": {{"hex": "#FFFFFF", "usage": "Page background"}},
        "text": {{"hex": "#1F2937", "usage": "Body text"}}
    }},
    "typography": {{
        "heading_font": "Inter",
        "body_font": "Inter",
        "scale": ["text-xs", "text-sm", "text-base", "text-lg", "text-xl"]
    }},
    "spacing": {{
        "base": "4px",
        "scale": ["4px", "8px", "16px", "24px", "32px", "48px"]
    }},
    "design_principles": ["Clean", "Accessible", "Consistent"],
    "component_patterns": ["Cards with shadow", "Rounded buttons"],
    "confidence": 0.85,
    "reasoning": "Design follows modern minimal approach..."
}}"""

        return await self._dispatch_inference("DESIGN_ANALYSIS", prompt)

    # =========================================================================
    # CONTEXT RELEVANCE
    # =========================================================================

    async def determine_relevant_context(
        self,
        task_description: str,
        available_memories: List[Dict],
        project_history: Optional[List[Dict]] = None
    ) -> AIInferenceResult:
        """
        AI-first context relevance determination.

        Instead of keyword triggers:
            if "color" in task → inject design context

        We ask Claude: "What context is actually relevant?"

        Claude understands:
        - "This component needs auth flow context"
        - "Similar to UserProfile we built yesterday"
        - Semantic relevance, not just keywords
        """
        memories_summary = json.dumps(available_memories[:20], indent=2)
        history_info = ""
        if project_history:
            history_info = f"\nProject History: {json.dumps(project_history[-10:], indent=2)}"

        prompt = f"""TASK: Determine Relevant Context

What context should be injected into this task?

Task: {task_description}

Available Memories:
{memories_summary}
{history_info}

Select memories that are:
1. Directly relevant to the task
2. Provide useful patterns or solutions
3. Contain warnings about pitfalls
4. Help with consistency (design, code style)

RESPOND WITH JSON ONLY:
{{
    "relevant_memories": [
        {{"id": "mem_123", "relevance": 0.95, "reason": "Same auth pattern needed"}},
        {{"id": "mem_456", "relevance": 0.7, "reason": "Contains useful error handling"}}
    ],
    "inject_design_system": true,
    "inject_patterns": ["auth-flow", "error-handling"],
    "warnings_to_include": ["Watch out for race conditions"],
    "confidence": 0.85,
    "reasoning": "Task involves authentication which..."
}}"""

        return await self._dispatch_inference("CONTEXT_RELEVANCE", prompt)

    async def extract_learnings(
        self,
        task_result: str,
        task_type: str,
        success: bool
    ) -> AIInferenceResult:
        """
        AI-first learning extraction.

        Instead of regex patterns:
            if "solved by" in result → extract solution

        We ask Claude: "What can we learn from this?"

        Claude understands:
        - This approach worked, extract the pattern
        - This failed because X, store as anti-pattern
        - Novel solution worth remembering
        """
        prompt = f"""TASK: Extract Learnings

What can we learn from this task result?

Task Type: {task_type}
Success: {success}
Result:
{task_result[:2000]}

Extract:
1. Patterns that worked well
2. Solutions to specific problems
3. Warnings/anti-patterns to avoid
4. Reusable code snippets

RESPOND WITH JSON ONLY:
{{
    "patterns": [
        {{"name": "auth-middleware-pattern", "description": "JWT validation in middleware", "reusable": true}}
    ],
    "solutions": [
        {{"problem": "Token expiry handling", "solution": "Refresh token rotation", "confidence": 0.9}}
    ],
    "warnings": [
        {{"issue": "Race condition in concurrent updates", "prevention": "Use optimistic locking"}}
    ],
    "code_snippets": [
        {{"name": "jwt-middleware", "language": "python", "snippet": "...", "context": "FastAPI auth"}}
    ],
    "should_store": true,
    "storage_priority": "high",
    "confidence": 0.85,
    "reasoning": "This contains a novel approach to..."
}}"""

        return await self._dispatch_inference("LEARNING_EXTRACTION", prompt)

    # =========================================================================
    # VALIDATION INTELLIGENCE
    # =========================================================================

    async def evaluate_validation_result(
        self,
        stage: str,
        result: Dict[str, Any],
        project_stage: str,
        quality_requirements: Optional[Dict] = None
    ) -> AIInferenceResult:
        """
        AI-first validation evaluation.

        Instead of binary pass/fail:
            if errors > 0 → fail

        We ask Claude: "Is this acceptable given the context?"

        Claude understands:
        - "This warning is OK for MVP"
        - "This error is critical - blocks users"
        - Context-dependent quality gates
        """
        requirements_info = ""
        if quality_requirements:
            requirements_info = f"\nQuality Requirements: {json.dumps(quality_requirements)}"

        prompt = f"""TASK: Evaluate Validation Result

Should this validation result block progress?

Stage: {stage}
Project Stage: {project_stage}
Result: {json.dumps(result, indent=2)}
{requirements_info}

Consider:
1. Severity of issues found
2. Project stage (MVP vs production)
3. User impact of the issues
4. Effort to fix vs benefit

RESPOND WITH JSON ONLY:
{{
    "should_block": false,
    "severity": "low",
    "critical_issues": [],
    "acceptable_issues": ["Minor style warning"],
    "suggested_fixes": [
        {{"issue": "Missing type annotation", "fix": "Add return type", "priority": "low"}}
    ],
    "fix_now": [],
    "fix_later": ["Style improvements"],
    "confidence": 0.85,
    "reasoning": "For MVP stage, these warnings are acceptable..."
}}"""

        return await self._dispatch_inference("VALIDATION_EVALUATION", prompt)

    # =========================================================================
    # ERROR RECOVERY
    # =========================================================================

    async def diagnose_and_recommend(
        self,
        error: str,
        task_context: Dict[str, Any],
        attempt_history: Optional[List[Dict]] = None
    ) -> AIInferenceResult:
        """
        AI-first error diagnosis and recovery.

        Instead of fixed retry:
            for attempt in range(3): retry()

        We ask Claude: "What caused this and how to fix it?"

        Claude understands:
        - "Rate limit - wait 60s"
        - "Missing dependency - install first"
        - "Logic error - fix code, don't retry"
        """
        history_info = ""
        if attempt_history:
            history_info = f"\nPrevious Attempts: {json.dumps(attempt_history, indent=2)}"

        prompt = f"""TASK: Diagnose Error and Recommend Action

What caused this error and how should we proceed?

Error: {error}
Task Context: {json.dumps(task_context, indent=2)}
{history_info}

Diagnose:
1. Root cause of the error
2. Is this transient or persistent?
3. What action should we take?
4. If retrying, what should change?

RESPOND WITH JSON ONLY:
{{
    "diagnosis": {{
        "root_cause": "Rate limit exceeded",
        "error_type": "transient",
        "is_recoverable": true
    }},
    "recommended_action": "wait_and_retry",
    "wait_seconds": 60,
    "should_retry": true,
    "retry_with_changes": {{"reduce_batch_size": true}},
    "fix_required": null,
    "escalate_to_user": false,
    "confidence": 0.9,
    "reasoning": "Error message indicates rate limiting..."
}}"""

        return await self._dispatch_inference("ERROR_DIAGNOSIS", prompt)

    # =========================================================================
    # TASK DEPENDENCIES
    # =========================================================================

    async def analyze_task_dependencies(
        self,
        tasks: List[Dict[str, Any]]
    ) -> AIInferenceResult:
        """
        AI-first task dependency analysis.

        Instead of manual dependency specification:
            task.depends_on = ["task_123"]

        We ask Claude: "What are the dependencies between these tasks?"

        Claude understands:
        - "API must exist before frontend can call it"
        - "These 3 tasks can run in parallel"
        - Implicit dependencies from task descriptions
        """
        tasks_summary = json.dumps(tasks, indent=2)

        prompt = f"""TASK: Analyze Task Dependencies

What are the dependencies between these tasks?

Tasks:
{tasks_summary}

Analyze:
1. Which tasks depend on others?
2. Which tasks can run in parallel?
3. What's the critical path?
4. Optimal execution order

RESPOND WITH JSON ONLY:
{{
    "dependencies": [
        {{"task": "task_2", "depends_on": ["task_1"], "reason": "Needs API endpoints"}},
        {{"task": "task_3", "depends_on": [], "reason": "Independent"}}
    ],
    "parallel_groups": [
        ["task_1", "task_3"],
        ["task_2", "task_4"]
    ],
    "critical_path": ["task_1", "task_2", "task_5"],
    "execution_order": ["task_1", "task_3", "task_2", "task_4", "task_5"],
    "bottlenecks": ["task_2 blocks multiple downstream tasks"],
    "confidence": 0.85,
    "reasoning": "Task 2 requires API from task 1..."
}}"""

        return await self._dispatch_inference("DEPENDENCY_ANALYSIS", prompt)

    # =========================================================================
    # KNOWLEDGE PATTERNS
    # =========================================================================

    async def identify_patterns(
        self,
        completed_task: Dict[str, Any],
        existing_patterns: List[Dict]
    ) -> AIInferenceResult:
        """
        AI-first pattern identification.

        Instead of manual pattern storage:
            await store_pattern(name, content)

        We ask Claude: "Is there a reusable pattern here?"

        Claude understands:
        - "This auth flow is reusable"
        - "Similar to existing pattern X"
        - "Novel approach worth storing"
        """
        existing_summary = json.dumps(existing_patterns[:10], indent=2)

        prompt = f"""TASK: Identify Reusable Patterns

Is there a reusable pattern in this completed task?

Completed Task:
{json.dumps(completed_task, indent=2)}

Existing Patterns:
{existing_summary}

Analyze:
1. Is there a novel pattern worth storing?
2. Is this similar to an existing pattern?
3. What makes this pattern reusable?
4. Quality and generalizability

RESPOND WITH JSON ONLY:
{{
    "has_pattern": true,
    "is_novel": true,
    "similar_to_existing": null,
    "pattern": {{
        "name": "jwt-refresh-rotation",
        "category": "authentication",
        "description": "Secure JWT refresh token rotation pattern",
        "use_cases": ["API auth", "Session management"],
        "code_template": "...",
        "tags": ["auth", "jwt", "security"]
    }},
    "quality_score": 0.85,
    "should_store": true,
    "confidence": 0.8,
    "reasoning": "This implements a secure refresh token pattern..."
}}"""

        return await self._dispatch_inference("PATTERN_IDENTIFICATION", prompt)

    # =========================================================================
    # COMMIT STRATEGY
    # =========================================================================

    async def plan_commits(
        self,
        changes: List[Dict[str, Any]],
        project_conventions: Optional[str] = None,
        recent_commits: Optional[List[str]] = None
    ) -> AIInferenceResult:
        """
        AI-first commit planning.

        Instead of one big commit:
            git commit -m "Changes"

        We ask Claude: "How should these changes be committed?"

        Claude understands:
        - Logical groupings of changes
        - Conventional commit format
        - Project-specific conventions
        """
        conventions_info = ""
        if project_conventions:
            conventions_info = f"\nProject Conventions: {project_conventions}"

        recent_info = ""
        if recent_commits:
            recent_info = f"\nRecent Commits: {json.dumps(recent_commits[-5:])}"

        prompt = f"""TASK: Plan Commits

How should these changes be committed?

Changes:
{json.dumps(changes, indent=2)}
{conventions_info}
{recent_info}

Plan:
1. Group related changes into logical commits
2. Write clear, conventional commit messages
3. Order commits logically
4. Identify any changes that should NOT be committed

RESPOND WITH JSON ONLY:
{{
    "commits": [
        {{
            "files": ["src/auth.py", "src/middleware.py"],
            "message": "feat(auth): add JWT authentication middleware",
            "type": "feature",
            "scope": "auth"
        }},
        {{
            "files": ["tests/test_auth.py"],
            "message": "test(auth): add unit tests for JWT validation",
            "type": "test",
            "scope": "auth"
        }}
    ],
    "do_not_commit": ["*.env", "*.local"],
    "commit_order": [0, 1],
    "confidence": 0.9,
    "reasoning": "Separating feature and test commits for clarity..."
}}"""

        return await self._dispatch_inference("COMMIT_PLANNING", prompt)

    # =========================================================================
    # TEST STRATEGY
    # =========================================================================

    async def select_tests(
        self,
        changes: List[Dict[str, Any]],
        available_tests: List[str],
        test_history: Optional[Dict] = None
    ) -> AIInferenceResult:
        """
        AI-first test selection.

        Instead of running all tests:
            npm test

        We ask Claude: "Which tests should we run?"

        Claude understands:
        - "Changed auth.py → run auth tests + integration"
        - "UI change → skip API tests, run E2E"
        - Historical test failures
        """
        history_info = ""
        if test_history:
            history_info = f"\nTest History: {json.dumps(test_history, indent=2)}"

        prompt = f"""TASK: Select Tests to Run

Which tests should we run for these changes?

Changes:
{json.dumps(changes, indent=2)}

Available Tests:
{json.dumps(available_tests, indent=2)}
{history_info}

Select:
1. Tests that MUST run (directly affected)
2. Tests that SHOULD run (related)
3. Tests that can be SKIPPED (unrelated)
4. Predicted failures based on changes

RESPOND WITH JSON ONLY:
{{
    "must_run": ["tests/test_auth.py", "tests/integration/test_login.py"],
    "should_run": ["tests/e2e/test_user_flow.py"],
    "can_skip": ["tests/test_utils.py", "tests/test_config.py"],
    "predicted_failures": [
        {{"test": "test_token_expiry", "reason": "Token logic changed", "confidence": 0.7}}
    ],
    "run_order": ["unit", "integration", "e2e"],
    "parallel_safe": ["test_auth.py", "test_utils.py"],
    "estimated_time_seconds": 45,
    "confidence": 0.85,
    "reasoning": "Changes to auth module require auth-related tests..."
}}"""

        return await self._dispatch_inference("TEST_SELECTION", prompt)

    # =========================================================================
    # DOCUMENTATION SYNC
    # =========================================================================

    async def suggest_doc_updates(
        self,
        changes: List[Dict[str, Any]],
        current_docs: str
    ) -> AIInferenceResult:
        """
        AI-first documentation sync.

        Instead of manual doc updates:
            # TODO: Update docs

        We ask Claude: "What documentation needs updating?"

        Claude understands:
        - "New endpoint added, update API section"
        - "Config changed, update setup instructions"
        - Keep docs in sync with code
        """
        prompt = f"""TASK: Suggest Documentation Updates

What documentation needs updating based on these changes?

Changes:
{json.dumps(changes, indent=2)}

Current Documentation:
{current_docs[:2000]}

Suggest:
1. Sections that need updating
2. New sections to add
3. Outdated content to remove
4. Examples that need updating

RESPOND WITH JSON ONLY:
{{
    "updates_needed": [
        {{
            "section": "API Reference",
            "action": "add",
            "content": "New /auth/refresh endpoint...",
            "priority": "high"
        }},
        {{
            "section": "Setup",
            "action": "update",
            "content": "Add JWT_SECRET to environment...",
            "priority": "medium"
        }}
    ],
    "new_sections": [
        {{"title": "Authentication", "content": "..."}}
    ],
    "outdated_content": ["Old token format example"],
    "confidence": 0.85,
    "reasoning": "New auth endpoints require API documentation..."
}}"""

        return await self._dispatch_inference("DOC_SYNC", prompt)

    # =========================================================================
    # QUALITY PREDICTION
    # =========================================================================

    async def predict_quality_issues(
        self,
        task_plan: Dict[str, Any],
        codebase_context: Optional[Dict] = None
    ) -> AIInferenceResult:
        """
        AI-first quality prediction.

        Instead of validating after implementation:
            result = await validate()

        We ask Claude: "What issues might this cause?"

        Claude understands:
        - "This approach will have performance issues"
        - "Missing error handling will cause failures"
        - Prevent issues before they happen
        """
        context_info = ""
        if codebase_context:
            context_info = f"\nCodebase Context: {json.dumps(codebase_context, indent=2)}"

        prompt = f"""TASK: Predict Quality Issues

What quality issues might this implementation have?

Task Plan:
{json.dumps(task_plan, indent=2)}
{context_info}

Predict:
1. Performance issues
2. Security vulnerabilities
3. Maintainability concerns
4. Missing error handling
5. Edge cases not covered

RESPOND WITH JSON ONLY:
{{
    "predicted_issues": [
        {{
            "type": "performance",
            "description": "N+1 query problem in user list",
            "severity": "medium",
            "prevention": "Use eager loading with joinedload()",
            "confidence": 0.8
        }},
        {{
            "type": "security",
            "description": "Missing input validation on user ID",
            "severity": "high",
            "prevention": "Add Pydantic validation",
            "confidence": 0.9
        }}
    ],
    "missing_considerations": ["Rate limiting", "Pagination"],
    "suggested_improvements": [
        {{"area": "error handling", "suggestion": "Add try-except for database operations"}}
    ],
    "overall_risk": "medium",
    "confidence": 0.8,
    "reasoning": "Database operations without transactions..."
}}"""

        return await self._dispatch_inference("QUALITY_PREDICTION", prompt)

    # =========================================================================
    # INTERNAL: Dispatch to Worker
    # =========================================================================

    async def _dispatch_inference(
        self,
        inference_type: str,
        prompt: str,
        timeout: int = 30
    ) -> AIInferenceResult:
        """Dispatch an inference task to an available worker."""

        # Check cache first
        cache_key = f"{inference_type}:{hash(prompt)}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug(f"Cache hit for {inference_type}")
            return cached

        try:
            # Use verificator worker for inference tasks
            result = await self.worker_pool.dispatch_verificator_task(
                task_type=inference_type,
                task_data={"prompt": prompt},
                timeout_seconds=timeout
            )

            if result and isinstance(result, dict):
                inference_result = AIInferenceResult(
                    success=True,
                    result=result,
                    confidence=result.get("confidence", 0.8),
                    reasoning=result.get("reasoning", ""),
                    fallback_used=False
                )

                # Cache the result
                self._cache[cache_key] = inference_result

                return inference_result

        except Exception as e:
            logger.warning(f"AI inference failed for {inference_type}: {e}")

        # Return failure result (caller should use fallback)
        return AIInferenceResult(
            success=False,
            result=None,
            confidence=0.0,
            reasoning=f"AI inference failed",
            fallback_used=True
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_ai_engine: Optional[AIFirstEngine] = None


def get_ai_engine() -> Optional[AIFirstEngine]:
    """Get the global AI engine instance."""
    return _ai_engine


def set_ai_engine(engine: AIFirstEngine) -> None:
    """Set the global AI engine instance."""
    global _ai_engine
    _ai_engine = engine


async def ai_infer_artifacts(
    task_title: str,
    task_description: str,
    project_context: Optional[Dict] = None
) -> List[str]:
    """
    Convenience function for artifact inference.

    Returns list of artifact paths, or empty list if AI fails.
    """
    engine = get_ai_engine()
    if not engine:
        return []

    result = await engine.infer_artifacts(task_title, task_description, project_context)

    if result.success and result.result:
        artifacts = result.result.get("artifacts", [])
        return [a.get("path", a.get("name", "")) for a in artifacts if a]

    return []


async def ai_detect_project(
    task_title: str,
    task_description: str,
    available_projects: List[str]
) -> Optional[str]:
    """
    Convenience function for project detection.

    Returns project path, or None if AI fails.
    """
    engine = get_ai_engine()
    if not engine:
        return None

    result = await engine.detect_project_path(
        task_title, task_description, available_projects
    )

    if result.success and result.result:
        return result.result.get("project_path")

    return None


async def ai_check_duplicate(
    task1_title: str,
    task1_desc: str,
    task2_title: str,
    task2_desc: str
) -> Tuple[bool, float]:
    """
    Convenience function for duplicate checking.

    Returns (is_duplicate, similarity), or (False, 0.0) if AI fails.
    """
    engine = get_ai_engine()
    if not engine:
        return False, 0.0

    result = await engine.check_duplicate(
        task1_title, task1_desc, task2_title, task2_desc
    )

    if result.success and result.result:
        return (
            result.result.get("is_duplicate", False),
            result.result.get("similarity", 0.0)
        )

    return False, 0.0
