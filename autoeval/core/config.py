"""Configuration settings for AutoEval Sandbox."""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application configuration with environment variable overrides."""

    app_name: str = "AutoEval Sandbox"
    app_version: str = "1.0.0"
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1"))

    # Redis & Celery broker
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    celery_result_backend: str = field(
        default_factory=lambda: os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    )

    # Sandbox Isolation & Cgroup Constraints
    docker_image: str = field(default_factory=lambda: os.getenv("DOCKER_IMAGE", "autoeval-sandbox:latest"))
    memory_limit_mb: int = field(default_factory=lambda: int(os.getenv("MEMORY_LIMIT_MB", "256")))
    cpu_quota_vcpu: float = field(default_factory=lambda: float(os.getenv("CPU_QUOTA_VCPU", "0.5")))
    tmpfs_size_mb: int = field(default_factory=lambda: int(os.getenv("TMPFS_SIZE_MB", "32")))
    default_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("DEFAULT_TIMEOUT_SECONDS", "10.0"))
    )
    max_code_size_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_CODE_SIZE_BYTES", "65536"))
    )

    # Execution Mode: 'auto', 'docker', or 'mock'
    sandbox_mode: str = field(default_factory=lambda: os.getenv("SANDBOX_MODE", "auto"))

    # Security Settings
    ast_strict_mode: bool = field(
        default_factory=lambda: os.getenv("AST_STRICT_MODE", "true").lower() in ("true", "1")
    )
    enable_bandit: bool = field(
        default_factory=lambda: os.getenv("ENABLE_BANDIT", "true").lower() in ("true", "1")
    )


settings = Settings()
