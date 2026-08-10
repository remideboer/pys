"""Create Class stub from unresolved type uses or constructor calls."""
from __future__ import annotations

import re
from pathlib import Path

from ..ast_nodes import (
    AssignStmt,
    Call,
    ClassDef,
    DataDef,
    EntityDef,
    EnumDef,
    FunctionDef,
    Identifier,
    KeywordArg,
    Literal,
    Module,
    StructDef,
)
from ..parse import parse_program
from ..transpiler import TranspileError
from .plan import RefactorConflict, RefactorEdit, RefactorPlan

_PASCAL = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")


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


def _find_ctor_call(module: Module, line: int, column: int):
    """Return (class_name, named_args, insert_line) or None."""
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


def _word_at_column(line_text: str, column: int) -> str:
    """Return the identifier touching 1-based ``column`` on ``line_text``."""
    if not line_text:
        return ""
    idx = max(min(column - 1, len(line_text) - 1), 0)
    if idx < len(line_text) and not (line_text[idx].isalnum() or line_text[idx] == "_"):
        # Prefer the token to the left of a caret sitting after the word.
        if idx > 0 and (line_text[idx - 1].isalnum() or line_text[idx - 1] == "_"):
            idx -= 1
        else:
            return ""
    start = idx
    while start > 0 and (line_text[start - 1].isalnum() or line_text[start - 1] == "_"):
        start -= 1
    end = idx + 1
    while end < len(line_text) and (line_text[end].isalnum() or line_text[end] == "_"):
        end += 1
    return line_text[start:end]


def _type_name_from_ast(module: Module, line: int) -> str | None:
    """Best-effort PascalCase type name used as an annotation on ``line``."""
    for stmt in module.body:
        if isinstance(stmt, AssignStmt):
            if stmt.span and stmt.span.line == line and stmt.declare_type:
                base = stmt.declare_type.split("<", 1)[0].strip()
                if base[:1].isupper():
                    return base
        if isinstance(stmt, FunctionDef):
            if stmt.span and stmt.span.line == line:
                if stmt.return_type and stmt.return_type[:1].isupper():
                    return stmt.return_type.split("<", 1)[0]
                for pt in stmt.param_types or []:
                    if pt[:1].isupper():
                        return pt.split("<", 1)[0]
        if isinstance(stmt, (ClassDef, EntityDef)):
            for field in stmt.fields or []:
                if field.span and field.span.line == line and field.type_name:
                    base = field.type_name.split("<", 1)[0].strip()
                    if base[:1].isupper():
                        return base
            for method in stmt.methods or []:
                if not method.span or method.span.line != line:
                    continue
                if method.return_type and method.return_type[:1].isupper():
                    return method.return_type.split("<", 1)[0]
                for pt in method.param_types or []:
                    if pt[:1].isupper():
                        return pt.split("<", 1)[0]
        if isinstance(stmt, (StructDef, DataDef)):
            for field in stmt.fields or []:
                if field.span and field.span.line == line and field.type_name:
                    base = field.type_name.split("<", 1)[0].strip()
                    if base[:1].isupper():
                        return base
    return None


def _enclosing_toplevel_insert_line(module: Module, line: int) -> int:
    """Insert before the top-level stmt that contains ``line`` (1-based)."""
    chosen = 1
    for stmt in module.body:
        sp = getattr(stmt, "span", None)
        if sp is None:
            continue
        if sp.line <= line:
            chosen = sp.line
        else:
            break
    return chosen


def _type_exists(module: Module, name: str) -> bool:
    for stmt in module.body:
        if isinstance(stmt, (ClassDef, EntityDef, StructDef, DataDef, EnumDef)):
            if stmt.name == name:
                return True
    return False


def _render_class(name: str, params: list[tuple[str, str]]) -> str:
    if not params:
        return f"class {name} {{\n}}\n\n"
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
    type_name: str | None = None,
) -> RefactorPlan:
    plan = RefactorPlan(
        ok=False,
        catalog_id="create-class",
        title="Create missing class",
        summary="Generate a class stub for an unresolved type or constructor call.",
        why="Unknown type — scaffold a typed host class for teaching.",
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
    lines = text.splitlines()
    line_text = lines[line - 1] if 1 <= line <= len(lines) else ""

    hinted = (type_name or "").strip()
    if hinted and not hinted.isidentifier():
        hinted = ""

    info = None if hinted else _find_ctor_call(tree, line, column)
    if info is None and not hinted:
        # Lexical fallback: ClassName(...named...)
        m = re.search(
            r"\b([A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)",
            line_text,
        )
        if m:
            cname = m.group(1)
            args_src = m.group(2)
            named_lex: list[tuple[str, str]] = []
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
                named_lex.append((pname, ptype))
            info = (cname, named_lex, line)

    class_name: str | None = None
    named: list[tuple[str, str]] = []
    insert_line = line

    if hinted:
        class_name = hinted
        insert_line = _enclosing_toplevel_insert_line(tree, line) if line else 1
        # Prefer insert before first top-level type that mentions the name on this line.
        if 1 <= line <= len(lines) and hinted in line_text:
            insert_line = _enclosing_toplevel_insert_line(tree, line)
        elif hinted:
            # Scan file for a use site of the hinted name to place the stub above it.
            for idx, raw in enumerate(lines, start=1):
                if re.search(rf"\b{re.escape(hinted)}\b", raw):
                    insert_line = _enclosing_toplevel_insert_line(tree, idx)
                    break
            else:
                insert_line = 1
    elif info is not None:
        class_name, named, insert_line = info
        # Bare TypeName(...) without named args → empty stub (same as type-site).
    else:
        # Annotation / field / param site: resolve PascalCase type near the cursor.
        word = _word_at_column(line_text, column)
        if word[:1].isupper() and word.isidentifier():
            class_name = word
        else:
            class_name = _type_name_from_ast(tree, line)
            if class_name is None:
                # Last resort: first PascalCase token on the line (diagnostic highlight).
                m = _PASCAL.search(line_text)
                if m:
                    class_name = m.group(1)
        if class_name:
            insert_line = _enclosing_toplevel_insert_line(tree, line)

    if not class_name:
        plan.conflicts.append(
            RefactorConflict(
                message="No unresolved type or constructor call found at the cursor.",
                file=str(path),
                line=line,
                column=column,
            )
        )
        plan.message = "Place the cursor on an unknown type name or TypeName(...) call."
        return plan.with_catalog()

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

    stub = _render_class(class_name, named)
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
    plan.title = f"Create class '{class_name}'"
    if named:
        plan.message = f"Create class {class_name} with {len(named)} constructor parameter(s)."
    else:
        plan.message = f"Create empty class {class_name}."
        plan.summary = f"Insert `class {class_name} {{ }}` for the unresolved type."
    return plan.with_catalog()
