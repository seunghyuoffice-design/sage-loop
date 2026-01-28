#!/usr/bin/env python3
"""
독설 진행 추적기 (Dokseol Progress Tracker)

PostToolUse hook에서 호출되어 작업 진행 상황에 따라 mid/end 독설 출력
"""
import json
import sys
import os
from pathlib import Path

# 상태 파일 경로
STATE_FILE = Path("/tmp/dokseol_state.json")

# 역할별 3단계 독설 (mid/end만 - start는 role_handler.py에서)
DOKSEOL = {
    # === 6조 역할 ===
    'ideator': {
        'mid': "⚠️ 지금 나열한 게 전부인가? 더 없나?",
        'end': "⚠️ 아이디어 수가 부족하면 그냥 실패다."
    },
    'analyst': {
        'mid': "⚠️ 순위만 매겨라. 설계는 네 일이 아니다.",
        'end': "⚠️ 불확실하면 불확실하다고 명시해라. 추측으로 채우지 마라."
    },
    'seungji': {
        'mid': "⚠️ 빠진 항목 없나 확인해라.",
        'end': "⚠️ 전달 형식이 틀리면 다시 해라."
    },
    'executor': {
        'mid': "⚠️ TODO나 생략은 허용되지 않는다.",
        'end': "⚠️ 실행 가능한 코드만 제출해라."
    },
    # === Core 역할 ===
    'critic': {
        'mid': "⚠️ 빠뜨린 위험이 없나?",
        'end': "⚠️ 칭찬은 필요 없다. 문제만 남겨라."
    },
    'architect': {
        'mid': "⚠️ 빠진 컴포넌트 없나?",
        'end': "⚠️ 설계가 모호하면 실행이 실패한다."
    },
    'validator': {
        'mid': "⚠️ 검증 기준이 명확한가?",
        'end': "⚠️ 애매하면 FAIL이다."
    },
    # === Advisory 역할 ===
    'academy': {
        'mid': "⚠️ 출처가 명확한가?",
        'end': "⚠️ 추측은 근거가 아니다."
    },
    'censor': {
        'mid': "⚠️ RULES 전체를 확인했나?",
        'end': "⚠️ 의심되면 BLOCK이다."
    },
    'compliance': {
        'mid': "⚠️ 라이선스/보안/아키텍처 전부 확인했나?",
        'end': "⚠️ 하나라도 위반이면 전체 위반이다."
    },
    'historian': {
        'mid': "⚠️ 빠진 이력이 없나?",
        'end': "⚠️ 왜곡 없이 있는 그대로 남겨라."
    },
    'inspector': {
        'mid': "⚠️ 전체를 훑었나?",
        'end': "⚠️ 의심되면 누락으로 처리해라."
    },
    'improver': {
        'mid': "⚠️ 다음 작업과 연결되나?",
        'end': "⚠️ 실행은 Executor 몫이다."
    },
    # === Approval 역할 ===
    'sage': {
        'mid': "⚠️ 모든 검토가 완료됐나?",
        'end': "⚠️ EXIT_SIGNAL 없이 끝내지 마라."
    },
    'left-state-councilor': {
        'mid': "⚠️ 인사/재정/의례 측면 전부 확인했나?",
        'end': "⚠️ 의견만 내고 결정은 Sage에게."
    },
    'right-state-councilor': {
        'mid': "⚠️ 보안/검증/인프라 측면 전부 확인했나?",
        'end': "⚠️ 의견만 내고 결정은 Sage에게."
    },
    # === Branch 역할 ===
    'referee': {
        'mid': "⚠️ 양측 주장을 정확히 파악했나?",
        'end': "⚠️ 한쪽 편들지 마라."
    },
    'feasibility-checker': {
        'mid': "⚠️ 기술/자원/시간 제약 전부 확인했나?",
        'end': "⚠️ 낙관은 금물이다."
    },
    'constraint-enforcer': {
        'mid': "⚠️ 모든 제약을 확인했나?",
        'end': "⚠️ 위반 상태로 진행하지 마라."
    },
    # === Ops 역할 ===
    'deploy': {
        'mid': "⚠️ 헬스체크 통과했나?",
        'end': "⚠️ 롤백 계획 없이 배포하지 마라."
    },
    'watchdog': {
        'mid': "⚠️ 이상 징후 놓치지 않았나?",
        'end': "⚠️ 의심되면 알람부터."
    },
    'code-review': {
        'mid': "⚠️ 성능/보안/가독성 전부 확인했나?",
        'end': "⚠️ 의견은 구체적으로."
    },
    'pipeline': {
        'mid': "⚠️ 각 단계 성공 여부 확인했나?",
        'end': "⚠️ 상태 확인 없이 진행하지 마라."
    },
    'quality': {
        'mid': "⚠️ 모든 품질 지표 확인했나?",
        'end': "⚠️ 품질 기준 미달이면 FAIL이다."
    },
    # === Management 역할 ===
    'resource-manager': {
        'mid': "⚠️ 예산 한도 확인했나?",
        'end': "⚠️ 예산 초과는 금지다."
    },
    'session': {
        'mid': "⚠️ 컨텍스트 손실 없나?",
        'end': "⚠️ 컨텍스트 손실 없이 복원해라."
    },
    'compact': {
        'mid': "⚠️ 중요 정보 누락 없나?",
        'end': "⚠️ 핵심만 남겨라."
    },
    'route': {
        'mid': "⚠️ 폴백 경로 확인했나?",
        'end': "⚠️ 라우팅 실패 시 폴백 필수."
    },
    # === Skill Management 역할 ===
    'skill-sync': {
        'mid': "⚠️ 모든 플랫폼 확인했나?",
        'end': "⚠️ 동기화 실패 시 롤백해라."
    },
    'skill-manager': {
        'mid': "⚠️ 검증 통과했나?",
        'end': "⚠️ 검증 없이 배포하지 마라."
    },
    'newskill': {
        'mid': "⚠️ 필수 필드 전부 있나?",
        'end': "⚠️ 표준 미준수 스킬은 거부된다."
    },
    'hook-manager': {
        'mid': "⚠️ 타임아웃 설정했나?",
        'end': "⚠️ 타임아웃 설정 필수."
    },
    # === 조선 관청 역할 ===
    'doseungji': {
        'mid': "⚠️ 누락된 승지 의견 없나?",
        'end': "⚠️ 취합 누락 없이 상신해라."
    },
    'saheonbu': {
        'mid': "⚠️ 모든 규칙 확인했나?",
        'end': "⚠️ 의심되면 BLOCK이다."
    },
    'sagawon': {
        'mid': "⚠️ 빠뜨린 문제 없나?",
        'end': "⚠️ 칭찬은 필요 없다. 문제만 남겨라."
    },
    'hongmungwan': {
        'mid': "⚠️ 근거가 명확한가?",
        'end': "⚠️ 추측은 근거가 아니다."
    },
    'gyujanggak': {
        'mid': "⚠️ 실행 가능한 개선안인가?",
        'end': "⚠️ 실행은 Executor 몫이다."
    },
    'uigeumbu': {
        'mid': "⚠️ 모든 위반 확인했나?",
        'end': "⚠️ 위반 상태로 진행하지 마라."
    },
    'chunchugwan': {
        'mid': "⚠️ 빠진 이력 없나?",
        'end': "⚠️ 왜곡 없이 있는 그대로 남겨라."
    },
    'seungmunwon': {
        'mid': "⚠️ 맥락 손실 없나?",
        'end': "⚠️ 맥락 손실 없이 정리해라."
    },
    'dohwaseo': {
        'mid': "⚠️ 설계가 명확한가?",
        'end': "⚠️ 설계가 모호하면 실행이 실패한다."
    },
    'gyoseogwan': {
        'mid': "⚠️ 기준이 명확한가?",
        'end': "⚠️ 검증 기준이 명확해야 한다."
    },
    'amhaeng': {
        'mid': "⚠️ 누락/오류 없나?",
        'end': "⚠️ 의심되면 누락으로 처리해라."
    },
    # === Approval 추가 ===
    'yeong-ui-jeong': {
        'mid': "⚠️ 좌/우의정 의견 전부 확인했나?",
        'end': "⚠️ 최종 결정권자임을 잊지 마라."
    },
    # === Branch 추가 ===
    'feedback-loop': {
        'mid': "⚠️ 모든 결과 수집했나?",
        'end': "⚠️ 결과 없이 종료하지 마라."
    },
    # === 6조 통합 관리 역할 ===
    'ministry-personnel': {
        'mid': "⚠️ 역할 할당 확인했나?",
        'end': "⚠️ 인사 정책은 신중히 다뤄라."
    },
    'ministry-finance': {
        'mid': "⚠️ 예산 확인했나?",
        'end': "⚠️ 예산 초과는 금지다."
    },
    'ministry-rites': {
        'mid': "⚠️ 형식 확인했나?",
        'end': "⚠️ 문서/의례 형식을 준수해라."
    },
    'ministry-military': {
        'mid': "⚠️ 절차 확인했나?",
        'end': "⚠️ 보안/운영 절차를 따라라."
    },
    'ministry-justice': {
        'mid': "⚠️ 기준 확인했나?",
        'end': "⚠️ 검증/감사 기준을 지켜라."
    },
    'ministry-works': {
        'mid': "⚠️ 절차 확인했나?",
        'end': "⚠️ 인프라/빌드 절차를 따라라."
    },
    # === Utility 역할 ===
    'ai-index-updater': {
        'mid': "⚠️ 누락된 파일 없나?",
        'end': "⚠️ 인덱스 누락 없이 업데이트해라."
    },
    'censor-general': {
        'mid': "⚠️ 모든 규칙 확인했나?",
        'end': "⚠️ 의심되면 BLOCK이다."
    },
    'collect': {
        'mid': "⚠️ 누락된 데이터 없나?",
        'end': "⚠️ 수집 누락 없이 완료해라."
    },
    'crawl': {
        'mid': "⚠️ 규칙 준수했나?",
        'end': "⚠️ 크롤링 규칙을 준수해라."
    },
    'dash': {
        'mid': "⚠️ 데이터 정확한가?",
        'end': "⚠️ 데이터 정확성을 확인해라."
    },
    'dep-license': {
        'mid': "⚠️ GPL/AGPL 확인했나?",
        'end': "⚠️ GPL/AGPL 위반은 금지다."
    },
    'hooks': {
        'mid': "⚠️ 설정 확인했나?",
        'end': "⚠️ 훅 설정을 신중히 다뤄라."
    },
    'insurer-terms': {
        'mid': "⚠️ 정확성 확인했나?",
        'end': "⚠️ 약관 정확성을 확인해라."
    },
    'library-evaluator': {
        'mid': "⚠️ 근거 명시했나?",
        'end': "⚠️ 역할 분류 근거를 명시해라."
    },
    'logs': {
        'mid': "⚠️ 패턴 확인했나?",
        'end': "⚠️ 로그 패턴을 놓치지 마라."
    },
    'parallel': {
        'mid': "⚠️ 충돌 확인했나?",
        'end': "⚠️ 충돌 없이 병렬 처리해라."
    },
    'pattern': {
        'mid': "⚠️ 일관성 확인했나?",
        'end': "⚠️ 패턴 일관성을 유지해라."
    },
    'policy-keeper': {
        'mid': "⚠️ 변경 사항 확인했나?",
        'end': "⚠️ 정책 변경은 신중히 다뤄라."
    },
    'reflector': {
        'mid': "⚠️ 객관적인가?",
        'end': "⚠️ 회고는 객관적으로 해라."
    },
    'sync': {
        'mid': "⚠️ 상태 확인했나?",
        'end': "⚠️ 동기화 실패 시 롤백해라."
    }
}


def get_role_type(role: str) -> str | None:
    """스킬명에서 역할 타입 추출"""
    # 6조 역할
    for role_type in ['ideator', 'analyst', 'seungji', 'executor']:
        if role.startswith(role_type):
            return role_type
    # 기타 역할 (정확히 일치)
    if role in DOKSEOL:
        return role
    return None


def load_state() -> dict:
    """상태 파일 로드"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"role": None, "tool_count": 0, "mid_shown": False, "end_shown": False}


def save_state(state: dict):
    """상태 파일 저장"""
    STATE_FILE.write_text(json.dumps(state))


def main():
    try:
        data = json.loads(sys.stdin.read())
    except:
        return

    tool_name = data.get("tool_name", "")

    state = load_state()
    role = state.get("role")

    if not role:
        # 역할이 설정되지 않음 (role_handler가 먼저 실행되어야 함)
        return

    role_type = get_role_type(role)
    if not role_type or role_type not in DOKSEOL:
        return

    # 도구 호출 횟수 증가
    state["tool_count"] = state.get("tool_count", 0) + 1
    count = state["tool_count"]

    output = {}

    # mid 독설: 3~5번째 도구 호출 시
    if 3 <= count <= 5 and not state.get("mid_shown"):
        output["enforcement"] = f"\n{DOKSEOL[role_type]['mid']}\n"
        state["mid_shown"] = True

    # end 독설: 8번째 이후 도구 호출 시
    elif count >= 8 and not state.get("end_shown"):
        output["enforcement"] = f"\n{DOKSEOL[role_type]['end']}\n"
        state["end_shown"] = True

    save_state(state)

    if output:
        print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
