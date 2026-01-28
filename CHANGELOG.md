# Changelog

All notable changes to Sage Loop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2026-01-28

### Added
- **Google Antigravity Support**: Full 14-phase native workflow
  - Model mapping: opus→gemini-3-pro-high, sonnet→gemini-3-pro-low, haiku→gemini-3-flash
  - Browser Subagent integration for Academy (홍문관) research phase
  - Task Groups support for parallel execution
- 77 skills synced to Antigravity global_skills

### Fixed
- SKILL.md frontmatter delimiter (------ → ---)
- 8 skills now properly sync: architect, executor, inspector, validator, reflector, improver, analyst, ideator

## [1.3.0] - 2026-01-28

### Added
- **English README** (`README.en.md`) for global audience
- **CONTRIBUTING.md** with contribution guidelines
- **examples/README.md** with usage walkthroughs
- GitHub badges (version, license, Python, platforms)
- Language switcher between Korean and English docs
- Lint scripts for AI/human code review (`lint_scripts.py`)
- Dokseol (harsh criticism) injection across all phases
- `allowed-tools` support for all 90+ skills

### Changed
- Unified version numbers across all files (pyproject.toml, __init__.py, README)
- Renamed 삼사 skills to match 14-phase system
- Enhanced README visualization with ASCII diagrams

### Fixed
- Python script issues in yeong-ui-jeong L3 scripts
- Linter warnings and code quality issues

## [1.2.1] - 2026-01-26

### Added
- Multi-platform support (Claude, Gemini, Codex, OpenCode, VSCode, Antigravity)
- One-click installation script (`install.sh`)
- Codex hooks system for automated workflows
- `--chain` CLI option for explicit chain selection

### Changed
- Renamed `sage` skill to `yeong-ui-jeong` (영의정)
- Improved orchestrator logic

### Fixed
- Exit conditions for validator FAIL in QUICK/REVIEW chains
- Redis session serialization (None/list/bool types)
- Bytes decoding in role output methods
- String analysis field handling in `from_dict`

## [1.2.0] - 2026-01-24

### Changed
- Removed hardcoded paths for portability
- Improved code quality and maintainability

### Fixed
- Path-related bugs affecting cross-environment usage

## [1.1.0] - 2026-01-22

### Added
- L1-L3 skill specification system
- 6조 체계 (Six Ministries) parallel execution
- 삼사 (Three Offices) parallel review
- Redis state management

### Changed
- Migrated from 16-phase to 14-phase system
- Optimized parallel execution performance

## [1.0.0] - 2026-01-20

### Added
- Initial release of Sage Loop
- 14-phase orchestration engine
- Joseon Dynasty governance-inspired role system
- 5 preset chains: FULL, QUICK, REVIEW, DESIGN, RESEARCH
- Basic skill system with 40+ roles
- Claude Code integration

---

## Version Naming Convention

- **Major (X.0.0)**: Breaking changes to API or phase structure
- **Minor (0.X.0)**: New features, new skills, new platforms
- **Patch (0.0.X)**: Bug fixes, documentation updates

## Links

- [GitHub Repository](https://github.com/seunghyuoffice-design/sage-loop)
- [PyPI Package](https://pypi.org/project/sage-loop/)
