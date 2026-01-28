#!/usr/bin/env python3
"""
독설 동적 주입기 (Dokseol Dynamic Injector)

Hook에서 호출되어 역할/진행단계에 맞는 독설 출력
"""
import sys
import json
import os

# 역할별 3단계 독설
DOKSEOL = {
    'ideator': {
        'start': "⚠️ 판단하지 말고 쏟아내라. 10개 안 되면 시작도 안 한 거다.",
        'mid': "⚠️ 지금 나열한 게 전부인가? 더 없나?",
        'end': "⚠️ 아이디어 수가 부족하면 그냥 실패다."
    },
    'analyst': {
        'start': "⚠️ 네 역할은 정리다. 새 아이디어 추가하면 월권이다.",
        'mid': "⚠️ 순위만 매겨라. 설계는 네 일이 아니다.",
        'end': "⚠️ 불확실하면 불확실하다고 명시해라. 추측으로 채우지 마라."
    },
    'seungji': {
        'start': "⚠️ 원안을 바꾸지 마라. 형식만 갖춰라.",
        'mid': "⚠️ 빠진 항목 없나 확인해라.",
        'end': "⚠️ 전달 형식이 틀리면 다시 해라."
    },
    'executor': {
        'start': "⚠️ 설계대로만 구현해라. 판단하지 마라.",
        'mid': "⚠️ TODO나 생략은 허용되지 않는다.",
        'end': "⚠️ 실행 가능한 코드만 제출해라."
    }
}

def get_role_from_skill(skill_name: str) -> str | None:
    """스킬명에서 역할 추출"""
    for role in ['ideator', 'analyst', 'seungji', 'executor']:
        if skill_name.startswith(role):
            return role
    return None

def inject(role: str, stage: str) -> None:
    """독설 출력"""
    if role in DOKSEOL and stage in DOKSEOL[role]:
        print(f"\n{DOKSEOL[role][stage]}\n", file=sys.stderr)

def main():
    if len(sys.argv) < 3:
        print("Usage: dokseol_injector.py <skill_name> <stage>", file=sys.stderr)
        sys.exit(1)

    skill_name = sys.argv[1]  # e.g., ideator-ijo
    stage = sys.argv[2]       # start | mid | end

    role = get_role_from_skill(skill_name)
    if role:
        inject(role, stage)

if __name__ == '__main__':
    main()
