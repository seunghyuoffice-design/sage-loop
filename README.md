# Sage Loop

A 17-phase autonomous agent orchestration system, inspired by the Korean Joseon Dynasty's Uijeongbu (의정부) deliberation system.

## Overview

Sage Loop implements a hierarchical decision-making chain where each role has specific responsibilities, enabling thorough analysis, critique, and execution of complex tasks.

The Sage (영의정) appears **three times**, following the historical Uijeongbu deliberation flow:

1. **Phase 1**: Accept petition and initiate review ("검토하라")
2. **Phase 10**: Authorize execution after deliberation ("시행하라")
3. **Phase 14**: Final approval after validation ("완료 확인")

```text
Sage(접수) → Ideator → Analyst → Critic → Censor → Academy → Architect
    → LeftState → RightState → Sage(허가) → Executor
    → Inspector → Validator → Sage(결재) → Historian → Reflector → Improver
```

## Roles (17 Phases)

| Phase | Role | Korean | Function |
| ----- | ---- | ------ | -------- |
| 1 | **Sage** | 영의정 | **Accept petition (1st)** - "검토하라" |
| 2 | Ideator | 현인 | Generate 50+ ideas |
| 3 | Analyst | 선지자 | Filter to 5 best ideas |
| 4 | Critic | 비조 | Identify risks (no solutions) |
| 5 | Censor | 파수꾼 | Block rule violations |
| 6 | Academy | 대제학 | Provide academic guidance |
| 7 | Architect | 장인 | Design implementation |
| 8 | LeftState | 좌의정 | Internal policy review (이조/호조/예조) |
| 9 | RightState | 우의정 | Technical/practical review (병조/형조/공조) |
| 10 | **Sage** | 영의정 | **Execution authorization (2nd)** - "시행하라" |
| 11 | Executor | 실행관 | Implement the design |
| 12 | Inspector | 감찰관 | Inspect execution |
| 13 | Validator | 검증관 | Quality gate |
| 14 | **Sage** | 영의정 | **Final approval (3rd)** - "완료 확인" |
| 15 | Historian | 역사관 | Record decisions |
| 16 | Reflector | 회고관 | Gather feedback |
| 17 | Improver | 개선관 | Propose improvements |

## Chain Types

- **FULL**: All 17 phases (complex tasks)
- **QUICK**: Critic → Architect → Executor → Validator → Historian
- **REVIEW**: Critic → Validator
- **DESIGN**: Ideator → Analyst → Critic → Architect

## Installation

### Quick Start (Platform-Specific)

```bash
# Clone the repo
git clone https://github.com/seunghyuoffice-design/sage-loop.git
cd sage-loop

# Apply overlay for your platform
python3 scripts/apply_overlay.py claude   # For Claude Code
python3 scripts/apply_overlay.py codex    # For OpenAI Codex

# Copy hooks (Claude Code only)
cp hooks/* ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
```

### Manual Installation (Claude Code)

```bash
# Copy skills to your Claude Code project
cp -r skills/* ~/.claude/skills/

# Copy hooks
cp hooks/* ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
```

### As Python Package

```bash
pip install -e .
```

## Cross-Platform Support

sage-loop is platform-agnostic at its core. Skills are defined without model specifications, allowing you to run them on any LLM platform.

### Overlay System

Platform-specific configurations are managed through **overlays**:

```text
overlays/
├── claude/
│   └── model_map.yaml   # Claude models + ultrathink
└── codex/
    └── model_map.yaml   # Codex models + reasoning_effort
```

### Model Mapping

| Role Type | Claude | Codex |
| --------- | ------ | ----- |
| Supervision (sage, critic, censor) | opus + ultrathink | gpt-5.2 + reasoning:high |
| Implementation (executor, architect) | sonnet | gpt-5.2-codex |
| Generation (ideator, analyst) | haiku | gpt-5.1-codex-mini |

### Custom Overlays

Create your own overlay for other platforms:

```yaml
# overlays/my-platform/model_map.yaml
platform: my-platform
skills_path: ~/.my-platform/skills/

models:
  sage: { model: my-best-model, thinking: extended }
  ideator: { model: my-fast-model }
```

## Usage

### With Claude Code

```bash
# Invoke Sage Loop
/sage "Implement user authentication"

# Use specific chain
/sage --chain quick "Fix the login bug"
```

### Programmatic Usage

```python
from sage_loop.engine.sage_commander import SageCommander
from sage_loop.schemas import ChainType

commander = SageCommander()
result = await commander.execute_chain(
    session_id="my-session",
    user_request="Implement feature X",
    chain_type=ChainType.FULL
)
```

## Architecture

```text
sage-loop/
├── skills/           # Role definitions (platform-agnostic)
│   ├── sage/         # Orchestrator skill
│   ├── ideator.md
│   ├── critic.md
│   └── ...
├── overlays/         # Platform-specific configurations
│   ├── claude/       # Claude Code overlay
│   └── codex/        # OpenAI Codex overlay
├── scripts/
│   └── apply_overlay.py
├── hooks/            # Claude Code hooks
├── src/sage_loop/
│   ├── engine/       # Core orchestration
│   ├── cli/          # CLI tools
│   ├── hooks/        # Phase hooks
│   └── schemas.py    # Data models
└── pyproject.toml
```

## Key Features

- **Platform Agnostic**: Core skills work on any LLM platform
- **Overlay System**: Platform-specific model/thinking configuration
- **Context Isolation**: Each role runs in isolated context via Task tool
- **Branching**: Dynamic branching based on role outputs
- **Circuit Breaker**: Prevents infinite loops
- **Feedback Loop**: Roles can request re-evaluation
- **State Persistence**: Redis-backed session state

## Environment Variables

```bash
SAGE_REDIS_HOST=localhost
SAGE_REDIS_PORT=6380
SAGE_MAX_LOOPS=50
SAGE_SESSION_TIMEOUT=3600
SAGE_DEBUG=0
```

## Historical Inspiration

The system draws from Korea's Joseon Dynasty (1392-1897) governance:

- **영의정 (Sage)**: Chief State Councilor - final authority
- **좌의정 (LeftState)**: Left State Councilor - internal affairs
- **우의정 (RightState)**: Right State Councilor - external/practical affairs
- **육조 (Six Ministries)**: Specialized departments under the councilors

## License

MIT License

## Contributing

Contributions welcome! Please read our contributing guidelines.
