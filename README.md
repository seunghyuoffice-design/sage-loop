# Sage Loop

A 15-phase autonomous agent orchestration system for Claude Code, inspired by the Korean Joseon Dynasty's Uijeongbu (의정부) deliberation system.

## Overview

Sage Loop implements a hierarchical decision-making chain where each role has specific responsibilities, enabling thorough analysis, critique, and execution of complex tasks.

```
Ideator → Analyst → Critic → Censor → Academy → Architect
    → LeftState → RightState → Sage → Executor
    → Inspector → Validator → Historian → Reflector → Improver
```

## Roles (15 Phases)

| Phase | Role | Korean | Function |
|-------|------|--------|----------|
| 1 | Ideator | 현인 | Generate 50+ ideas |
| 2 | Analyst | 선지자 | Filter to 5 best ideas |
| 3 | Critic | 비조 | Identify risks (no solutions) |
| 4 | Censor | 파수꾼 | Block rule violations |
| 5 | Academy | 대제학 | Provide academic guidance |
| 6 | Architect | 장인 | Design implementation |
| 7 | LeftState | 좌의정 | Internal policy review |
| 8 | RightState | 우의정 | Technical/practical review |
| 9 | Sage | 영의정 | Final approval authority |
| 10 | Executor | 실행관 | Implement the design |
| 11 | Inspector | 감찰관 | Inspect execution |
| 12 | Validator | 검증관 | Final quality gate |
| 13 | Historian | 역사관 | Record decisions |
| 14 | Reflector | 회고관 | Gather feedback |
| 15 | Improver | 개선관 | Propose improvements |

## Chain Types

- **FULL**: All 15 phases (complex tasks)
- **QUICK**: Critic → Architect → Executor → Validator → Historian
- **REVIEW**: Critic → Validator
- **DESIGN**: Ideator → Analyst → Critic → Architect

## Installation

### As Claude Code Skills

```bash
# Copy skills to your Claude Code project
cp -r skills/* .claude/skills/

# Copy hooks
cp hooks/* .claude/hooks/
chmod +x .claude/hooks/*.sh
```

### As Python Package

```bash
pip install -e .
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
from sage.engine.sage_commander import SageCommander
from sage.schemas import ChainType

commander = SageCommander()
result = await commander.execute_chain(
    session_id="my-session",
    user_request="Implement feature X",
    chain_type=ChainType.FULL
)
```

## Architecture

```
sage-loop/
├── skills/           # Role definitions (markdown)
├── hooks/            # Claude Code hooks
│   ├── stop-hook.sh
│   ├── completion_detector.py
│   ├── circuit_breaker_check.py
│   └── sage_state_manager.py
├── src/sage/
│   ├── engine/       # Core orchestration
│   ├── services/     # State management
│   ├── feedback/     # Feedback loop
│   └── schemas.py    # Data models
└── docs/
```

## Key Features

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

---

*Built with Claude Code*
