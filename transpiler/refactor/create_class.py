"""Create Class stub from an unresolved constructor call with named args."""
from __future__ import annotations

import re
from pathlib import Path

from ..ast_nodes import AssignStmt, Call, Identifier, KeywordArg, Literal, Module
from ..parse import parse_program
from ..transpiler import TranspileError
from .plan import RefactorConflict, RefactorEdit, RefactorPlan


def _infer_type(expr) -> str:
    if isinstance(expr, Literal):
        kind = expr.kind or ""
        if kind in {"string", "int", "float", "bool", "char"}:
            return kind
        text = expr.text or ""
        if kind == "string" or text.startswith(("\"", "'")):
            return "string"
        if text in {"true", "false"}:
            return "bool"
        if re.fullmatch(r"-?\d+", text):
            return "int"
        if re.fullmatch(r"-?\d+\.\d+", text):
            return "float"
    return "object"


def _find_ctor_call(module: Module, line: int, column: int):
    """Return (class_name, named_args dict, insert_line) or None."""
    for stmt in module.body:
        if isinstance(stmt, AssignStmt) and isinstance(stmt.value, Call):
            call = stmt.value
            sp = call.span or stmt.span
            if sp and sp.line == line:
                return _call_info(call, stmt.span.line if stmt.span else line)
        if isinstance(stmt, Call):
            sp = stmt.span
            if sp and sp.line == line:
                return _call_info(stmt, sp.line)
    for stmt in module.body:
        call = None
        insert_line = line
        if isinstance(stmt, AssignStmt) and isinstance(stmt.value, Call):
            call = stmt.value
            insert_line = stmt.span.line if stmt.span else line
        elif isinstance(stmt, Call):
            call = stmt
            insert_line = stmt.span.line if stmt.span else line
        if call is None:
            continue
        info = _call_info(call, insert_line)
        if info and call.span and call.span.line == line:
            return info
    return None


def _call_info(call: Call, insert_line: int):
    callee = call.callee
    if not isinstance(callee, Identifier):
        return None
    name = callee.name
    named: list[tuple[str, str]] = []
    for arg in call.args or []:
        if isinstance(arg, KeywordArg):
            named.append((arg.name, _infer_type(arg.value)))
    return name, named, insert_line


def _type_exists(module: Module, name: str) -> bool:
    from ..ast_nodes import ClassDef, DataDef, EntityDef, EnumDef, StructDef

    for stmt in module.body:
        if isinstance(stmt, (ClassDef, EntityDef, StructDef, DataDef, EnumDef)):
            if stmt.name == name:
                return True
    return False


def _render_class(name: str, params: list[tuple[str, str]]) -> str:
    field_lines = []
    ctor_params = []
    assigns = []
    for pname, ptype in params:
        field_lines.append(f"    public {ptype} {pname}")
        ctor_params.append(f"{ptype} {pname}")
        assigns.append(f"        this.{pname} = {pname}")
    fields = "\n".join(field_lines)
    param_list = ", ".join(ctor_params)
    body = "\n".join(assigns) if assigns else "        pass"
    return (
        f"class {name} {{\n"
        f"{fields}\n\n"
        f"    public constructor({param_list}) {{\n"
        f"{body}\n"
        f"    }}\n"
        f"}}\n\n"
    )


def plan_create_class(
    source_path: Path,
    *,
    line: int,
    column: int,
    source: str | None = None,
) -> RefactorPlan:
    plan = RefactorPlan(
        ok=False,
        catalog_id="create-class",
        title="Create class from constructor call",
        summary="Generate a class with fields and constructor from named arguments.",
        why="Unresolved constructor call — scaffold a typed host class for teaching.",
    )
    path = source_path.resolve()
    text = source if source is not None else path.read_text(encoding="utf-8")
    try:
        tree = parse_program(text)
    except TranspileError as exc:
        plan.conflicts.append(
            RefactorConflict(message=f"Cannot parse file: {exc}", file=str(path), line=line)
        )
        plan.message = str(exc)
        return plan.with_catalog()

    assert isinstance(tree, Module)
    info = _find_ctor_call(tree, line, column)
    if info is None:
        # Lexical fallback: ClassName(...named...)
        lines = text.splitlines()
        if 1 <= line <= len(lines):
            m = re.search(
                r"\b([A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)",
                lines[line - 1],
            )
            if m:
                cname = m.group(1)
                args_src = m.group(2)
                named = []
                for part in args_src.split(","):
                    part = part.strip()
                    if not part or "=" not in part:
                        continue
                    left, right = part.split("=", 1)
                    pname = left.strip()
                    r = right.strip()
                    if r.startswith(("\"", "'")):
                        ptype = "string"
                    elif r in {"true", "false"}:
                        ptype = "bool"
                    elif re.fullmatch(r"-?\d+", r):
                        ptype = "int"
                    elif re.fullmatch(r"-?\d+\.\d+", r):
                        ptype = "float"
                    else:
                        ptype = "object"
                    named.append((pname, ptype))
                info = (cname, named, line)
    if info is None:
        plan.conflicts.append(
            RefactorConflict(
                message="No constructor call with named arguments found at the cursor.",
                file=str(path),
                line=line,
                column=column,
            )
        )
        plan.message = "Place the cursor on an unresolved TypeName(...) call."
        return plan.with_catalog()

    class_name, named, insert_line = info
    if _type_exists(tree, class_name):
        plan.conflicts.append(
            RefactorConflict(
                message=f"Type '{class_name}' already exists — will not overwrite.",
                file=str(path),
                line=line,
            )
        )
        plan.message = f"Class '{class_name}' already declared."
        return plan.with_catalog()
    if not named:
        plan.conflicts.append(
            RefactorConflict(
                message="Create Class MVP requires named arguments (e.g. naam=\"Jaap\").",
                file=str(path),
                line=line,
            )
        )
        plan.message = "Use named constructor arguments."
        return plan.with_catalog()

    stub = _render_class(class_name, named)
    # Insert above the call line (1-based → column 1)
    plan.edits.append(
        RefactorEdit(
            file=str(path),
            line=insert_line,
            column=1,
            end_line=insert_line,
            end_column=1,
            new_text=stub,
            kind="insert",
            label=f"Insert class {class_name}",
        )
    )
    plan.ok = True
    plan.message = f"Create class {class_name} with {len(named)} constructor parameter(s)."
    return plan.with_catalog()
