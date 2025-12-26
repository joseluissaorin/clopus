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

    # =========================================================================
    # OUTCOME TRACKING (Architecture: Decision Learning)
    # =========================================================================

    async def record_outcome(
        self,
        decision_id: str,
        outcome: Dict,
        success: bool
    ) -> None:
        """
        Record the outcome of a decision (Architecture: record_outcome).
        Alias for learn_from_outcome with additional metadata.
        """
        # Store detailed outcome
        await self.memory.log_activity(
            source="confidence_engine",
            action="outcome_recorded",
            details={
                "decision_id": decision_id,
                "success": success,
                "outcome": outcome
            }
        )

        # Learn from outcome
        await self.learn_from_outcome(decision_id, success)

        # Store in long-term memory for pattern recognition
        decision = next(
            (d for d in self._decision_history if d["id"] == decision_id),
            None
        )

        if decision:
            memory_content = f"Decision outcome: {decision['type']} - {'SUCCESS' if success else 'FAILURE'}"
            await self.memory.long_term.store(
                memory_type="decision",
                content=memory_content,
                metadata={
                    "decision_id": decision_id,
                    "decision_type": decision["type"],
                    "confidence": decision["confidence"],
                    "outcome": "success" if success else "failure",
                    "was_autonomous": decision["confidence"] >= self.threshold
                }
            )

    async def record_task_outcome(
        self,
        task_id: str,
        task_type: str,
        success: bool,
        validation_passed: bool,
        error: Optional[str] = None
    ) -> None:
        """Record task completion outcome for learning."""
        # Find related decision
        decision = next(
            (d for d in self._decision_history
             if d.get("context", {}).get("task_id") == task_id),
            None
        )

        if decision:
            await self.record_outcome(
                decision_id=decision["id"],
                outcome={
                    "task_id": task_id,
                    "validation_passed": validation_passed,
                    "error": error
                },
                success=success and validation_passed
            )
        else:
            # No decision recorded, but still learn from pattern
            pattern_key = f"task_type:{task_type}"

            if not success or not validation_passed:
                # Lower confidence for similar tasks in future
                self._weight_adjustments[pattern_key] = (
                    self._weight_adjustments.get(pattern_key, 0) - self.learning_rate
                )
                logger.info(f"Learned from failure pattern: {pattern_key}")
            else:
                # Increase confidence for similar tasks
                self._weight_adjustments[pattern_key] = (
                    self._weight_adjustments.get(pattern_key, 0) + self.learning_rate * 0.5
                )

    async def update_confidence_weights(self, decision: Dict) -> None:
        """
        Adjust confidence calculation based on outcomes.
        (Architecture: update_confidence_weights)
        """
        similar_decisions = await self.memory.long_term.search(
            query=f"decision {decision.get('type', '')}",
            n_results=10
        )

        if not similar_decisions:
            return

        # Calculate success rate for similar decisions
        successes = sum(
            1 for d in similar_decisions
            if d.metadata.get("outcome") == "success"
        )
        total = len(similar_decisions)

        if total < 3:
            return  # Not enough data

        success_rate = successes / total

        # Adjust weights based on success rate
        if success_rate < 0.5:
            # Lower confidence for this type of decision
            pattern = f"decision_type:{decision.get('type', 'unknown')}"
            self._weight_adjustments[pattern] = -0.1
            logger.info(f"Lowered confidence for pattern: {pattern} (success rate: {success_rate:.0%})")
        elif success_rate > 0.8:
            # Increase confidence for this type
            pattern = f"decision_type:{decision.get('type', 'unknown')}"
            self._weight_adjustments[pattern] = 0.1
            logger.info(f"Increased confidence for pattern: {pattern} (success rate: {success_rate:.0%})")

    async def learn_preference(
        self,
        context: Dict,
        user_choice: str
    ) -> None:
        """
        Learn from user correction/preference.
        (Architecture: learn_preference)
        """
        # Store user preference pattern
        await self.memory.long_term.store(
            memory_type="preference",
            content=f"User preferred: {user_choice}",
            metadata={
                "context_summary": str(context)[:500],
                "user_choice": user_choice,
                "learned_at": "now"
            }
        )

        # Reduce confidence for similar contexts where we suggested differently
        pattern_key = f"preference:{context.get('decision_type', 'unknown')}"
        self._weight_adjustments[pattern_key] = (
            self._weight_adjustments.get(pattern_key, 0) - self.learning_rate
        )

        logger.info(f"Learned user preference for {pattern_key}: {user_choice}")
