from pathlib import Path

REQUIRED_GITIGNORE_ENTRIES = {
    ".env",
    ".env.*",
    "!.env.example",
    "credentials/",
    "secrets/",
    "exports/",
}


def test_readme_has_secrets_policy() -> None:
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    assert "never commit secrets" in readme
    assert "api keys" in readme


def test_gitignore_includes_sensitive_and_exported_data_rules() -> None:
    entries = {
        line.strip()
        for line in Path(".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert REQUIRED_GITIGNORE_ENTRIES.issubset(entries)


def test_ci_includes_secret_scan_step() -> None:
    ci_workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "gitleaks/gitleaks-action@v2" in ci_workflow
