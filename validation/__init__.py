# =============================================================================
# CLOPUS v3 Validation System
# =============================================================================
"""
8-stage validation pipeline ensuring code quality and correctness.

Stages:
1. Syntax - Basic syntax checking
2. Lint - ESLint, Pylint, etc.
3. Build - Compilation/bundling
4. Unit Tests - Unit test execution
5. Integration Tests - Integration testing
6. E2E Tests - End-to-end with Playwright
7. Security - Security scanning
8. Review - Code review by reviewer worker
"""

from .pipeline import ValidationPipeline, ValidationResult, ValidationStage

__all__ = ["ValidationPipeline", "ValidationResult", "ValidationStage"]
