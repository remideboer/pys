"""Apply text edits from a RefactorPlan to source strings (tests / preview)."""
from __future__ import annotations

from pathlib import Path

from .plan import RefactorEdit, RefactorPlan


def apply_edits_to_text(text: str, edits: list[RefactorEdit]) -> str:
    """Apply replace/insert/delete edits to one file's text (1-based positions)."""
    lines = text.splitlines(keepends=True)
    # Work bottom-up so offsets stay valid
    ordered = sorted(
        edits,
        key=lambda e: (e.line, e.column, e.end_line, e.end_column),
        reverse=True,
    )
    for ed in ordered:
        if ed.kind == "insert":
            line_i = ed.line - 1
            if line_i < 0:
                line_i = 0
            col = max(ed.column - 1, 0)
            while len(lines) <= line_i:
                lines.append("\n")
            line = lines[line_i]
            # strip keepends for splice
            nl = ""
            body = line
            if body.endswith("\r\n"):
                nl = "\r\n"
                body = body[:-2]
            elif body.endswith("\n"):
                nl = "\n"
                body = body[:-1]
            lines[line_i] = body[:col] + ed.new_text + body[col:] + nl
            continue
        # replace / delete
        start_line = ed.line - 1
        end_line = ed.end_line - 1
        start_col = max(ed.column - 1, 0)
        end_col = max(ed.end_column - 1, 0)
        if start_line == end_line:
            line = lines[start_line]
            nl = ""
            body = line
            if body.endswith("\r\n"):
                nl = "\r\n"
                body = body[:-2]
            elif body.endswith("\n"):
                nl = "\n"
                body = body[:-1]
            lines[start_line] = body[:start_col] + ed.new_text + body[end_col:] + nl
        else:
            # Multi-line replace: keep prefix of first + new_text + suffix of last
            first = lines[start_line]
            last = lines[end_line]
            nl = "\n"
            if first.endswith("\r\n"):
                first_body, first_nl = first[:-2], "\r\n"
            elif first.endswith("\n"):
                first_body, first_nl = first[:-1], "\n"
            else:
                first_body, first_nl = first, ""
            if last.endswith("\r\n"):
                last_body, last_nl = last[:-2], "\r\n"
            elif last.endswith("\n"):
                last_body, last_nl = last[:-1], "\n"
            else:
                last_body, last_nl = last, ""
            merged = first_body[:start_col] + ed.new_text + last_body[end_col:] + last_nl
            lines[start_line : end_line + 1] = [merged]
    return "".join(lines)


def apply_plan_to_files(plan: RefactorPlan, roots: dict[str, str] | None = None) -> dict[str, str]:
    """Return mapping path → new text after applying plan edits."""
    by_file: dict[str, list[RefactorEdit]] = {}
    for ed in plan.edits:
        by_file.setdefault(ed.file, []).append(ed)
    out: dict[str, str] = {}
    for path, edits in by_file.items():
        if roots and path in roots:
            text = roots[path]
        else:
            text = Path(path).read_text(encoding="utf-8")
        out[path] = apply_edits_to_text(text, edits)
    return out
