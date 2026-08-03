"""Inline Variable / Inline Function refactors."""
from __future__ import annotations

import re
from pathlib import Path

from ..ast_nodes import AssignStmt, FunctionDef
from ..parse import parse_program
from .catalog import catalog_entry
from .plan import RefactorConflict, RefactorEdit, RefactorPlan
from .refs import build_index, resolve_at


def plan_inline_variable(
    source_path: Path,
    *,
    line: int,
    column: int,
) -> RefactorPlan:
    meta = catalog_entry("inline-variable")
    plan = RefactorPlan(
        ok=False,
        catalog_id="inline-variable",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    path = source_path.resolve()
    index = build_index(path)
    decl = resolve_at(index, path, line, column)
    if decl is None or decl.kind != "var":
        plan.conflicts.append(
            RefactorConflict(message="Cursor is not on a local / variable declaration.")
        )
        return plan
    sites = index.sites_for(decl)
    decl_sites = [s for s in sites if s.kind == "decl"]
    use_sites = [s for s in sites if s.kind == "use"]
    if len(decl_sites) != 1:
        plan.conflicts.append(RefactorConflict(message="Could not locate a single declaration site."))
        return plan
    # Find initializer text from AST
    mod = index.modules.get(decl.file)
    source = index.sources.get(decl.file, "")
    init = None
    decl_stmt_line = decl.line
    if mod is not None:
        for stmt in _iter_assigns(mod):
            if stmt.name == decl.name and stmt.declare_type is not None:
                if stmt.span and stmt.span.line == decl.line or True:
                    # extract RHS from source line
                    lines = source.splitlines()
                    if 0 <= decl.line - 1 < len(lines):
                        m = re.search(r"=\s*(.*)$", lines[decl.line - 1])
                        if m:
                            init = m.group(1).strip()
                            decl_stmt_line = decl.line
                    break
    if not init:
        plan.conflicts.append(RefactorConflict(message="No single initializer found to inline."))
        return plan
    # Multiple assignments to same var (extra uses that are assign targets) — count assign uses
    assign_uses = 0
    for s in use_sites:
        lines = source.splitlines()
        if 0 <= s.line - 1 < len(lines):
            frag = lines[s.line - 1]
            if re.search(rf"\b{re.escape(decl.name)}\s*=", frag) and "==" not in frag:
                assign_uses += 1
    if assign_uses:
        plan.conflicts.append(
            RefactorConflict(
                message="Variable is assigned more than once; Inline Variable requires a single assignment.",
            )
        )
        return plan
    for s in use_sites:
        plan.edits.append(
            RefactorEdit(
                file=s.file,
                line=s.line,
                column=s.column,
                end_line=s.line,
                end_column=s.end_column,
                new_text=init,
                kind="replace",
                label="inline use",
            )
        )
    # Delete declaration line
    ds = decl_sites[0]
    plan.edits.append(
        RefactorEdit(
            file=ds.file,
            line=decl_stmt_line,
            column=1,
            end_line=decl_stmt_line,
            end_column=len(source.splitlines()[decl_stmt_line - 1]) + 1,
            new_text="",
            kind="replace",
            label="remove declaration",
        )
    )
    plan.ok = True
    return plan


def _iter_assigns(mod):
    from ..ast_nodes import Block, ClassDef, FunctionDef, IfStmt

    def walk(stmts):
        for s in stmts or []:
            if isinstance(s, AssignStmt):
                yield s
            body = getattr(s, "body", None)
            if isinstance(body, Block):
                yield from walk(body.statements)
            if isinstance(s, FunctionDef) and s.body:
                yield from walk(s.body.statements)
            if isinstance(s, ClassDef):
                for m in s.methods or []:
                    if m.body:
                        yield from walk(m.body.statements)
            if isinstance(s, IfStmt):
                if s.then_body:
                    yield from walk(s.then_body.statements)
                if isinstance(s.else_body, Block):
                    yield from walk(s.else_body.statements)

    yield from walk(mod.body)


def plan_inline_function(
    source_path: Path,
    *,
    line: int,
    column: int,
) -> RefactorPlan:
    meta = catalog_entry("inline-function")
    plan = RefactorPlan(
        ok=False,
        catalog_id="inline-function",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    path = source_path.resolve()
    index = build_index(path)
    decl = resolve_at(index, path, line, column)
    if decl is None or decl.kind != "function":
        plan.conflicts.append(RefactorConflict(message="Cursor is not on a function declaration."))
        return plan
    if decl.kind == "function":
        # Exported and used elsewhere: still allow inline of body into call sites in graph
        pass
    sites = index.sites_for(decl)
    use_sites = [s for s in sites if s.kind in {"use", "import"}]
    decl_sites = [s for s in sites if s.kind == "decl"]
    mod = index.modules.get(decl.file)
    source = index.sources.get(decl.file, "")
    body_text = None
    fn: FunctionDef | None = None
    if mod:
        for stmt in mod.body:
            if isinstance(stmt, FunctionDef) and stmt.name == decl.name:
                fn = stmt
                break
    if fn is None or fn.body is None:
        plan.conflicts.append(RefactorConflict(message="Function body not found."))
        return plan
    if fn.params:
        plan.conflicts.append(
            RefactorConflict(
                message="Inline Function currently supports zero-parameter functions only.",
            )
        )
        return plan
    # Single return expr or single statement print — take body source between braces
    lines = source.splitlines()
    # Find function line and matching closing brace (simple scan)
    start = decl.line - 1
    depth = 0
    body_start = None
    body_end = None
    for i in range(start, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                if depth == 1:
                    body_start = i
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    body_end = i
                    break
        if body_end is not None:
            break
    if body_start is None or body_end is None:
        plan.conflicts.append(RefactorConflict(message="Could not locate function body braces."))
        return plan
    inner = lines[body_start + 1 : body_end]
    body_text = "\n".join(l.strip() for l in inner if l.strip())
    # Only inline trivial single-return
    m = re.match(r"^return\s+(.+)$", body_text.strip())
    if not m:
        plan.conflicts.append(
            RefactorConflict(
                message="Inline Function supports a single `return expr` body for DoD.",
            )
        )
        return plan
    expr = m.group(1).strip()
    for s in use_sites:
        if s.kind == "import":
            plan.conflicts.append(
                RefactorConflict(
                    message="Function is imported elsewhere; remove imports after inlining call sites, or use Safe Delete.",
                    file=s.file,
                    line=s.line,
                    column=s.column,
                    soft=True,
                )
            )
            continue
        # Replace `name()` call — expand site to include ()
        plan.edits.append(
            RefactorEdit(
                file=s.file,
                line=s.line,
                column=s.column,
                end_line=s.line,
                end_column=s.end_column,
                new_text=f"({expr})",
                kind="replace",
                label="inline call name",
                optional=False,
            )
        )
        # Also need to remove () after name — handled if we extend end_column
        # Peek source for () 
        flines = Path(s.file).read_text(encoding="utf-8").splitlines()
        frag = flines[s.line - 1][s.end_column - 1 : s.end_column + 2]
        if frag.startswith("()"):
            plan.edits[-1].end_column = s.end_column + 2
            plan.edits[-1].new_text = f"({expr})"
    # Delete function definition (from decl line through closing brace)
    if decl_sites:
        plan.edits.append(
            RefactorEdit(
                file=decl.file,
                line=body_start + 1,
                column=1,
                end_line=body_end + 1,
                end_column=len(lines[body_end]) + 1,
                new_text="",
                kind="replace",
                label="remove function",
            )
        )
    plan.ok = True
    return plan
