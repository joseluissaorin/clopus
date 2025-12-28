# =============================================================================
# CLOPUS v3 Configuration
# =============================================================================
"""
Configuration management for the orchestrator.
Loads from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml


class WorkerConfig(BaseModel):
    """Worker configuration."""
    count: int = 11  # 6 regular + 1 heartbeat + 1 verificator + 2 browser + 1 services
    roles: List[str] = [
        "coder", "tester", "reviewer", "researcher", "debugger", "designer",
        "heartbeat", "verificator", "browser-headless", "browser-chrome", "services"
    ]
    reserved_roles: List[str] = [
        "heartbeat", "verificator", "browser-headless", "browser-chrome", "services"
    ]  # Roles not assigned regular tasks
    poll_interval_ms: int = 500
    heartbeat_interval_s: int = 10
    task_timeout_s: int = 3600


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    sqlite_path: str = "/app/data/sqlite/clopus.db"
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_size: int = 10000


class ValidationConfig(BaseModel):
    """Validation pipeline configuration."""
    enabled_stages: List[str] = [
        "syntax", "lint", "build", "unit_tests",
        "integration_tests", "e2e_tests", "security", "review"
    ]
    strict_mode: bool = True
    allow_warnings: bool = True
    max_retries: int = 3
    timeout_per_stage_s: int = 300


class ConfidenceConfig(BaseModel):
    """Confidence engine configuration."""
    threshold: float = 0.4  # Lower threshold to proceed more autonomously
    weights: Dict[str, float] = {
        "task_complexity": 0.2,
        "similar_past_success": 0.25,
        "clear_requirements": 0.2,
        "available_context": 0.15,
        "domain_familiarity": 0.2
    }
    learning_rate: float = 0.1


class GitHubConfig(BaseModel):
    """GitHub integration configuration."""
    clopus_repo: str = ""
    auto_sync: bool = True
    sync_skills: bool = True
    sync_templates: bool = True
    sync_mcps: bool = True
    commit_prefix: str = "[CLOPUS]"


class ServicesConfig(BaseModel):
    """Services configuration."""
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "clopus"
    postgres_password: str = "clopus"
    postgres_db: str = "clopus"
    redis_host: str = "redis"
    redis_port: int = 6379
    minio_host: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"


class EmailConfig(BaseModel):
    """Email configuration."""
    provider: str = "smtp"  # smtp, resend
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""
    from_address: str = "clopus@localhost"


class InterfaceConfig(BaseModel):
    """Interface configuration."""
    cli_enabled: bool = True
    file_adapter_enabled: bool = True
    webhook_enabled: bool = False
    webhook_port: int = 8888
    objectives_dir: str = "/app/objectives"
    questions_dir: str = "/app/questions"
    answers_dir: str = "/app/answers"


class IntegrationTestingConfig(BaseModel):
    """Integration testing configuration."""
    enabled: bool = True
    start_services: bool = True
    timeout_seconds: int = 120
    take_screenshots: bool = True


class CompletionGateConfig(BaseModel):
    """Completion gate configuration."""
    require_all_validation_stages: bool = True
    require_integration_tests: bool = True
    require_e2e_tests: bool = True
    allowed_failed_tasks: int = 0


class HeartbeatConfig(BaseModel):
    """Heartbeat Agent (Completion Guardian) configuration."""
    enabled: bool = True
    interval_seconds: int = 300  # 5 minutes
    first_check_delay_seconds: int = 30
    use_claude_analysis: bool = True
    model: str = "claude-sonnet-4-20250514"
    integration_testing: IntegrationTestingConfig = IntegrationTestingConfig()
    completion_gate: CompletionGateConfig = CompletionGateConfig()


class Settings(BaseSettings):
    """Main settings loaded from environment."""

    # API Keys
    anthropic_api_key: str = ""
    github_token: str = ""

    # Auth
    auth_mode: str = "hybrid"  # api, login, hybrid

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Paths
    workspace_path: str = "/workspace"
    ipc_path: str = "/app/ipc"
    output_path: str = "/app/output"
    skills_path: str = "/app/skills"
    templates_path: str = "/app/templates"
    mcp_servers_path: str = "/app/mcp-servers"

    # Service connection settings (from docker-compose environment)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "clopus"
    postgres_password: str = "clopus"
    postgres_db: str = "clopus"
    redis_host: str = "redis"
    redis_port: int = 6379
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    minio_host: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    vnc_port: int = 6080

    # Component configs (loaded from config.yaml)
    # Using underscore prefix to avoid env var conflicts
    worker_config: WorkerConfig = WorkerConfig()
    memory_config: MemoryConfig = MemoryConfig()
    validation_config: ValidationConfig = ValidationConfig()
    confidence_config: ConfidenceConfig = ConfidenceConfig()
    github_config: GitHubConfig = GitHubConfig()
    services_config: ServicesConfig = ServicesConfig()
    email_config: EmailConfig = EmailConfig()
    interface_config: InterfaceConfig = InterfaceConfig()
    heartbeat_config: HeartbeatConfig = HeartbeatConfig()

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def load_config(config_path: Optional[str] = None) -> Settings:
    """Load configuration from environment and config file."""
    settings = Settings()

    # Load config.yaml if exists
    if config_path is None:
        config_path = os.environ.get("CLOPUS_CONFIG", "/app/config.yaml")

    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        if config_data:
            # Update component configs from file
            if "workers" in config_data:
                settings.worker_config = WorkerConfig(**config_data["workers"])
            if "memory" in config_data:
                settings.memory_config = MemoryConfig(**config_data["memory"])
            if "validation" in config_data:
                settings.validation_config = ValidationConfig(**config_data["validation"])
            if "confidence" in config_data:
                settings.confidence_config = ConfidenceConfig(**config_data["confidence"])
            if "github" in config_data:
                settings.github_config = GitHubConfig(**config_data["github"])
            if "services" in config_data:
                settings.services_config = ServicesConfig(**config_data["services"])
            if "email" in config_data:
                settings.email_config = EmailConfig(**config_data["email"])
            if "interface" in config_data:
                settings.interface_config = InterfaceConfig(**config_data["interface"])
            if "heartbeat" in config_data:
                heartbeat_data = config_data["heartbeat"]
                # Handle nested configs
                if "integration_testing" in heartbeat_data:
                    heartbeat_data["integration_testing"] = IntegrationTestingConfig(
                        **heartbeat_data["integration_testing"]
                    )
                if "completion_gate" in heartbeat_data:
                    heartbeat_data["completion_gate"] = CompletionGateConfig(
                        **heartbeat_data["completion_gate"]
                    )
                settings.heartbeat_config = HeartbeatConfig(**heartbeat_data)

    return settings


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings
