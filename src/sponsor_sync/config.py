"""Application configuration models and loaders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class RulesConfig(BaseModel):
    """Deterministic filtering rules loaded from disk."""

    allowed_titles: list[str] = Field(min_length=1)
    salary_threshold_gbp: int = Field(gt=0)
    exclusion_keywords: list[str] = Field(default_factory=list)
    company_blacklist: list[str] = Field(default_factory=list)


class AppConfig(BaseSettings):
    """Strongly typed app configuration loaded from env and JSON overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("SPONSORSYNC_ENVIRONMENT", "ENVIRONMENT"),
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SPONSORSYNC_ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY",
        ),
    )
    reed_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SPONSORSYNC_REED_API_KEY",
            "REED_API_KEY",
        ),
    )
    database_url: str = Field(
        default="sqlite:///./sponsorsync.db",
        validation_alias=AliasChoices("SPONSORSYNC_DATABASE_URL", "DATABASE_URL"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        validation_alias=AliasChoices("SPONSORSYNC_LOG_LEVEL", "LOG_LEVEL"),
    )
    config_dir: Path = Field(
        default=Path("configs"),
        validation_alias=AliasChoices("SPONSORSYNC_CONFIG_DIR", "CONFIG_DIR"),
    )
    rules_file_name: str = Field(
        default="rules.default.json",
        validation_alias=AliasChoices("SPONSORSYNC_RULES_FILE_NAME", "RULES_FILE_NAME"),
    )
    claude_max_tokens_per_call: int = Field(
        default=800,
        gt=0,
        le=4096,
        validation_alias=AliasChoices(
            "SPONSORSYNC_CLAUDE_MAX_TOKENS_PER_CALL",
            "CLAUDE_MAX_TOKENS_PER_CALL",
        ),
    )
    claude_run_budget_usd: float = Field(
        default=1.0,
        gt=0,
        validation_alias=AliasChoices(
            "SPONSORSYNC_CLAUDE_RUN_BUDGET_USD", "CLAUDE_RUN_BUDGET_USD"
        ),
    )
    claude_input_cost_per_million_tokens: float = Field(
        default=3.0,
        ge=0,
        validation_alias=AliasChoices(
            "SPONSORSYNC_CLAUDE_INPUT_COST_PER_MILLION_TOKENS",
            "CLAUDE_INPUT_COST_PER_MILLION_TOKENS",
        ),
    )
    claude_output_cost_per_million_tokens: float = Field(
        default=15.0,
        ge=0,
        validation_alias=AliasChoices(
            "SPONSORSYNC_CLAUDE_OUTPUT_COST_PER_MILLION_TOKENS",
            "CLAUDE_OUTPUT_COST_PER_MILLION_TOKENS",
        ),
    )

    @property
    def environment_override_path(self) -> Path:
        return self.config_dir / "environments" / f"{self.environment}.json"

    @property
    def rules_path(self) -> Path:
        return self.config_dir / self.rules_file_name

    @classmethod
    def load(cls) -> AppConfig:
        """Load configuration with optional environment-specific override file."""
        base_config = cls()
        override_path = base_config.environment_override_path
        if not override_path.exists():
            return base_config

        override_data = json.loads(override_path.read_text(encoding="utf-8"))
        try:
            return cls.model_validate({**base_config.model_dump(), **override_data})
        except ValidationError as exc:  # pragma: no cover - wrapped for clearer message
            raise ValueError(
                f"Invalid environment override file: {override_path}"
            ) from exc

    def load_rules_config(self) -> RulesConfig:
        """Load deterministic filtering rules from JSON file."""
        if not self.rules_path.exists():
            raise ValueError(f"Rules config file not found: {self.rules_path}")

        raw_rules = json.loads(self.rules_path.read_text(encoding="utf-8"))
        try:
            return RulesConfig.model_validate(raw_rules)
        except ValidationError as exc:  # pragma: no cover - wrapped for clearer message
            raise ValueError(f"Invalid rules config file: {self.rules_path}") from exc
