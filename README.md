# Sage Loop

A 17-phase autonomous agent orchestration system for Claude Code, inspired by the Korean Joseon Dynasty's Uijeongbu (의정부) deliberation system.

## Overview

Sage Loop implements a hierarchical decision-making chain where each role has specific responsibilities, enabling thorough analysis, critique, and execution of complex tasks.

The Sage (영의정) appears **three times**, following the historical Uijeongbu deliberation flow:
1. **Phase 1**: Accept petition and initiate review ("검토하라")
2. **Phase 10**: Authorize execution after deliberation ("시행하라")
3. **Phase 14**: Final approval after validation ("완료 확인")

```
Sage(접수) → Ideator → Analyst → Critic → Censor → Academy → Architect
    → LeftState → RightState → Sage(허가) → Executor
    → Inspector → Validator → Sage(결재) → Historian → Reflector → Improver
```

## Roles (17 Phases)

| Phase | Role | Korean | Function |
|-------|------|--------|----------|
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
