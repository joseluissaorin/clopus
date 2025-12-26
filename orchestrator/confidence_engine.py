# =============================================================================
# CLOPUS v3 Confidence Engine
# =============================================================================
"""
Calculates decision confidence and learns from outcomes.
Core component for autonomous operation.
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging
import math

logger = logging.getLogger("clopus.confidence_engine")


@dataclass
class ConfidenceResult:
    """Result of confidence calculation."""
    score: float
    factors: Dict[str, float]
    reasoning: str
    should_ask: bool
    suggested_question: Optional[str] = None


class ConfidenceEngine:
    """Calculate and learn decision confidence."""

    def __init__(self, memory_client, config):
        self.memory = memory_client
        self.config = config
        self.threshold = config.threshold
        self.weights = config.weights
        self.learning_rate = config.learning_rate

        # Runtime adjustments based on outcomes
        self._weight_adjustments: Dict[str, float] = {}
        self._decision_history: List[Dict] = []

    async def calculate(
        self,
        decision_type: str,
        context: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for a decision."""
        factors = await self._evaluate_factors(decision_type, context)

        # Calculate weighted score
        total_weight = sum(self.weights.values())
        score = sum(
            factors.get(factor, 0.5) * weight
            for factor, weight in self.weights.items()
        ) / total_weight

        # Apply learned adjustments
        for factor, adjustment in self._weight_adjustments.items():
            if factor in factors:
                score += factors[factor] * adjustment * 0.1

        # Clamp to valid range
        score = max(0.0, min(1.0, score))

        logger.info(f"Confidence for {decision_type}: {score:.2f}")
        return score

    async def evaluate(
        self,
        decision_type: str,
        context: Dict[str, Any]
    ) -> ConfidenceResult:
        """Full confidence evaluation with reasoning."""
        factors = await self._evaluate_factors(decision_type, context)

        # Calculate score
        total_weight = sum(self.weights.values())
        score = sum(
            factors.get(factor, 0.5) * weight
            for factor, weight in self.weights.items()
        ) / total_weight

        # Apply adjustments
        for factor, adjustment in self._weight_adjustments.items():
            if factor in factors:
                score += factors[factor] * adjustment * 0.1

        score = max(0.0, min(1.0, score))

        # Generate reasoning
        reasoning = self._generate_reasoning(factors, score)

        # Determine if we should ask user
        should_ask = score < self.threshold

        # Generate suggested question if needed
        suggested_question = None
        if should_ask:
            suggested_question = self._generate_question(decision_type, factors, context)

        return ConfidenceResult(
            score=score,
            factors=factors,
            reasoning=reasoning,
            should_ask=should_ask,
            suggested_question=suggested_question
        )

    async def _evaluate_factors(
        self,
        decision_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Evaluate individual confidence factors."""
        factors = {}

        # Task complexity
        factors["task_complexity"] = await self._evaluate_complexity(context)

        # Similar past success
        factors["similar_past_success"] = await self._evaluate_past_success(
            decision_type, context
        )

        # Clear requirements
        factors["clear_requirements"] = self._evaluate_requirements_clarity(context)

        # Available context
        factors["available_context"] = await self._evaluate_available_context(context)

        # Domain familiarity
        factors["domain_familiarity"] = await self._evaluate_domain_familiarity(context)

        return factors

    async def _evaluate_complexity(self, context: Dict) -> float:
        """Evaluate task complexity factor."""
        complexity = context.get("estimated_complexity", "medium")
        complexity_scores = {
            "low": 0.9,
            "medium": 0.7,
            "high": 0.5,
            "very_high": 0.3
        }
        return complexity_scores.get(complexity, 0.5)

    async def _evaluate_past_success(
        self,
        decision_type: str,
        context: Dict
    ) -> float:
        """Evaluate based on similar past decisions."""
        # Search for similar past decisions
        query = f"{decision_type} {context.get('summary', '')}"
        similar = await self.memory.long_term.find_similar_decisions(query, n_results=5)

        if not similar:
            return 0.5  # Neutral if no history

        # Calculate success rate from similar decisions
        success_count = sum(
            1 for m in similar
            if m.metadata.get("outcome") == "success"
        )

        if len(similar) == 0:
            return 0.5

        return success_count / len(similar)

    def _evaluate_requirements_clarity(self, context: Dict) -> float:
        """Evaluate clarity of requirements."""
        unclear_points = context.get("unclear_points", [])
        features = context.get("features", [])
        original = context.get("original", "")

        score = 0.8  # Start high

        # Deduct for unclear points
        score -= len(unclear_points) * 0.15

        # Boost for explicit features
        if features:
            score += min(len(features) * 0.05, 0.2)

        # Deduct for very short objectives
        if len(original) < 50:
            score -= 0.2

        # Deduct for vague language
        vague_terms = ["something", "somehow", "maybe", "etc", "various", "stuff"]
        for term in vague_terms:
            if term in original.lower():
                score -= 0.1

        return max(0.1, min(1.0, score))

    async def _evaluate_available_context(self, context: Dict) -> float:
        """Evaluate available context quality."""
        score = 0.5

        # Check if we have relevant memories
        query = context.get("summary", context.get("original", ""))
        if query:
            memories = await self.memory.search_memories(query, n_results=3)
            if memories:
                # More relevant memories = higher confidence
                avg_relevance = sum(m.relevance_score or 0 for m in memories) / len(memories)
                score = 0.3 + avg_relevance * 0.7

        # Boost if technologies are specified
        technologies = context.get("technologies", [])
        if technologies:
            score += min(len(technologies) * 0.05, 0.2)

        return min(1.0, score)

    async def _evaluate_domain_familiarity(self, context: Dict) -> float:
        """Evaluate familiarity with the domain."""
        project_type = context.get("project_type", "custom")
        technologies = context.get("technologies", [])

        # Check for past projects of same type
        query = f"project type {project_type}"
        similar = await self.memory.search_memories(query, n_results=5)

        base_score = 0.5

        # Known project types get a boost
        known_types = ["todo_app", "api", "dashboard", "website", "cli"]
        if project_type in known_types:
            base_score += 0.2

        # Familiar technologies
        common_tech = ["react", "python", "typescript", "nextjs", "fastapi"]
        familiar_count = sum(1 for t in technologies if t in common_tech)
        base_score += familiar_count * 0.05

        # Past experience
        if similar:
            base_score += min(len(similar) * 0.05, 0.2)

        return min(1.0, base_score)

    def _generate_reasoning(self, factors: Dict[str, float], score: float) -> str:
        """Generate human-readable reasoning for confidence score."""
        parts = []

        parts.append(f"Overall confidence: {score:.0%}")

        # Highlight low factors
        low_factors = [(k, v) for k, v in factors.items() if v < 0.5]
        if low_factors:
            parts.append("\nAreas of uncertainty:")
            for factor, value in low_factors:
                factor_name = factor.replace("_", " ").title()
                parts.append(f"  - {factor_name}: {value:.0%}")

        # Highlight high factors
        high_factors = [(k, v) for k, v in factors.items() if v >= 0.7]
        if high_factors:
            parts.append("\nAreas of confidence:")
            for factor, value in high_factors:
                factor_name = factor.replace("_", " ").title()
                parts.append(f"  - {factor_name}: {value:.0%}")

        return "\n".join(parts)

    def _generate_question(
        self,
        decision_type: str,
        factors: Dict[str, float],
        context: Dict
    ) -> str:
        """Generate a clarification question."""
        # Find the lowest factor
        lowest_factor = min(factors.items(), key=lambda x: x[1])[0]

        questions = {
            "task_complexity": "This seems complex. Could you break it down into smaller pieces or clarify the scope?",
            "similar_past_success": "I haven't done something exactly like this before. Could you provide more details or examples?",
            "clear_requirements": "I'm not entirely sure what you need. Could you clarify the specific requirements?",
            "available_context": "I need more context to proceed confidently. Could you provide additional details or references?",
            "domain_familiarity": "This domain is somewhat unfamiliar. Could you point me to any documentation or examples?"
        }

        base_question = questions.get(
            lowest_factor,
            "Could you provide more details to help me understand this better?"
        )

        # Add specific unclear points if any
        unclear = context.get("unclear_points", [])
        if unclear:
            base_question += f"\n\nSpecifically, I'm unsure about: {unclear[0]}"

        return base_question

    async def record_decision(
        self,
        decision_type: str,
        options: List[str],
        chosen: str,
        confidence: float,
        context: Dict,
        reasoning: Optional[str] = None
    ) -> str:
        """Record a decision for later learning."""
        decision_id = await self.memory.record_decision(
            decision_type=decision_type,
            options=options,
            chosen=chosen,
            confidence=confidence,
            reasoning=reasoning
        )

        self._decision_history.append({
            "id": decision_id,
            "type": decision_type,
            "confidence": confidence,
            "context": context
        })

        return decision_id

    async def learn_from_outcome(
        self,
        decision_id: str,
        success: bool
    ) -> None:
        """Learn from a decision outcome."""
        await self.memory.update_decision_outcome(decision_id, success)

        # Find the decision in history
        decision = next(
            (d for d in self._decision_history if d["id"] == decision_id),
            None
        )

        if decision:
            confidence = decision["confidence"]

            # If we were confident but failed, reduce weights
            if confidence >= self.threshold and not success:
                logger.info(f"Learning from confident failure: {decision_id}")
                for factor in self.weights:
                    self._weight_adjustments[factor] = (
                        self._weight_adjustments.get(factor, 0) - self.learning_rate
                    )

            # If we were not confident but succeeded anyway, increase weights
            elif confidence < self.threshold and success:
                logger.info(f"Learning from uncertain success: {decision_id}")
                for factor in self.weights:
                    self._weight_adjustments[factor] = (
                        self._weight_adjustments.get(factor, 0) + self.learning_rate
                    )

    async def get_statistics(self) -> Dict:
        """Get confidence engine statistics."""
        return {
            "threshold": self.threshold,
            "weights": self.weights,
            "adjustments": self._weight_adjustments,
            "decisions_recorded": len(self._decision_history)
        }
