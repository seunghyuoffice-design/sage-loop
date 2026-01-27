#!/usr/bin/env python3
"""
Agenda Parser - sage 명령어에서 안건 파싱

사용:
    python3 agenda_parser.py "sage 풀체인"
    python3 agenda_parser.py "sage 풀체인: API 개선"
    python3 agenda_parser.py "sage API 개선 작업"

출력 (JSON):
    {"has_agenda": false, "chain": "FULL", "agenda": null}
    {"has_agenda": true, "chain": "FULL", "agenda": "API 개선"}
"""

import argparse
import json
import re
import sys


CHAIN_KEYWORDS = {
    "풀체인": "FULL",
    "full": "FULL",
    "전체": "FULL",
    "퀵체인": "QUICK",
    "quick": "QUICK",
    "리뷰체인": "REVIEW",
    "review": "REVIEW",
    "디자인체인": "DESIGN",
    "design": "DESIGN",
}


def parse_agenda(prompt: str) -> dict:
    """
    sage 명령어에서 체인명과 안건 파싱

    Returns:
        {
            "has_agenda": bool,
            "chain": str,  # FULL, QUICK, REVIEW, DESIGN
            "agenda": str | None,
            "prompt_type": str,  # "chain_only", "chain_with_agenda", "agenda_only"
        }
    """
    prompt = prompt.strip()

    # "sage" 접두사 제거 (공백 유무 상관없이)
    if prompt.lower().startswith("sage"):
        prompt = prompt[4:].strip()

    result = {
        "has_agenda": False,
        "chain": "FULL",  # 기본값
        "agenda": None,
        "prompt_type": "chain_only",
    }

    # 패턴 1: "풀체인: 안건" 또는 "풀체인 - 안건"
    for keyword, chain_name in CHAIN_KEYWORDS.items():
        pattern = rf"^{re.escape(keyword)}[\s::\-]+(.+)$"
        match = re.match(pattern, prompt, re.IGNORECASE)
        if match:
            result["chain"] = chain_name
            result["agenda"] = match.group(1).strip()
            result["has_agenda"] = True
            result["prompt_type"] = "chain_with_agenda"
            return result

    # 패턴 2: 체인명만 (안건 없음)
    prompt_lower = prompt.lower()
    for keyword, chain_name in CHAIN_KEYWORDS.items():
        if prompt_lower == keyword or prompt_lower == keyword.lower():
            result["chain"] = chain_name
            result["has_agenda"] = False
            result["prompt_type"] = "chain_only"
            return result

    # 패턴 3: 빈 입력 (안건 없음)
    if not prompt:
        result["has_agenda"] = False
        result["prompt_type"] = "chain_only"
        return result

    # 패턴 4: 체인명 없이 안건만
    if prompt not in CHAIN_KEYWORDS:
        result["agenda"] = prompt
        result["has_agenda"] = True
        result["prompt_type"] = "agenda_only"
        return result

    return result


def main():
    parser = argparse.ArgumentParser(description="Sage 안건 파서")
    parser.add_argument("prompt", help="sage 명령어 (예: 'sage 풀체인: API 개선')")
    parser.add_argument("--format", choices=["json", "text"], default="json")

    args = parser.parse_args()
    result = parse_agenda(args.prompt)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result["has_agenda"]:
            print(f"CHAIN: {result['chain']}")
            print(f"AGENDA: {result['agenda']}")
            print("ACTION: confirm_and_execute")
        else:
            print(f"CHAIN: {result['chain']}")
            print("AGENDA: (없음)")
            print("ACTION: ask_user_question")

    # 반환 코드: 안건 있으면 0, 없으면 1
    sys.exit(0 if result["has_agenda"] else 1)


if __name__ == "__main__":
    main()
