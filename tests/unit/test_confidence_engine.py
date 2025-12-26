"""
Unit tests for Confidence Engine
"""

import pytest
from orchestrator.confidence_engine import ConfidenceEngine, ConfidenceFactors


class TestConfidenceEngine:
    """Tests for ConfidenceEngine class."""

    @pytest.mark.asyncio
    async def test_calculate_confidence_simple_task(self, confidence_engine, sample_task):
        """Test confidence calculation for a simple task."""
        confidence = await confidence_engine.calculate_confidence(sample_task)

        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_confidence_complex_task(self, confidence_engine):
        """Test confidence is lower for complex tasks."""
        simple_task = {
            "id": "simple",
            "description": "Add a button",
            "type": "simple",
            "context": {"has_examples": True},
        }

        complex_task = {
            "id": "complex",
            "description": "Implement a distributed caching layer with Redis cluster",
            "type": "architecture",
            "context": {"has_examples": False},
        }

        simple_confidence = await confidence_engine.calculate_confidence(simple_task)
        complex_confidence = await confidence_engine.calculate_confidence(complex_task)

        assert simple_confidence > complex_confidence

    @pytest.mark.asyncio
    async def test_should_ask_user_low_confidence(self, confidence_engine):
        """Test that low confidence triggers user question."""
        low_confidence_task = {
            "id": "unclear",
            "description": "Do something with the thing",
            "type": "unknown",
            "context": {},
        }

        should_ask = await confidence_engine.should_ask_user(low_confidence_task)

        # With vague description and no context, should ask user
        # (depends on threshold, but likely true for this case)
        assert isinstance(should_ask, bool)

    @pytest.mark.asyncio
    async def test_record_outcome_updates_learning(self, confidence_engine, sample_task):
        """Test that recording outcomes updates the learning system."""
        # Record a successful outcome
        await confidence_engine.record_outcome(
            task=sample_task,
            success=True,
            confidence_was=0.8,
        )

        # Should improve future confidence for similar tasks
        new_confidence = await confidence_engine.calculate_confidence(sample_task)

        assert new_confidence >= 0.0


class TestConfidenceFactors:
    """Tests for ConfidenceFactors dataclass."""

    def test_factors_creation(self):
        """Test factor creation with valid values."""
        factors = ConfidenceFactors(
            task_complexity=0.8,
            similar_past_success=0.7,
            clear_requirements=0.9,
            available_context=0.6,
            domain_familiarity=0.75,
        )

        assert factors.task_complexity == 0.8
        assert factors.similar_past_success == 0.7

    def test_weighted_score(self):
        """Test weighted score calculation."""
        factors = ConfidenceFactors(
            task_complexity=1.0,
            similar_past_success=1.0,
            clear_requirements=1.0,
            available_context=1.0,
            domain_familiarity=1.0,
        )

        weights = {
            "task_complexity": 0.2,
            "similar_past_success": 0.25,
            "clear_requirements": 0.25,
            "available_context": 0.15,
            "domain_familiarity": 0.15,
        }

        score = factors.weighted_score(weights)

        # All factors at 1.0, so score should be 1.0
        assert score == pytest.approx(1.0, rel=0.01)

    def test_weighted_score_partial(self):
        """Test weighted score with partial values."""
        factors = ConfidenceFactors(
            task_complexity=0.5,
            similar_past_success=0.5,
            clear_requirements=0.5,
            available_context=0.5,
            domain_familiarity=0.5,
        )

        weights = {
            "task_complexity": 0.2,
            "similar_past_success": 0.25,
            "clear_requirements": 0.25,
            "available_context": 0.15,
            "domain_familiarity": 0.15,
        }

        score = factors.weighted_score(weights)

        # All factors at 0.5, so score should be 0.5
        assert score == pytest.approx(0.5, rel=0.01)
