#!/usr/bin/env python3
"""
sage-loop 자동 릴리즈 스크립트

pyproject.toml 버전이 업데이트되면:
1. Git 태그 생성
2. CHANGELOG.md에서 릴리즈 노트 추출
3. GitHub 릴리즈 생성
"""

import re
import subprocess
import sys
from pathlib import Path


def get_version_from_pyproject() -> str:
    """pyproject.toml에서 현재 버전 읽기"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject_path.read_text()

    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("pyproject.toml에서 버전을 찾을 수 없습니다")

    return match.group(1)


def get_existing_tags() -> set[str]:
    """기존 Git 태그 목록 가져오기"""
    result = subprocess.run(
        ["git", "tag", "-l"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()


def extract_changelog_section(version: str) -> str | None:
    """CHANGELOG.md에서 특정 버전의 섹션 추출"""
    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
    if not changelog_path.exists():
        return None

    content = changelog_path.read_text()

    # 버전 섹션 찾기 (예: ## [1.3.1] - 2026-01-28)
    pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return None

    notes = match.group(1).strip()

    # Full Changelog 링크 추가
    prev_version = get_previous_version(version, content)
    if prev_version:
        notes += f"\n\n---\n\n**Full Changelog**: https://github.com/seunghyuoffice-design/sage-loop/compare/v{prev_version}...v{version}"

    return notes


def get_previous_version(current: str, changelog: str) -> str | None:
    """CHANGELOG.md에서 이전 버전 찾기"""
    pattern = r"## \[([^\]]+)\]"
    versions = re.findall(pattern, changelog)

    try:
        idx = versions.index(current)
        if idx + 1 < len(versions):
            return versions[idx + 1]
    except (ValueError, IndexError):
        pass

    return None


def create_git_tag(version: str) -> bool:
    """Git 태그 생성"""
    tag = f"v{version}"

    try:
        subprocess.run(
            ["git", "tag", tag],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", tag],
            check=True,
            capture_output=True,
        )
        print(f"✓ Git 태그 생성: {tag}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Git 태그 생성 실패: {e.stderr.decode()}")
        return False


def create_github_release(version: str, notes: str) -> bool:
    """GitHub 릴리즈 생성"""
    tag = f"v{version}"

    # 제목 추출 (CHANGELOG의 첫 줄에서)
    title = f"v{version}"
    if notes:
        first_line = notes.split("\n")[0].strip()
        if first_line.startswith("-") or first_line.startswith("**"):
            # 첫 줄이 항목이면 간단한 제목 사용
            title = f"v{version}"
        else:
            title = f"v{version} - {first_line}"

    try:
        subprocess.run(
            ["gh", "release", "create", tag, "--title", title, "--notes", notes],
            check=True,
            capture_output=True,
        )
        print(f"✓ GitHub 릴리즈 생성: https://github.com/seunghyuoffice-design/sage-loop/releases/tag/{tag}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ GitHub 릴리즈 생성 실패: {e.stderr.decode()}")
        return False


def main():
    """메인 함수"""
    print("sage-loop 자동 릴리즈 시작...")

    # 1. 현재 버전 확인
    try:
        version = get_version_from_pyproject()
        print(f"현재 버전: {version}")
    except Exception as e:
        print(f"✗ 버전 확인 실패: {e}")
        sys.exit(1)

    # 2. 태그가 이미 존재하는지 확인
    existing_tags = get_existing_tags()
    tag = f"v{version}"

    if tag in existing_tags:
        print(f"✓ 태그 {tag}가 이미 존재합니다")
    else:
        # 3. Git 태그 생성
        if not create_git_tag(version):
            sys.exit(1)

    # 4. GitHub 릴리즈 확인
    result = subprocess.run(
        ["gh", "release", "view", tag],
        capture_output=True,
    )

    if result.returncode == 0:
        print(f"✓ 릴리즈 {tag}가 이미 존재합니다")
        return

    # 5. CHANGELOG에서 릴리즈 노트 추출
    notes = extract_changelog_section(version)
    if not notes:
        print(f"⚠ CHANGELOG.md에서 버전 {version} 섹션을 찾을 수 없습니다")
        notes = f"Release v{version}"

    # 6. GitHub 릴리즈 생성
    if not create_github_release(version, notes):
        sys.exit(1)

    print("\n✓ 자동 릴리즈 완료!")


if __name__ == "__main__":
    main()
