"""Create a static method stub on a class from TypeName.method(...) calls."""
from __future__ import annotations

import re
from pathlib import Path

from ..ast_nodes import (
    AssignStmt,
    Call,
    ClassDef,
    ExprStmt,
    Identifier,
    KeywordArg,
    Literal,
    Member,
    Module,
)
from ..parse import parse_program
from ..transpiler import TranspileError
from .plan import RefactorConflict, RefactorEdit, RefactorPlan

_DEFAULT_RETURN = {
    "string": '""',
    "char": "'\\0'",
    "int": "0",
    "float": "0.0",
    "bool": "false",
}


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
    if isinstance(expr, Identifier):
        # Best-effort: PascalCase → object/type, else object
        if expr.name[:1].isupper():
            return "object"
    return "object"


def _param_name(index: int, typ: str, used: set[str]) -> str:
    bases = {
        "string": "text",
        "int": "n",
        "float": "x",
        "bool": "flag",
        "char": "ch",
    }
    base = bases.get(typ, "arg")
    candidate = base
    n = 0
    while candidate in used:
        n += 1
        candidate = f"{base}{n}"
    used.add(candidate)
    return candidate


def _find_static_call(module: Module, line: int):
    """Return (class_name, method_name, param_types, return_type, call_line) or None."""

    def from_call(call: Call, ret: str | None):
        callee = call.callee
        if not isinstance(callee, Member) or not isinstance(callee.object, Identifier):
            return None
        cls = callee.object.name
        if not cls[:1].isupper():
            return None
        method = callee.name
        params: list[str] = []
        used: set[str] = set()
        for arg in call.args or []:
            if isinstance(arg, KeywordArg):
                typ = _infer_type(arg.value)
                pname = arg.name if arg.name.isidentifier() else _param_name(len(params), typ, used)
                used.add(pname)
                params.append(f"{typ} {pname}")
            else:
                typ = _infer_type(arg)
                pname = _param_name(len(params), typ, used)
                params.append(f"{typ} {pname}")
        return cls, method, params, ret or "void", call.span.line if call.span else line

    for stmt in module.body:
        if isinstance(stmt, AssignStmt) and isinstance(stmt.value, Call):
            sp = stmt.value.span or stmt.span
            if sp and sp.line == line:
                ret = stmt.declare_type if stmt.declare_type and stmt.declare_type != "var" else None
                hit = from_call(stmt.value, ret)
                if hit:
                    return hit
        if isinstance(stmt, ExprStmt) and isinstance(stmt.expr, Call):
            sp = stmt.expr.span or stmt.span
            if sp and sp.line == line:
                hit = from_call(stmt.expr, None)
                if hit:
                    return hit
        if isinstance(stmt, Call):
            sp = stmt.span
            if sp and sp.line == line:
                hit = from_call(stmt, None)
                if hit:
                    return hit
    return None


def _class_insert_line(text: str, class_name: str) -> int | None:
    """1-based line to insert before the class closing `}`."""
    lines = text.splitlines()
    header = re.compile(rf"^\s*(?:(?:global|package|module)\s+)?(?:(?:closed|abstract)\s+)?class\s+{re.escape(class_name)}\b")
    start = None
    for i, raw in enumerate(lines):
        if header.match(raw):
            start = i
            break
    if start is None:
        return None
    depth = 0
    started = False
    for i in range(start, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return i + 1  # 1-based line of closing brace
    return None


def _render_method(method: str, params: list[str], return_type: str) -> str:
    sig = ", ".join(params)
    if return_type == "void" or not return_type:
        return (
            f"\n    public static void {method}({sig}) {{\n"
            f"    }}\n"
        )
    default = _DEFAULT_RETURN.get(return_type, "null")
    return (
        f"\n    public static {return_type} {method}({sig}) {{\n"
        f"        return {default}\n"
        f"    }}\n"
    )


def plan_create_static_method(
    source_path: Path,
    *,
    line: int,
    column: int,
    source: str | None = None,
    class_name: str | None = None,
    method_name: str | None = None,
) -> RefactorPlan:
    plan = RefactorPlan(
        ok=False,
        catalog_id="create-static-method",
        title="Create static method",
        summary="Insert a static method stub inferred from a TypeName.method(...) call.",
        why="Undefined static call — scaffold a matching method so students can keep typing.",
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
    hit = _find_static_call(tree, line)
    cls = (class_name or "").strip() or (hit[0] if hit else "")
    method = (method_name or "").strip() or (hit[1] if hit else "")
    params = list(hit[2]) if hit else []
    ret = hit[3] if hit else "void"

    if not cls or not method:
        # Lexical fallback: ClassName.method(...)
        lines = text.splitlines()
        line_text = lines[line - 1] if 1 <= line <= len(lines) else ""
        m = re.search(
            r"\b([A-Z][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_]\w*)\s*\(",
            line_text,
        )
        if m:
            cls = cls or m.group(1)
            method = method or m.group(2)

    if not cls or not method:
        plan.conflicts.append(
            RefactorConflict(
                message="No TypeName.method(...) call found at the cursor.",
                file=str(path),
                line=line,
                column=column,
            )
        )
        plan.message = "Place the cursor on an undefined static method call."
        return plan.with_catalog()

    class_node = next(
        (s for s in tree.body if isinstance(s, ClassDef) and s.name == cls),
        None,
    )
    if class_node is None:
        plan.conflicts.append(
            RefactorConflict(
                message=f"Class '{cls}' not found in this file.",
                file=str(path),
                line=line,
            )
        )
        plan.message = f"Class '{cls}' is not declared here."
        return plan.with_catalog()

    existing = {m.name for m in class_node.methods if not m.is_constructor}
    if method in existing:
        plan.conflicts.append(
            RefactorConflict(
                message=f"Method '{method}' already exists on class {cls}.",
                file=str(path),
                line=line,
            )
        )
        plan.message = f"'{method}' is already declared."
        return plan.with_catalog()

    insert_line = _class_insert_line(text, cls)
    if insert_line is None:
        plan.conflicts.append(
            RefactorConflict(
                message=f"Could not find closing brace of class {cls}.",
                file=str(path),
                line=line,
            )
        )
        plan.message = "Malformed class body."
        return plan.with_catalog()

    stub = _render_method(method, params, ret)
    plan.edits.append(
        RefactorEdit(
            file=str(path),
            line=insert_line,
            column=1,
            end_line=insert_line,
            end_column=1,
            new_text=stub,
            kind="insert",
            label=f"Insert static method {cls}.{method}",
        )
    )
    plan.ok = True
    plan.title = f"Create static method '{method}' on {cls}"
    plan.message = f"Add public static {ret} {method}({', '.join(params)}) to class {cls}."
    return plan.with_catalog()
