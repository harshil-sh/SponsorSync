import json

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("pydantic_settings")

from sponsor_sync.config import AppConfig


def test_app_config_loads_defaults_and_rules() -> None:
    config = AppConfig.load()

    assert config.environment == "development"
    assert config.log_level == "DEBUG"
    assert config.claude_max_tokens_per_call == 800
    assert config.claude_run_budget_usd == 1.0

    rules = config.load_rules_config()
    assert rules.salary_threshold_gbp == 45000
    assert "tech lead" in rules.allowed_titles


def test_app_config_applies_environment_specific_override(
    tmp_path, monkeypatch
) -> None:
    config_dir = tmp_path / "configs"
    environment_dir = config_dir / "environments"
    environment_dir.mkdir(parents=True)

    (config_dir / "rules.default.json").write_text(
        json.dumps(
            {
                "allowed_titles": ["principal engineer"],
                "salary_threshold_gbp": 60000,
                "exclusion_keywords": [],
                "company_blacklist": [],
            }
        ),
        encoding="utf-8",
    )
    (environment_dir / "test.json").write_text(
        json.dumps({"log_level": "ERROR", "database_url": "sqlite:///./test.db"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("SPONSORSYNC_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("SPONSORSYNC_ENVIRONMENT", "test")

    config = AppConfig.load()

    assert config.log_level == "ERROR"
    assert config.database_url == "sqlite:///./test.db"
    assert config.load_rules_config().salary_threshold_gbp == 60000


def test_app_config_raises_clear_error_for_invalid_override(
    tmp_path, monkeypatch
) -> None:
    config_dir = tmp_path / "configs"
    environment_dir = config_dir / "environments"
    environment_dir.mkdir(parents=True)

    (config_dir / "rules.default.json").write_text(
        json.dumps(
            {
                "allowed_titles": ["principal engineer"],
                "salary_threshold_gbp": 60000,
                "exclusion_keywords": [],
                "company_blacklist": [],
            }
        ),
        encoding="utf-8",
    )
    (environment_dir / "production.json").write_text(
        json.dumps({"log_level": "VERBOSE"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("SPONSORSYNC_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("SPONSORSYNC_ENVIRONMENT", "production")

    with pytest.raises(ValueError, match="Invalid environment override file"):
        AppConfig.load()


def test_rules_config_validation_has_clear_error(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir(parents=True)

    (config_dir / "rules.default.json").write_text(
        json.dumps(
            {
                "allowed_titles": ["principal engineer"],
                "salary_threshold_gbp": -1,
                "exclusion_keywords": [],
                "company_blacklist": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SPONSORSYNC_CONFIG_DIR", str(config_dir))

    with pytest.raises(ValueError, match="Invalid rules config file"):
        AppConfig().load_rules_config()


def test_app_config_rejects_invalid_claude_budget(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_RUN_BUDGET_USD", "0")

    with pytest.raises(ValueError):
        AppConfig.load()
