---
name: sage
description: 의정부 영의정. 임무 완수까지 자율 실행
alias: 영의정 (領議政)
model: opus
---

`command -v sage-orchestrator && sage-orchestrator "<task>" || python3 ~/sage-loop/src/sage_loop/cli/orchestrator.py "<task>"`

1. `TODO_REQUIRED:` JSON → TodoWrite 호출
2. NEXT 역할 스킬 호출 (Skill 도구로 `/역할명`)
3. 완료 시 TodoWrite로 completed 마킹 → 다음 pending 역할 실행
4. 모든 역할 완료까지 반복 (세션 불필요, TodoWrite가 상태)
