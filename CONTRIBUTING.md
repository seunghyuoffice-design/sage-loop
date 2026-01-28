# Contributing to Sage Loop

Thank you for your interest in contributing to Sage Loop!

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (platform, Python version)

### Suggesting Features

1. Open an issue with `[Feature]` prefix
2. Describe the use case
3. Explain how it fits the 14-phase model

### Code Contributions

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

## Development Setup

```bash
git clone https://github.com/seunghyuoffice-design/sage-loop.git
cd sage-loop
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Code Standards

### Python

- Python 3.10+
- Type hints required for public functions
- Docstrings for all public APIs
- Run `ruff check` before committing

### Skill Files

Skills follow the L1-L3 specification:

| Level | Structure | Use Case |
|-------|-----------|----------|
| L1 | Single `.md` file | Simple roles |
| L2 | Directory with `SKILL.md` | Complex roles |
| L3 | L2 + `scripts/` folder | Roles with Python helpers |

### Commit Messages

```
type(scope): description

Types: feat, fix, docs, refactor, test, chore
```

Examples:
```
feat(skills): add new ministry role
fix(engine): resolve parallel execution deadlock
docs(readme): add Korean translation
```

## Adding New Roles

### 1. Create skill file

```markdown
---
name: your-role
description: What this role does
model: haiku|sonnet|opus
---

# Role instructions here
```

### 2. Register in orchestrator

Add to `skills/yeong-ui-jeong/reference.md`

### 3. Add overlay configurations

Add model mappings in `overlays/*/models.yaml`

### 4. Write tests

Add tests in `tests/skills/test_your_role.py`

## Adding Platform Support

1. Create overlay directory: `overlays/your-platform/`
2. Add configuration files:
   - `models.yaml` - Model mappings
   - `settings.yaml` - Platform-specific settings
3. Update `install.sh` for one-line install
4. Document in README

## Testing

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_engine.py

# Run with coverage
make coverage
```

## Documentation

- English: `README.en.md`
- Korean: `README.md`
- Examples: `examples/`

Update both README files for user-facing changes.

## Questions?

- Open an issue with `[Question]` prefix
- Check existing discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

*Thank you for making Sage Loop better!*
