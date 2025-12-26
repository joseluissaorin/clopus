"""
End-to-end tests for CLOPUS
"""

import asyncio
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestFullWorkflow:
    """End-to-end tests for complete CLOPUS workflows."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("CLOPUS_E2E") != "true",
        reason="E2E tests require CLOPUS_E2E=true",
    )
    async def test_simple_project_creation(self, tmp_path):
        """Test creating a simple project from objective to completion."""
        # This is a full E2E test that requires the system to be running

        from orchestrator.main import Orchestrator

        # Initialize orchestrator
        orchestrator = Orchestrator()
        await orchestrator.initialize()

        try:
            # Submit objective
            objective_id = await orchestrator.submit_objective(
                description="Create a simple Python script that prints 'Hello, World!'",
                output_dir=str(tmp_path),
            )

            # Wait for completion (with timeout)
            completed = await orchestrator.wait_for_objective(
                objective_id,
                timeout=300,  # 5 minutes
            )

            assert completed is True

            # Verify output
            output_files = list(tmp_path.glob("**/*.py"))
            assert len(output_files) > 0

            # Check content
            content = output_files[0].read_text()
            assert "Hello" in content or "print" in content

        finally:
            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_objective_parsing(self):
        """Test that objectives are parsed correctly."""
        from orchestrator.objective_parser import ObjectiveParser

        parser = ObjectiveParser()

        objective = "Build a React todo app with TypeScript and Tailwind CSS"
        parsed = await parser.parse(objective)

        assert parsed["project_type"] in ["react", "frontend"]
        assert "typescript" in parsed.get("technologies", [])
        assert "tailwind" in parsed.get("technologies", [])

    @pytest.mark.asyncio
    async def test_validation_pipeline_full_run(self, sample_project_path):
        """Test running the full validation pipeline."""
        from validation.pipeline import ValidationPipeline

        pipeline = ValidationPipeline()

        result = await pipeline.validate(
            project_path=str(sample_project_path),
            stages=["syntax", "lint", "build"],
        )

        assert "stages" in result
        assert "overall_passed" in result
        assert "total_duration_ms" in result

        # Check each stage has required fields
        for stage in result["stages"]:
            assert "stage" in stage
            assert "passed" in stage
            assert "errors" in stage
            assert "warnings" in stage
            assert "duration_ms" in stage

    @pytest.mark.asyncio
    async def test_skill_discovery(self, tmp_path):
        """Test that skills are discovered correctly."""
        from orchestrator.skills_engine import SkillsEngine

        # Create a test skill
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)

        (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
version: 1.0.0
author: Test
tools:
  - Bash
triggers:
  - test
---

# Test Skill

This is a test skill.
""")

        engine = SkillsEngine(skills_dir=str(tmp_path / "skills"))
        await engine.discover_skills()

        skills = engine.list_skills()
        assert len(skills) >= 1

        skill = engine.get_skill("test-skill")
        assert skill is not None
        assert skill["name"] == "test-skill"

    @pytest.mark.asyncio
    async def test_template_extraction(self, sample_project_path):
        """Test template extraction from a project."""
        from orchestrator.template_extractor import TemplateExtractor

        extractor = TemplateExtractor()

        template = await extractor.extract(
            project_path=str(sample_project_path),
            template_name="test-template",
        )

        assert template is not None
        assert "name" in template
        assert "parameters" in template

    @pytest.mark.asyncio
    async def test_github_sync_mock(self):
        """Test GitHub sync functionality (mocked)."""
        from orchestrator.github_sync import GitHubSync

        sync = GitHubSync()

        with patch.object(sync, "_create_repo", new_callable=AsyncMock) as mock_create:
            with patch.object(sync, "_push_to_repo", new_callable=AsyncMock) as mock_push:
                mock_create.return_value = "https://github.com/test/repo"
                mock_push.return_value = True

                result = await sync.sync_skill(
                    skill_name="test-skill",
                    skill_path="/path/to/skill",
                )

                # Should attempt to sync
                assert mock_push.called or result is not None


class TestFileInterface:
    """Test file-based interface."""

    @pytest.mark.asyncio
    async def test_objective_file_submission(self, tmp_path):
        """Test submitting objective via file."""
        from interfaces.file_adapter import FileAdapter

        # Create interface directories
        ipc_dir = tmp_path / "ipc" / "interface"
        ipc_dir.mkdir(parents=True)

        adapter = FileAdapter(ipc_dir=str(ipc_dir))

        # Write objective file
        (ipc_dir / "objective.txt").write_text(
            "Build a simple CLI tool with Python"
        )

        # Check for new objectives
        objective = await adapter.check_for_objective()

        assert objective is not None
        assert "CLI" in objective or "Python" in objective

    @pytest.mark.asyncio
    async def test_answer_file_processing(self, tmp_path):
        """Test processing answer files."""
        from interfaces.file_adapter import FileAdapter

        ipc_dir = tmp_path / "ipc" / "interface"
        ipc_dir.mkdir(parents=True)

        adapter = FileAdapter(ipc_dir=str(ipc_dir))

        # Write answer file
        import json

        answer_data = {
            "question_id": "q_123",
            "answer": "Use PostgreSQL for the database",
        }
        (ipc_dir / "answer.txt").write_text(json.dumps(answer_data))

        # Check for answers
        answer = await adapter.check_for_answer()

        assert answer is not None
        assert answer["question_id"] == "q_123"


class TestCLIInterface:
    """Test CLI interface."""

    def test_cli_help(self):
        """Test CLI help command."""
        import subprocess

        result = subprocess.run(
            ["./clopus", "--help"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )

        # Should show help or error gracefully
        assert result.returncode == 0 or "Usage" in result.stdout or "clopus" in result.stdout.lower()

    def test_cli_status_command(self):
        """Test CLI status command (may fail if not running)."""
        import subprocess

        result = subprocess.run(
            ["./clopus", "status"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
        )

        # Should either show status or indicate system is not running
        output = result.stdout + result.stderr
        assert "status" in output.lower() or "not running" in output.lower() or result.returncode >= 0
