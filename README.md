# SponsorSync

SponsorSync is a Python project for ingesting candidate CV data and finding high-fit UK permanent roles.

## Security policy (secrets)

- **Never commit secrets** (API keys, tokens, passwords, private keys, credential files).
- Store local secrets in `.env` (or other local-only secret stores) and keep them out of version control.
- Use non-sensitive placeholders in `.env.example` for required configuration values.
- If a secret is committed by mistake, rotate it immediately and remove it from git history.

## Development

Install dev dependencies:

```bash
pip install -e .[dev]
```

Run checks:

```bash
ruff check .
pytest
```
