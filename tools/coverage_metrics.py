"""Render statement, branch, function and line coverage from a coverage JSON file.

Function coverage is estimated from the AST: a function counts as covered when at
least one non-docstring body line was executed. This mirrors "function was called
at least once" for this small Flask project.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def _function_body_start(node):
    for statement in node.body:
        if isinstance(statement, ast.Expr) and isinstance(
            statement.value, ast.Constant
        ):
            if isinstance(statement.value.value, str):
                continue
        return statement.lineno
    return node.end_lineno


def _function_name(node):
    return node.name


def _collect_functions(source_path):
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = _function_body_start(node)
            functions.append((_function_name(node), start, node.end_lineno))
    return functions


def _percent(covered, total):
    if not total:
        return 100.0
    return covered * 100.0 / total


def _format_percent(value):
    return f"{value:.1f}%"


def build_report(coverage_json, root, title):
    data = json.loads(Path(coverage_json).read_text(encoding="utf-8"))
    files = []
    total_statements = total_covered_statements = 0
    total_branches = total_covered_branches = 0
    total_lines = total_covered_lines = 0
    total_functions = total_covered_functions = 0
    function_rows = []

    for filename, file_data in sorted(data.get("files", {}).items()):
        summary = file_data["summary"]
        source = Path(filename)
        if not source.is_absolute():
            source = Path(root) / source
        executed = set(file_data.get("executed_lines", []))
        missing = set(file_data.get("missing_lines", []))
        functions = _collect_functions(source) if source.is_file() else []

        covered_functions = 0
        for name, start, end in functions:
            executable = {
                line
                for line in range(start, end + 1)
                if line in executed or line in missing
            }
            covered = {line for line in executable if line in executed}
            if covered:
                covered_functions += 1
            if executable:
                function_rows.append(
                    (
                        f"{filename}:{name}",
                        start,
                        end,
                        _percent(len(covered), len(executable)),
                    )
                )

        statements = summary["num_statements"]
        covered_statements = summary["covered_lines"]
        branches = summary["num_branches"]
        covered_branches = summary["covered_branches"]
        line_total = len(executed) + len(missing)
        line_covered = len(executed)

        files.append(
            {
                "filename": filename,
                "stmt_pct": _percent(covered_statements, statements),
                "stmt_covered": covered_statements,
                "stmt_total": statements,
                "branch_pct": _percent(covered_branches, branches),
                "branch_covered": covered_branches,
                "branch_total": branches,
                "func_pct": _percent(covered_functions, len(functions)),
                "func_covered": covered_functions,
                "func_total": len(functions),
                "line_pct": _percent(line_covered, line_total),
                "line_covered": line_covered,
                "line_total": line_total,
            }
        )

        total_statements += statements
        total_covered_statements += covered_statements
        total_branches += branches
        total_covered_branches += covered_branches
        total_lines += line_total
        total_covered_lines += line_covered
        total_functions += len(functions)
        total_covered_functions += covered_functions

    lines = [
        f"# {title}",
        "",
        f"数据源：`{coverage_json}`。函数覆盖率按“函数体至少执行一行”估算，含嵌套函数。",
        "",
        "| 文件 | 语句 % | 分支 % | 函数 % | 行 % |",
        "|---|---|---|---|---|",
    ]
    for row in files:
        lines.append(
            f"| `{row['filename']}` "
            f"| {_format_percent(row['stmt_pct'])} "
            f"({row['stmt_covered']}/{row['stmt_total']}) "
            f"| {_format_percent(row['branch_pct'])} "
            f"({row['branch_covered']}/{row['branch_total']}) "
            f"| {_format_percent(row['func_pct'])} "
            f"({row['func_covered']}/{row['func_total']}) "
            f"| {_format_percent(row['line_pct'])} "
            f"({row['line_covered']}/{row['line_total']}) |"
        )
    lines.append(
        f"| **合计** | **{_format_percent(_percent(total_covered_statements, total_statements))}** "
        f"({total_covered_statements}/{total_statements}) "
        f"| **{_format_percent(_percent(total_covered_branches, total_branches))}** "
        f"({total_covered_branches}/{total_branches}) "
        f"| **{_format_percent(_percent(total_covered_functions, total_functions))}** "
        f"({total_covered_functions}/{total_functions}) "
        f"| **{_format_percent(_percent(total_covered_lines, total_lines))}** "
        f"({total_covered_lines}/{total_lines}) |"
    )

    lowest = sorted(function_rows, key=lambda item: item[3])[:3]
    lines.extend(
        [
            "",
            "## 函数行覆盖最低的 3 个函数",
            "",
            "| 函数 | 行范围 | 函数内行覆盖 |",
            "|---|---|---|",
        ]
    )
    for name, start, end, pct in lowest:
        lines.append(f"| `{name}` | {start}-{end} | {_format_percent(pct)} |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("coverage_json")
    parser.add_argument("--root", default=".")
    parser.add_argument("--title", default="覆盖率指标")
    parser.add_argument("--output")
    args = parser.parse_args()

    report = build_report(args.coverage_json, args.root, args.title)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"written: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
