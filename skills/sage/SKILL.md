---
name: sage
description: 의정부 영의정. 임무 완수까지 자율 실행
alias: 영의정 (領議政)
model: opus
---

`command -v sage-orchestrator && sage-orchestrator "<task>" || python3 ~/sage-loop/src/sage_loop/cli/orchestrator.py "<task>"`

TODO_REQUIRED JSON → TodoWrite 호출 후:

**멈추지 말고 반복**: 역할 스킬 호출 → completed 마킹 → 다음 pending 호출 → 15단계 전부 완료까지 계속
