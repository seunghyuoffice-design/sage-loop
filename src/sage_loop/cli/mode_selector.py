#!/usr/bin/env python3
"""
Mode Selector - Sage 3가지 실행 모드 추천

- config.yaml의 execution_modes 기반
- 키워드 매칭 + 우선순위로 모드 결정
"""

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


DEFAULT_PRIORITY = ["interactive", "plan-first", "full-auto"]


def load_config(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"config.yaml not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize(text: str) -> str:
    return text.lower().strip()


def keyword_matches(text: str, keywords: List[str]) -> List[str]:
    hits = []
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in text:
            hits.append(kw)
    # 안정적인 순서를 유지하면서 중복 제거
    return list(dict.fromkeys(hits))


def collect_mode_matches(text: str, config: Dict) -> Dict[str, List[str]]:
    matches: Dict[str, List[str]] = {}
    for mode_name, mode_cfg in (config.get("execution_modes") or {}).items():
        rec = mode_cfg.get("recommended_for") or {}
        keywords = list(rec.get("keywords") or [])
        keywords.extend(rec.get("complexity") or [])
        keywords.extend(rec.get("risk") or [])
        hits = keyword_matches(text, keywords)
        if hits:
            matches[mode_name] = hits
    return matches


def pick_mode(matches: Dict[str, List[str]], config: Dict) -> str:
    for mode in DEFAULT_PRIORITY:
        if mode in matches:
            return mode
    if matches:
        return next(iter(matches.keys()))
    return config.get("default_mode", "plan-first")


def recommend_mode(text: str, config: Dict) -> Tuple[str, Dict[str, List[str]]]:
    normalized = normalize(text)
    matches = collect_mode_matches(normalized, config)
    mode = pick_mode(matches, config)
    return mode, matches


def print_mode_list(config: Dict):
    modes = config.get("execution_modes") or {}
    default_mode = config.get("default_mode", "plan-first")
    print("available_modes:")
    for name in modes.keys():
        print(f"  - {name}")
    print(f"default_mode: {default_mode}")


def main():
    parser = argparse.ArgumentParser(description="Sage mode selector (3-mode system)")
    parser.add_argument("text", nargs="?", help="작업 설명 텍스트")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "config.yaml"),
        help="Sage config.yaml 경로",
    )
    parser.add_argument("--list", action="store_true", help="모드 목록 출력")
    parser.add_argument("--dry-run", action="store_true", help="결정 과정 출력")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 출력")

    args = parser.parse_args()

    config = load_config(Path(args.config))

    if args.list:
        print_mode_list(config)
        return

    if not args.text:
        parser.print_help()
        raise SystemExit(1)

    mode, matches = recommend_mode(args.text, config)

    if args.verbose or args.dry_run:
        print(f"input: {args.text}")
        print(f"recommended_mode: {mode}")
        if matches:
            print("matches:")
            for name, hits in matches.items():
                print(f"  - {name}: {', '.join(hits)}")
        else:
            print("matches: (none)")
    else:
        print(mode)


if __name__ == "__main__":
    main()
