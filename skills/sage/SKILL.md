---
name: sage
description: 의정부 영의정. 17단계 체인을 자율 실행하는 오케스트레이터
alias: 영의정 (領議政)
---

## 1. 체인 초기화
```bash
python3 ~/sage-loop/src/sage_loop/cli/orchestrator.py "ARGUMENTS"
```

출력을 읽고:
- `CHAIN:` → 선택된 체인
- `NEXT:` → 첫 번째 역할
- `TODO_REQUIRED:` → TodoWrite JSON

## 2. TodoWrite 호출
TODO_REQUIRED의 JSON으로 TodoWrite 도구 호출

## 3. 역할 루프 (멈추지 말 것!)

**매 역할마다**:

### 3.1 역할 스킬 호출
```
/[역할명] ARGUMENTS
```
예: `/ideator ARGUMENTS`, `/analyst ARGUMENTS`, `/critic ARGUMENTS`

### 3.2 역할 완료 보고
```bash
python3 ~/sage-loop/src/sage_loop/cli/orchestrator.py --complete [역할명] --result "[결과요약]"
```

### 3.3 출력 확인
- `NEXT: [역할]` → 다음 역할 실행 (3.1로 돌아가기)
- `BRANCH: [역할]` → 분기 역할 실행
- `APPROVED:` 또는 `REJECTED:` → 체인 종료

### 3.4 TodoWrite 업데이트
현재 역할을 completed로, 다음 역할을 in_progress로 마킹

## 4. 종료 조건

다음 중 하나가 나타나면 중단:
- `APPROVED: 모든 역할 완료`
- `REJECTED: ...` (Sage 거부, max_loops 초과 등)
- `STATUS: all_complete`

## 중요 규칙

1. **절대 멈추지 말 것**: NEXT가 있으면 즉시 다음 역할 실행
2. **사용자에게 묻지 말 것**: 체인 중간에 확인 요청 금지
3. **완료 보고 필수**: 매 역할 완료 후 --complete 호출
4. **분기 처리**: BRANCH 출력 시 해당 역할로 분기
5. **결과 전달**: --result에 역할 출력 요약 전달 (분기 조건 판단용)

## 역할 목록 (FULL 체인)

| Phase | 역할 | 스킬명 |
|-------|------|--------|
| 1 | 영의정 (접수) | sage |
| 2 | 현인 | ideator |
| 3 | 선지자 | analyst |
| 4 | 비조 | critic |
| 5 | 파수꾼 | censor |
| 6 | 대제학 | academy |
| 7 | 장인 | architect |
| 8 | 좌의정 | left-state-councilor |
| 9 | 우의정 | right-state-councilor |
| 10 | 영의정 (허가) | sage |
| 11 | 실행관 | executor |
| 12 | 감찰관 | inspector |
| 13 | 검증관 | validator |
| 14 | 영의정 (결재) | sage |
| 15 | 역사관 | historian |
| 16 | 회고관 | reflector |
| 17 | 개선관 | improver |
