#!/usr/bin/env python3
"""
Sage L3 스크립트 검수 도구

다른 AI/사람이 검토할 수 있도록 코드 품질 리포트 생성

사용:
    python3 lint_scripts.py                    # 현재 디렉토리 검사
    python3 lint_scripts.py --path /some/dir   # 특정 경로 검사
    python3 lint_scripts.py --json             # JSON 출력
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Issue:
    """검출된 문제"""

    file: str
    line: int
    severity: str  # ERROR, WARNING, INFO
    code: str  # E001, W001, I001
    message: str


@dataclass
class LintResult:
    """검수 결과"""

    file: str
    issues: List[Issue] = field(default_factory=list)
    passed: bool = True


class ScriptLinter:
    """Python 스크립트 검수기"""

    def __init__(self):
        self.issues: List[Issue] = []

    def lint_file(self, path: Path) -> LintResult:
        """단일 파일 검수"""
        self.issues = []
        result = LintResult(file=str(path))

        try:
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
        except Exception as e:
            result.issues.append(
                Issue(
                    file=str(path),
                    line=0,
                    severity="ERROR",
                    code="E000",
                    message=f"파일 읽기 실패: {e}",
                )
            )
            result.passed = False
            return result

        # 1. 문법 검사
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            result.issues.append(
                Issue(
                    file=str(path),
                    line=e.lineno or 0,
                    severity="ERROR",
                    code="E001",
                    message=f"구문 오류: {e.msg}",
                )
            )
            result.passed = False
            return result

        # 2. 함수 내부 import 검사
        self._check_inner_imports(tree, str(path))

        # 3. 정규식 패턴 검사
        self._check_regex_patterns(lines, str(path))

        # 4. 중복 함수명 검사
        self._check_duplicate_functions(tree, str(path))

        # 5. 사용되지 않는 import 검사
        self._check_unused_imports(tree, content, str(path))

        # 6. 타입 힌트 일관성 검사
        self._check_type_hints(tree, str(path))

        # 7. docstring 검사
        self._check_docstrings(tree, str(path))

        result.issues = self.issues
        result.passed = not any(i.severity == "ERROR" for i in self.issues)
        return result

    def _check_inner_imports(self, tree: ast.AST, filepath: str):
        """함수 내부 import 검사"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        self.issues.append(
                            Issue(
                                file=filepath,
                                line=child.lineno,
                                severity="WARNING",
                                code="W001",
                                message=f"함수 내부 import: {self._get_import_name(child)}",
                            )
                        )

    def _get_import_name(self, node) -> str:
        """import 문에서 모듈명 추출"""
        if isinstance(node, ast.Import):
            return ", ".join(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            return node.module or ""
        return ""

    def _check_regex_patterns(self, lines: List[str], filepath: str):
        """정규식 패턴 검사"""
        for i, line in enumerate(lines, 1):
            # 이중 이스케이프 검사 (raw string 내 \\s 등)
            if 'r"' in line or "r'" in line:
                # raw string 내에서 \\s, \\d 등은 버그일 가능성
                if re.search(r'r["\'].*\\\\[sdwSDW]', line):
                    self.issues.append(
                        Issue(
                            file=filepath,
                            line=i,
                            severity="ERROR",
                            code="E002",
                            message="raw string 내 이중 이스케이프 의심: \\\\s → \\s",
                        )
                    )

            # 빈 문자 클래스 검사
            if re.search(r"\[\]", line) and ("re." in line or "pattern" in line.lower()):
                self.issues.append(
                    Issue(
                        file=filepath,
                        line=i,
                        severity="WARNING",
                        code="W002",
                        message="빈 문자 클래스 []",
                    )
                )

    def _check_duplicate_functions(self, tree: ast.AST, filepath: str):
        """중복 함수명 검사"""
        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name in functions:
                    self.issues.append(
                        Issue(
                            file=filepath,
                            line=node.lineno,
                            severity="ERROR",
                            code="E003",
                            message=f"중복 함수명: {node.name} (첫 정의: {functions[node.name]}행)",
                        )
                    )
                else:
                    functions[node.name] = node.lineno

    def _check_unused_imports(self, tree: ast.AST, content: str, filepath: str):
        """사용되지 않는 import 검사 (간단 버전)"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append((name, node.lineno))

        # 단순 검사: import 이후 코드에서 이름이 등장하는지
        for name, lineno in imports:
            # import 행 제외하고 검색
            lines = content.splitlines()
            found = False
            for i, line in enumerate(lines, 1):
                if i == lineno:
                    continue
                if re.search(rf"\b{re.escape(name)}\b", line):
                    found = True
                    break
            if not found:
                self.issues.append(
                    Issue(
                        file=filepath,
                        line=lineno,
                        severity="INFO",
                        code="I001",
                        message=f"미사용 import 의심: {name}",
                    )
                )

    def _check_type_hints(self, tree: ast.AST, filepath: str):
        """타입 힌트 일관성 검사"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 공개 함수(언더스코어 미시작)에 반환 타입 없으면 경고
                if not node.name.startswith("_") and node.name != "main":
                    if node.returns is None:
                        self.issues.append(
                            Issue(
                                file=filepath,
                                line=node.lineno,
                                severity="INFO",
                                code="I002",
                                message=f"반환 타입 힌트 없음: {node.name}()",
                            )
                        )

    def _check_docstrings(self, tree: ast.AST, filepath: str):
        """docstring 검사"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    if not node.name.startswith("_"):
                        self.issues.append(
                            Issue(
                                file=filepath,
                                line=node.lineno,
                                severity="INFO",
                                code="I003",
                                message=f"docstring 없음: {node.name}",
                            )
                        )


def lint_directory(path: Path) -> List[LintResult]:
    """디렉토리 내 모든 Python 파일 검수"""
    linter = ScriptLinter()
    results = []

    for py_file in path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        results.append(linter.lint_file(py_file))

    return results


def format_report(results: List[LintResult], json_output: bool = False) -> str:
    """검수 결과 포맷"""
    if json_output:
        data = []
        for r in results:
            data.append(
                {
                    "file": r.file,
                    "passed": r.passed,
                    "issues": [
                        {
                            "line": i.line,
                            "severity": i.severity,
                            "code": i.code,
                            "message": i.message,
                        }
                        for i in r.issues
                    ],
                }
            )
        return json.dumps(data, ensure_ascii=False, indent=2)

    # 텍스트 포맷
    lines = []
    lines.append("=" * 60)
    lines.append("Sage L3 스크립트 검수 리포트")
    lines.append("=" * 60)

    total_errors = 0
    total_warnings = 0
    total_info = 0

    for r in results:
        lines.append(f"\n📄 {r.file}")
        lines.append("-" * 40)

        if not r.issues:
            lines.append("  ✅ 문제 없음")
        else:
            for issue in r.issues:
                icon = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}.get(
                    issue.severity, "?"
                )
                lines.append(f"  {icon} [{issue.code}] 행 {issue.line}: {issue.message}")

                if issue.severity == "ERROR":
                    total_errors += 1
                elif issue.severity == "WARNING":
                    total_warnings += 1
                else:
                    total_info += 1

    lines.append("\n" + "=" * 60)
    lines.append("요약")
    lines.append("=" * 60)
    lines.append(f"  검사 파일: {len(results)}개")
    lines.append(f"  ❌ ERROR: {total_errors}개")
    lines.append(f"  ⚠️  WARNING: {total_warnings}개")
    lines.append(f"  ℹ️  INFO: {total_info}개")

    if total_errors > 0:
        lines.append("\n🚨 ERROR가 있습니다. 수정이 필요합니다.")
    elif total_warnings > 0:
        lines.append("\n⚠️  WARNING이 있습니다. 검토를 권장합니다.")
    else:
        lines.append("\n✅ 모든 검사 통과")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sage L3 스크립트 검수 도구")
    parser.add_argument("--path", type=str, default=".", help="검사할 경로")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--strict", action="store_true", help="WARNING도 실패로 처리")

    args = parser.parse_args()

    path = Path(args.path)
    if path.is_file():
        linter = ScriptLinter()
        results = [linter.lint_file(path)]
    else:
        results = lint_directory(path)

    print(format_report(results, json_output=args.json))

    # 종료 코드
    has_error = any(
        any(i.severity == "ERROR" for i in r.issues) for r in results
    )
    has_warning = any(
        any(i.severity == "WARNING" for i in r.issues) for r in results
    )

    if has_error:
        sys.exit(2)
    elif args.strict and has_warning:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
