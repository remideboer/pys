"""IDE completions: in-scope identifiers and accessible members (near → far)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ast_nodes import (
    ArrayDecl,
    AssignStmt,
    AtomicDecl,
    Block,
    Call,
    ClassDef,
    DataDef,
    EntityDef,
    EnumDef,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    ImportStmt,
    LambdaExpr,
    Module,
    SharedDecl,
    Span,
    StructDef,
    SwitchStmt,
    WhileStmt,
)
from .parse import parse_program
from .transpiler import TranspileError
from .workspace import resolve_workspace_path, workspace_root_from_env

# VS Code CompletionItemKind-ish strings for the extension to map.
_KIND_MAP = {
    "var": "variable",
    "param": "variable",
    "foreach": "variable",
    "field": "field",
    "method": "method",
    "function": "function",
    "class": "class",
    "entity": "class",
    "struct": "struct",
    "data": "struct",
    "enum": "enum",
    "enum_member": "enumMember",
    "import": "module",
    "type": "class",
    "keyword": "keyword",
}


@dataclass
class _Binding:
    name: str
    kind: str
    type_name: str = ""
    depth: int = 0  # 0 = innermost
    detail: str = ""


@dataclass
class _TypeInfo:
    fields: list[tuple[str, str, str]] = field(default_factory=list)  # name, type, access
    methods: list[tuple[str, str, str, list[str]]] = field(
        default_factory=list
    )  # name, return, access, params
    parent: str | None = None


def _line_col_before(source: str, line: int, column: int) -> tuple[str, int, int]:
    """Source with a dummy IDENT after a trailing `.` so `rm.` parses as Member."""
    lines = source.splitlines(keepends=True)
    if not lines:
        return source, line, column
    idx = max(line - 1, 0)
    if idx >= len(lines):
        idx = len(lines) - 1
        line = idx + 1
    raw = lines[idx]
    # column is 1-based into the logical line (without worrying about \r)
    bare = raw.rstrip("\r\n")
    ending = raw[len(bare) :]
    col0 = max(min(column - 1, len(bare)), 0)
    prefix = bare[:col0]
    suffix = bare[col0:]
    if prefix.rstrip().endswith("."):
        # Insert dummy member so `rm.` / `rm.s` mid-type becomes valid Member.
        insert = "_pys_cc"
        if suffix and suffix[0].isalnum():
            # Completing mid-identifier after dot: keep typed prefix as part of dummy? 
            # Use full remainder as continuing the dummy name.
            bare = prefix + insert
        else:
            bare = prefix + insert + suffix
        lines[idx] = bare + ending
        return "".join(lines), line, col0 + 1 + len(insert)
    return source, line, column


def _collect_types(module: Module) -> dict[str, _TypeInfo]:
    types: dict[str, _TypeInfo] = {}
    for stmt in module.body:
        if isinstance(stmt, ClassDef):
            info = _TypeInfo(parent=stmt.parent or None)
            for f in stmt.fields or []:
                info.fields.append((f.name, f.type_name or "", f.access or "module"))
            for m in stmt.methods or []:
                if m.name == "constructor" or m.is_constructor:
                    info.methods.append(
                        ("constructor", "", m.access or "public", list(m.params))
                    )
                else:
                    info.methods.append(
                        (
                            m.name,
                            m.return_type or "void",
                            m.access or "module",
                            list(m.params),
                        )
                    )
            types[stmt.name] = info
        elif isinstance(stmt, EntityDef):
            info = _TypeInfo(parent=stmt.parent or None)
            for f in stmt.fields or []:
                info.fields.append((f.name, f.type_name or "", f.access or "module"))
            for m in stmt.methods or []:
                if m.name == "constructor" or m.is_constructor:
                    info.methods.append(
                        ("constructor", "", m.access or "public", list(m.params))
                    )
                else:
                    info.methods.append(
                        (
                            m.name,
                            m.return_type or "void",
                            m.access or "module",
                            list(m.params),
                        )
                    )
            types[stmt.name] = info
        elif isinstance(stmt, (StructDef, DataDef)):
            info = _TypeInfo()
            for f in stmt.fields or []:
                info.fields.append((f.name, f.type_name or "", "public"))
            types[stmt.name] = info
        elif isinstance(stmt, EnumDef):
            info = _TypeInfo()
            for mem in stmt.members or []:
                info.fields.append((mem.name, stmt.name, "public"))
            types[stmt.name] = info
    return types


def _accessible(access: str, *, inside_type: bool) -> bool:
    if inside_type:
        return True
    return (access or "module") in {"public", "module", ""}


def _flatten_members(
    types: dict[str, _TypeInfo], type_name: str, *, inside_type: bool
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    current: str | None = type_name
    walked: set[str] = set()
    while current and current not in walked:
        walked.add(current)
        info = types.get(current)
        if info is None:
            break
        for name, typ, access in info.fields:
            if name in seen or not _accessible(access, inside_type=inside_type):
                continue
            seen.add(name)
            items.append(
                {
                    "label": name,
                    "kind": "field",
                    "detail": typ or access,
                    "insertText": name,
                    "sortText": f"2_{name}",
                }
            )
        for name, ret, access, params in info.methods:
            if name in seen or name == "constructor":
                continue
            if not _accessible(access, inside_type=inside_type):
                continue
            seen.add(name)
            sig = f"{name}({', '.join(params)})"
            if ret and ret != "void":
                sig = f"{sig}: {ret}"
            items.append(
                {
                    "label": name,
                    "kind": "method",
                    "detail": sig,
                    "insertText": name,
                    "sortText": f"2_{name}",
                }
            )
        current = info.parent
    return items


def _env_type(bindings: list[_Binding], name: str) -> str | None:
    for b in bindings:
        if b.name == name and b.type_name:
            return b.type_name
    return None


@dataclass
class _ScopeWalk:
    line: int
    column: int
    bindings: list[_Binding] = field(default_factory=list)
    enclosing_type: str | None = None
    var_types: dict[str, str] = field(default_factory=dict)

    def add(self, name: str, kind: str, depth: int, type_name: str = "", detail: str = "") -> None:
        self.bindings.append(
            _Binding(name=name, kind=kind, type_name=type_name, depth=depth, detail=detail)
        )
        if type_name:
            self.var_types[name] = type_name


def _in_span(span: Span | None, line: int, column: int) -> bool:
    if span is None:
        return False
    end_line = span.end_line if span.end_line is not None else span.line
    end_col = span.end_column if span.end_column is not None else 10**9
    if line < span.line or line > end_line:
        return False
    if line == span.line and column < span.column:
        return False
    if line == end_line and span.end_column is not None and column > end_col:
        return False
    return True


def _walk_block(block: Block | None, walk: _ScopeWalk, depth: int) -> None:
    if block is None:
        return
    for stmt in block.statements or []:
        _walk_stmt(stmt, walk, depth)


def _walk_stmt(stmt: Any, walk: _ScopeWalk, depth: int) -> None:
    if isinstance(stmt, ImportStmt):
        names = []
        if stmt.alias:
            names.append(stmt.alias)
        elif stmt.names:
            names.extend(stmt.names)
        elif stmt.name:
            names.append(stmt.name)
        elif stmt.module and stmt.kind == "module":
            names.append(stmt.module.split(".")[0])
        for n in names:
            walk.add(n, "import", depth)
        return
    if isinstance(stmt, FunctionDef):
        walk.add(stmt.name, "function", depth, detail=stmt.return_type or "")
        if _in_span(stmt.span, walk.line, walk.column) or _block_contains(
            stmt.body, walk.line, walk.column
        ):
            for i, pname in enumerate(stmt.params):
                pt = stmt.param_types[i] if i < len(stmt.param_types) else ""
                walk.add(pname, "param", depth + 1, type_name=pt)
            _walk_block(stmt.body, walk, depth + 1)
        return
    if isinstance(stmt, (ClassDef, EntityDef)):
        kind = "class" if isinstance(stmt, ClassDef) else "entity"
        walk.add(stmt.name, kind, depth)
        inside = _in_span(stmt.span, walk.line, walk.column) or any(
            _in_span(m.span, walk.line, walk.column)
            or _block_contains(m.body, walk.line, walk.column)
            for m in (stmt.methods or [])
        )
        if inside:
            walk.enclosing_type = stmt.name
            for f in stmt.fields or []:
                walk.add(f.name, "field", depth + 1, type_name=f.type_name or "")
            for m in stmt.methods or []:
                walk.add(m.name, "method", depth + 1, detail=m.return_type or "")
                if _in_span(m.span, walk.line, walk.column) or _block_contains(
                    m.body, walk.line, walk.column
                ):
                    for i, pname in enumerate(m.params):
                        pt = m.param_types[i] if i < len(m.param_types) else ""
                        walk.add(pname, "param", depth + 2, type_name=pt)
                    _walk_block(m.body, walk, depth + 2)
        return
    if isinstance(stmt, (StructDef, DataDef, EnumDef)):
        k = (
            "struct"
            if isinstance(stmt, StructDef)
            else ("data" if isinstance(stmt, DataDef) else "enum")
        )
        walk.add(stmt.name, k, depth)
        return
    if isinstance(stmt, AssignStmt) and stmt.declare_type is not None:
        t = stmt.declare_type if stmt.declare_type not in {"var", "const", "fix"} else ""
        walk.add(stmt.name, "var", depth, type_name=t)
        return
    if isinstance(stmt, (ArrayDecl, SharedDecl, AtomicDecl)):
        t = getattr(stmt, "elem_type", "") or getattr(stmt, "type_name", "") or ""
        walk.add(stmt.name, "var", depth, type_name=t)
        return
    if isinstance(stmt, ForEachStmt):
        if _in_span(stmt.span, walk.line, walk.column) or _block_contains(
            stmt.body, walk.line, walk.column
        ):
            walk.add(stmt.var, "foreach", depth + 1, type_name=stmt.var_type or "")
            _walk_block(stmt.body, walk, depth + 1)
        return
    if isinstance(stmt, ForRangeStmt):
        if _in_span(stmt.span, walk.line, walk.column) or _block_contains(
            stmt.body, walk.line, walk.column
        ):
            walk.add(stmt.var, "foreach", depth + 1, type_name="int")
            _walk_block(stmt.body, walk, depth + 1)
        return
    if isinstance(stmt, WhileStmt):
        _walk_block(stmt.body, walk, depth + 1)
        return
    if isinstance(stmt, IfStmt):
        _walk_block(stmt.then_body, walk, depth + 1)
        else_body = getattr(stmt, "else_body", None)
        # else-if chains nest as IfStmt in else_body
        while isinstance(else_body, IfStmt):
            _walk_block(else_body.then_body, walk, depth + 1)
            else_body = getattr(else_body, "else_body", None)
        if isinstance(else_body, Block):
            _walk_block(else_body, walk, depth + 1)
        return
    if isinstance(stmt, SwitchStmt):
        for arm in stmt.arms or []:
            _walk_block(getattr(arm, "body", None), walk, depth + 1)
        return


def _block_contains(block: Block | None, line: int, column: int) -> bool:
    if block is None:
        return False
    if _in_span(block.span, line, column):
        return True
    for stmt in block.statements or []:
        if _in_span(getattr(stmt, "span", None), line, column):
            return True
        if isinstance(stmt, IfStmt):
            if _block_contains(getattr(stmt, "then_body", None), line, column):
                return True
            else_body = getattr(stmt, "else_body", None)
            while isinstance(else_body, IfStmt):
                if _block_contains(else_body.then_body, line, column):
                    return True
                else_body = getattr(else_body, "else_body", None)
            if _block_contains(else_body if isinstance(else_body, Block) else None, line, column):
                return True
        if isinstance(stmt, (ForEachStmt, ForRangeStmt, WhileStmt, FunctionDef)):
            if _block_contains(getattr(stmt, "body", None), line, column):
                return True
    return False


def _dot_receiver(source: str, line: int, column: int) -> str | None:
    """If cursor is in/after a member access, return the receiver identifier."""
    lines = source.splitlines()
    if line < 1 or line > len(lines):
        return None
    text = lines[line - 1]
    col0 = max(column - 1, 0)
    left = text[:col0]
    # Strip partial member name after the last dot.
    if "." not in left:
        return None
    before, _after = left.rsplit(".", 1)
    recv = before.rstrip()
    # Take trailing identifier (rm / this / Name)
    i = len(recv) - 1
    while i >= 0 and (recv[i].isalnum() or recv[i] == "_"):
        i -= 1
    name = recv[i + 1 :]
    return name or None


_KEYWORDS = [
    "if",
    "else",
    "elseif",
    "loop",
    "while",
    "for",
    "function",
    "return",
    "class",
    "struct",
    "data",
    "entity",
    "trait",
    "uses",
    "requires",
    "public",
    "private",
    "protected",
    "fix",
    "const",
    "print",
    "this",
    "super",
    "new",
    "null",
    "true",
    "false",
]


def completions_at(
    source: str,
    *,
    line: int,
    column: int,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Return completion items at 1-based line/column in ``source``."""
    patched, _pl, _pc = _line_col_before(source, line, column)
    try:
        tree = parse_program(patched)
    except TranspileError:
        try:
            tree = parse_program(source)
        except TranspileError as exc:
            return {
                "ok": False,
                "message": str(exc),
                "items": _keyword_items(),
            }

    assert isinstance(tree, Module)
    types = _collect_types(tree)
    walk = _ScopeWalk(line=line, column=column)
    for stmt in tree.body:
        _walk_stmt(stmt, walk, depth=0)

    receiver = _dot_receiver(source, line, column)
    items: list[dict[str, Any]] = []

    if receiver:
        type_name: str | None = None
        if receiver == "this" and walk.enclosing_type:
            type_name = walk.enclosing_type
        else:
            type_name = walk.var_types.get(receiver) or _env_type(walk.bindings, receiver)
            if type_name is None and receiver in types:
                # TypeName. — enum/static-ish: show type members
                type_name = receiver
        if type_name:
            inside = walk.enclosing_type == type_name
            items.extend(_flatten_members(types, type_name, inside_type=inside))
            return {"ok": True, "items": items, "mode": "members", "type": type_name}

    # In-scope identifiers (near → far): sort by depth ascending then name
    seen: set[str] = set()
    ranked = sorted(walk.bindings, key=lambda b: (b.depth, b.name))
    for b in ranked:
        if b.name in seen:
            continue
        seen.add(b.name)
        sort_prefix = {
            "param": "1",
            "foreach": "0",
            "var": "0",
            "field": "2",
            "method": "2",
            "function": "3",
            "class": "4",
            "entity": "4",
            "struct": "4",
            "data": "4",
            "enum": "4",
            "import": "5",
        }.get(b.kind, "6")
        items.append(
            {
                "label": b.name,
                "kind": _KIND_MAP.get(b.kind, "variable"),
                "detail": b.type_name or b.detail or b.kind,
                "insertText": b.name,
                "sortText": f"{sort_prefix}_{b.depth:02d}_{b.name}",
            }
        )

    # Known types not already listed
    for tname in sorted(types):
        if tname in seen:
            continue
        items.append(
            {
                "label": tname,
                "kind": "class",
                "detail": "type",
                "insertText": tname,
                "sortText": f"4_{tname}",
            }
        )

    items.extend(_keyword_items(exclude=seen))
    _ = source_path  # reserved for multi-file later
    return {"ok": True, "items": items, "mode": "scope"}


def _keyword_items(*, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    exclude = exclude or set()
    out = []
    for kw in _KEYWORDS:
        if kw in exclude:
            continue
        out.append(
            {
                "label": kw,
                "kind": "keyword",
                "detail": "keyword",
                "insertText": kw,
                "sortText": f"9_{kw}",
            }
        )
    return out


def completions_for_file(
    source_path: Path,
    *,
    line: int,
    column: int,
    source: str | None = None,
) -> dict[str, Any]:
    workspace_root = workspace_root_from_env()
    if workspace_root is not None:
        contained = resolve_workspace_path(source_path, workspace_root)
        if contained is None:
            return {
                "ok": False,
                "message": f"Source path resolves outside the workspace: {source_path}",
                "items": [],
            }
        source_path = contained
    else:
        source_path = source_path.resolve()
    if source is None:
        source = source_path.read_text(encoding="utf-8")
    return completions_at(source, line=line, column=column, source_path=source_path)
