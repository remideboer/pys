"""Extract Variable / Extract Function refactors."""
from __future__ import annotations

import re
from pathlib import Path

from ..lex import KEYWORDS
from ..parse import parse_program
from .catalog import catalog_entry
from .plan import RefactorConflict, RefactorEdit, RefactorPlan


_IDENT = re.compile(r"^[A-Za-z_]\w*$")


def plan_extract_variable(
    source_path: Path,
    *,
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
    new_name: str,
    declare_type: str = "var",
) -> RefactorPlan:
    meta = catalog_entry("extract-variable")
    plan = RefactorPlan(
        ok=False,
        catalog_id="extract-variable",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    new_name = (new_name or "").strip()
    if not _IDENT.match(new_name) or new_name in KEYWORDS:
        plan.conflicts.append(RefactorConflict(message=f"Invalid name {new_name!r}."))
        return plan
    path = source_path.resolve()
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        plan.conflicts.append(RefactorConflict(message="Selection out of range."))
        return plan
    if start_line != end_line:
        plan.conflicts.append(
            RefactorConflict(message="Extract Variable supports a single-line expression selection.")
        )
        return plan
    line = lines[start_line - 1]
    expr = line[start_column - 1 : end_column - 1]
    if not expr.strip():
        plan.conflicts.append(RefactorConflict(message="Empty selection."))
        return plan
    # Insert decl on previous line (same indent as current)
    indent = re.match(r"^[ \t]*", line)
    ind = indent.group(0) if indent else ""
    dtype = declare_type if declare_type != "var" else "var"
    decl_line = f"{ind}{dtype} {new_name} = {expr.strip()}\n"
    # Replace expression with name
    plan.edits.append(
        RefactorEdit(
            file=str(path),
            line=start_line,
            column=start_column,
            end_line=end_line,
            end_column=end_column,
            new_text=new_name,
            kind="replace",
            label="replace expression",
        )
    )
    plan.edits.append(
        RefactorEdit(
            file=str(path),
            line=start_line,
            column=1,
            end_line=start_line,
            end_column=1,
            new_text=decl_line,
            kind="insert",
            label="insert declaration",
        )
    )
    plan.ok = True
    return plan


def plan_extract_function(
    source_path: Path,
    *,
    start_line: int,
    end_line: int,
    new_name: str,
    visibility: str = "",
) -> RefactorPlan:
    meta = catalog_entry("extract-function")
    plan = RefactorPlan(
        ok=False,
        catalog_id="extract-function",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    new_name = (new_name or "").strip()
    if not _IDENT.match(new_name) or new_name in KEYWORDS:
        plan.conflicts.append(RefactorConflict(message=f"Invalid name {new_name!r}."))
        return plan
    path = source_path.resolve()
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        plan.conflicts.append(RefactorConflict(message="Selection out of range."))
        return plan
    selected = "".join(lines[start_line - 1 : end_line])
    # Detect if inside class by scanning upward for `class ` / `entity `
    before = "".join(lines[: start_line - 1])
    in_type = bool(re.search(r"\b(class|entity)\s+\w+", before)) and before.rstrip().endswith("{") is False
    # Simpler: count unmatched braces before selection
    open_braces = before.count("{") - before.count("}")
    is_method = open_braces >= 2  # module {? no — brace class body is depth>=1 with class header
    # Heuristic: if `class` or `entity` appears with brace depth >= 1
    is_method = open_braces >= 1 and bool(
        re.search(r"\b(class|entity|abstract\s+class)\s+\w+", before)
    )

    body_indent = "    "
    first = lines[start_line - 1]
    m = re.match(r"^([ \t]*)", first)
    sel_indent = m.group(1) if m else ""
    # Dedent selected body by sel_indent length relative to body_indent
    body_lines = []
    for raw in lines[start_line - 1 : end_line]:
        nl = "\n" if raw.endswith("\n") else ""
        core = raw[:-1] if raw.endswith("\n") else raw
        if core.startswith(sel_indent):
            core = core[len(sel_indent) :]
        body_lines.append(body_indent + core + nl)
    body_text = "".join(body_lines)
    if not body_text.endswith("\n"):
        body_text += "\n"

    if is_method:
        # Insert method at end of class: before last closing braces of file type — 
        # place immediately before selection as call, and insert method after type's last field/method:
        # Practical DoD: insert new method just before the selected lines (still in method section if selection was methods),
        # and replace selection with call.
        access = "public"
        fn = f"{sel_indent}{access} {new_name}() {{\n{body_text}{sel_indent}}}\n\n"
        call = f"{sel_indent}this.{new_name}()\n"
        # Delete selection then insert call, insert function before selection
        plan.edits.append(
            RefactorEdit(
                file=str(path),
                line=start_line,
                column=1,
                end_line=end_line,
                end_column=len(lines[end_line - 1].rstrip("\r\n")) + 1,
                new_text=call,
                kind="replace",
                label="replace with method call",
            )
        )
        plan.edits.append(
            RefactorEdit(
                file=str(path),
                line=start_line,
                column=1,
                end_line=start_line,
                end_column=1,
                new_text=fn,
                kind="insert",
                label="insert method (method section)",
            )
        )
    else:
        vis = f"{visibility} " if visibility else ""
        fn = f"{vis}function {new_name}() {{\n{body_text}}}\n\n"
        call = f"{sel_indent}{new_name}()\n"
        plan.edits.append(
            RefactorEdit(
                file=str(path),
                line=start_line,
                column=1,
                end_line=end_line,
                end_column=len(lines[end_line - 1].rstrip("\r\n")) + 1,
                new_text=call,
                kind="replace",
                label="replace with call",
            )
        )
        # Insert function at top of file after imports
        insert_at = 1
        try:
            mod = parse_program(text)
            for stmt in mod.body:
                from ..ast_nodes import ImportStmt, CommentStmt, BlankStmt

                if isinstance(stmt, (ImportStmt, CommentStmt, BlankStmt)):
                    if stmt.span:
                        insert_at = max(insert_at, stmt.span.line + 1)
                else:
                    break
        except Exception:
            insert_at = 1
        plan.edits.append(
            RefactorEdit(
                file=str(path),
                line=insert_at,
                column=1,
                end_line=insert_at,
                end_column=1,
                new_text=fn,
                kind="insert",
                label="insert function",
            )
        )
    plan.ok = True
    return plan
