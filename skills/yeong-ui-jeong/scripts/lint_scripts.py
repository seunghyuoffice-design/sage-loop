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
import io
import json
import re
import sys
import tokenize
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


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

    _DEFAULT_NORMAL_INFO_EXCLUDE = {"I002", "I003"}

    def __init__(
        self,
        info_level: str = "normal",
        info_codes: Optional[Set[str]] = None,
        info_exclude_codes: Optional[Set[str]] = None,
    ):
        self.issues: List[Issue] = []
        self.info_level = info_level
        self.info_codes = info_codes
        self.info_exclude_codes = info_exclude_codes or set()

    _EXCLUDE_DIRS: Set[str] = {
        "__pycache__",
        ".venv",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
    }
    _REGEX_CONTEXT_RE = re.compile(
        r"\b(compile|search|match|fullmatch|findall|finditer|sub|split)\s*\(",
        re.IGNORECASE,
    )

    def _summarize_results(self, results: List[LintResult]) -> Tuple[int, int, int]:
        """리포트 요약 수치 계산"""
        total_errors = 0
        total_warnings = 0
        total_info = 0

        for result in results:
            for issue in result.issues:
                if issue.severity == "ERROR":
                    total_errors += 1
                elif issue.severity == "WARNING":
                    total_warnings += 1
                else:
                    total_info += 1

        return total_errors, total_warnings, total_info

    def _issue_reason(self, errors: int, warnings: int, info: int) -> str:
        """파일별 통과 사유 요약"""
        if errors > 0:
            return f"errors:{errors}"
        if warnings > 0:
            return f"warnings:{warnings}"
        if info > 0:
            return f"info:{info}"
        return "clean"

    def _issue_reason_codes(self, issues: List[Issue]) -> Dict[str, Dict[str, int]]:
        """파일별 코드 사유 요약 (코드별 발생 횟수)"""
        reason: Dict[str, Counter] = {
            "errors": Counter(),
            "warnings": Counter(),
            "info": Counter(),
        }
        for issue in issues:
            if issue.severity == "ERROR":
                reason["errors"][issue.code] += 1
            elif issue.severity == "WARNING":
                reason["warnings"][issue.code] += 1
            else:
                reason["info"][issue.code] += 1
        return {
            "errors": dict(reason["errors"]),
            "warnings": dict(reason["warnings"]),
            "info": dict(reason["info"]),
        }

    def _top_codes(self, issues: List[Issue], top_n: int) -> Dict[str, List[Dict[str, int]]]:
        """심각도별 상위 코드 통계"""
        reason = self._issue_reason_codes(issues)
        top = {}
        for key in ("errors", "warnings", "info"):
            items = sorted(reason[key].items(), key=lambda kv: (-kv[1], kv[0]))
            top[key] = [{"code": code, "count": count} for code, count in items[:top_n]]
        return top

    def lint_file(self, path: Path) -> LintResult:
        """단일 파일 검수"""
        self.issues = []
        result = LintResult(file=str(path))

        try:
            content = path.read_text(encoding="utf-8")
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
        self._check_regex_patterns(content, str(path))

        # 4. 중복 함수명 검사
        self._check_duplicate_functions(tree, str(path))

        # 5. 사용되지 않는 import 검사
        self._check_unused_imports(tree, str(path))

        # 6. 타입 힌트 일관성 검사
        self._check_type_hints(tree, str(path))

        # 7. docstring 검사
        self._check_docstrings(tree, str(path))

        result.issues = self._filter_info_issues(self.issues)
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

    def _check_regex_patterns(self, content: str, filepath: str):
        """정규식 패턴 검사"""
        lines = content.splitlines()

        for token in tokenize.generate_tokens(io.StringIO(content).readline):
            if token.type != tokenize.STRING:
                continue

            line_no = token.start[0]
            line_text = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            if not self._is_regex_context_line(line_text):
                continue

            try:
                value = ast.literal_eval(token.string)
            except Exception:
                continue

            if "[]" in value:
                self.issues.append(
                    Issue(
                        file=filepath,
                        line=line_no,
                        severity="WARNING",
                        code="W002",
                        message="빈 문자 클래스 []",
                    )
                )

            prefix = self._get_string_prefix(token.string)
            if "r" not in prefix or "f" in prefix:
                continue
            if re.search(r"\\\\[sdwSDW]", value):
                self.issues.append(
                    Issue(
                        file=filepath,
                        line=line_no,
                        severity="ERROR",
                        code="E002",
                        message="raw string 내 이중 이스케이프 의심: \\\\s → \\s",
                    )
                )

    def _get_string_prefix(self, literal: str) -> str:
        """문자열 리터럴 접두사 추출 (r, b, f, u 조합)"""
        for idx, ch in enumerate(literal):
            if ch in ("'", '"'):
                return literal[:idx].lower()
        return ""

    def _is_regex_context_line(self, line: str) -> bool:
        """정규식 맥락 라인 판정"""
        lowered = line.lower()
        if "re." in line:
            return True
        if "pattern" in lowered or "regex" in lowered:
            return True
        if self._REGEX_CONTEXT_RE.search(lowered):
            return True
        return False

    def _build_parent_map(self, tree: ast.AST) -> Dict[ast.AST, ast.AST]:
        """AST 부모 노드 맵 생성"""
        parent_map: Dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parent_map[child] = parent
        return parent_map

    def _filter_info_issues(self, issues: List[Issue]) -> List[Issue]:
        """INFO 코드 필터 적용"""
        if not self.info_codes and not self.info_exclude_codes:
            return issues

        filtered: List[Issue] = []
        for issue in issues:
            if issue.severity != "INFO":
                filtered.append(issue)
                continue
            if self.info_codes and issue.code not in self.info_codes:
                continue
            if issue.code in self.info_exclude_codes:
                continue
            filtered.append(issue)
        return filtered

    def _is_nested_def(self, node: ast.AST, parent_map: Dict[ast.AST, ast.AST]) -> bool:
        """중첩된 함수/클래스 여부 판정"""
        parent = parent_map.get(node)
        while parent:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return True
            parent = parent_map.get(parent)
        return False

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

    def _check_unused_imports(self, tree: ast.AST, filepath: str):
        """사용되지 않는 import 검사 (AST 기반)"""
        if self.info_level == "off":
            return

        imports = []
        used_names: Set[str] = set()

        class UsedNameVisitor(ast.NodeVisitor):
            """사용된 이름 수집"""

            def visit_Name(self, node: ast.Name) -> None:
                """사용된 식별자 기록"""
                if isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
                self.generic_visit(node)

        UsedNameVisitor().visit(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imports.append((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    imports.append((name, node.lineno))

        for name, lineno in imports:
            if name not in used_names:
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
        if self.info_level == "off":
            return

        parent_map = self._build_parent_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self.info_level != "strict":
                    if self._is_nested_def(node, parent_map):
                        continue
                    # 공개 함수(언더스코어 미시작)에 반환 타입 없으면 경고
                    if node.name.startswith("_") or node.name == "main":
                        continue
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
        if self.info_level == "off":
            return

        parent_map = self._build_parent_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if self.info_level != "strict":
                    if self._is_nested_def(node, parent_map):
                        continue
                    if node.name.startswith("_"):
                        continue
                if not ast.get_docstring(node):
                    self.issues.append(
                        Issue(
                            file=filepath,
                            line=node.lineno,
                            severity="INFO",
                            code="I003",
                            message=f"docstring 없음: {node.name}",
                        )
                    )


def lint_directory(
    path: Path,
    info_level: str,
    info_codes: Optional[Set[str]],
    info_exclude_codes: Set[str],
) -> List[LintResult]:
    """디렉토리 내 모든 Python 파일 검수"""
    linter = ScriptLinter(
        info_level=info_level,
        info_codes=info_codes,
        info_exclude_codes=info_exclude_codes,
    )
    results = []

    for py_file in sorted(path.rglob("*.py")):
        if any(part in linter._EXCLUDE_DIRS for part in py_file.parts):
            continue
        results.append(linter.lint_file(py_file))

    return results


def format_report(
    results: List[LintResult],
    json_output: bool = False,
    json_format: str = "summary",
    summary_top_n: int = 5,
) -> str:
    """검수 결과 포맷"""
    summary_errors = 0
    summary_warnings = 0
    summary_info = 0

    if json_output:
        data_files = []
        file_reasons = []
        for r in results:
            file_errors = 0
            file_warnings = 0
            file_info = 0
            for issue in r.issues:
                if issue.severity == "ERROR":
                    file_errors += 1
                elif issue.severity == "WARNING":
                    file_warnings += 1
                else:
                    file_info += 1
            linter = ScriptLinter()
            reason = linter._issue_reason(file_errors, file_warnings, file_info)
            reason_codes = linter._issue_reason_codes(r.issues)
            file_reasons.append(
                {
                    "file": r.file,
                    "passed": r.passed,
                    "reason": reason,
                    "reason_codes": reason_codes,
                    "counts": {
                        "errors": file_errors,
                        "warnings": file_warnings,
                        "info": file_info,
                    },
                }
            )
            data_files.append(
                {
                    "file": r.file,
                    "passed": r.passed,
                    "reason": reason,
                    "reason_codes": reason_codes,
                    "counts": {
                        "errors": file_errors,
                        "warnings": file_warnings,
                        "info": file_info,
                    },
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
        for r in results:
            for issue in r.issues:
                if issue.severity == "ERROR":
                    summary_errors += 1
                elif issue.severity == "WARNING":
                    summary_warnings += 1
                else:
                    summary_info += 1

        all_issues = [issue for r in results for issue in r.issues]
        summary = {
            "file_count": len(results),
            "errors": summary_errors,
            "warnings": summary_warnings,
            "info": summary_info,
            "passed": summary_errors == 0,
            "strict_passed": summary_errors == 0 and summary_warnings == 0,
            "file_reasons": file_reasons,
            "top_codes": ScriptLinter()._top_codes(all_issues, summary_top_n),
        }

        if json_format == "legacy":
            return json.dumps(data_files, ensure_ascii=False, indent=2)
        return json.dumps(
            {"summary": summary, "files": data_files},
            ensure_ascii=False,
            indent=2,
        )

    # 텍스트 포맷
    lines = []
    lines.append("=" * 60)
    lines.append("Sage L3 스크립트 검수 리포트")
    lines.append("=" * 60)

    total_errors, total_warnings, total_info = ScriptLinter()._summarize_results(results)

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
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="Sage L3 스크립트 검수 도구")
    parser.add_argument("--path", type=str, default=".", help="검사할 경로")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument(
        "--json-format",
        choices=["summary", "legacy"],
        default="summary",
        help="JSON 출력 형식 (summary: 요약 포함, legacy: 기존 파일 리스트)",
    )
    parser.add_argument(
        "--summary-top-n",
        type=int,
        default=5,
        help="JSON summary의 심각도별 상위 코드 개수",
    )
    parser.add_argument(
        "--info-level",
        choices=["off", "normal", "strict"],
        default="normal",
        help="INFO 검사 기준 (off=비활성, normal=기본, strict=엄격)",
    )
    parser.add_argument(
        "--info-codes",
        type=str,
        default="",
        help="INFO 코드 선택 (예: I001,I003). 지정 시 해당 코드만 포함",
    )
    parser.add_argument(
        "--info-exclude-codes",
        type=str,
        default="",
        help="제외할 INFO 코드 (예: I002). 여러 개는 콤마로 구분",
    )
    parser.add_argument("--strict", action="store_true", help="WARNING도 실패로 처리")

    args = parser.parse_args()

    def parse_code_list(value: str) -> Optional[Set[str]]:
        codes = {code.strip().upper() for code in value.split(",") if code.strip()}
        return codes or None

    info_codes = parse_code_list(args.info_codes)
    info_exclude_codes = parse_code_list(args.info_exclude_codes) or set()
    if (
        args.info_level == "normal"
        and info_codes is None
        and not args.info_exclude_codes
    ):
        info_exclude_codes = ScriptLinter._DEFAULT_NORMAL_INFO_EXCLUDE.copy()

    path = Path(args.path)
    if not path.exists():
        print(f"경로가 존재하지 않습니다: {path}", file=sys.stderr)
        sys.exit(2)
    if path.is_file():
        linter = ScriptLinter(
            info_level=args.info_level,
            info_codes=info_codes,
            info_exclude_codes=info_exclude_codes,
        )
        results = [linter.lint_file(path)]
    else:
        results = lint_directory(
            path,
            info_level=args.info_level,
            info_codes=info_codes,
            info_exclude_codes=info_exclude_codes,
        )

    print(
        format_report(
            results,
            json_output=args.json,
            json_format=args.json_format,
            summary_top_n=args.summary_top_n,
        )
    )

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
