"""Binding-aware reference index for Find Usages and refactoring."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ast_nodes import (
    ArrayDecl,
    AssignStmt,
    AtomicDecl,
    AugAssignStmt,
    BinaryOp,
    Block,
    Call,
    ClassDef,
    DataDef,
    EntityDef,
    EnumDef,
    Expr,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    ImportStmt,
    Index,
    InterpolatedString,
    LambdaExpr,
    Member,
    Module,
    PrintStmt,
    ReturnStmt,
    ResultPattern,
    SharedDecl,
    Span,
    StructDef,
    SwitchExpr,
    SwitchStmt,
    UnaryOp,
    WhileStmt,
)
from ..imports import discover_imported_modules
from ..lex import KEYWORDS, tokenize
from ..parse import parse_program
from ..workspace import resolve_workspace_path, workspace_root_from_env

# Skip type-name uses for builtins / width aliases (not user type bindings).
_PRIMITIVE_TYPES = frozenset(
    {
        "int",
        "float",
        "char",
        "string",
        "bool",
        "void",
        "object",
        "byte",
        "short",
        "long",
        "ubyte",
        "ushort",
        "uint",
        "ulong",
    }
)

_HOLE_RE = re.compile(r"\{([^{}]+)\}")
_BASE_TYPE_RE = re.compile(
    r"^(?:nullable|list|dict|set|array)<\s*([A-Za-z_]\w*)",
    re.IGNORECASE,
)
_IDENT_TYPE_RE = re.compile(r"^([A-Za-z_]\w*)")


@dataclass(frozen=True)
class DeclKey:
    file: str
    line: int
    column: int
    name: str
    kind: str  # function|var|param|field|method|class|struct|enum|import|foreach|…


@dataclass(frozen=True)
class RefSite:
    file: str
    line: int
    column: int
    end_column: int
    kind: str  # decl|use|import
    decl: DeclKey


@dataclass
class _Scope:
    bindings: dict[str, DeclKey] = field(default_factory=dict)
    # Local / param binding → nominal type name (for Member resolution).
    var_types: dict[str, str] = field(default_factory=dict)


@dataclass
class RefIndex:
    """All sites keyed by DeclKey; also map (file,line,col) → DeclKey for cursor resolve."""

    sites_by_decl: dict[DeclKey, list[RefSite]] = field(default_factory=dict)
    at_position: dict[tuple[str, int, int], DeclKey] = field(default_factory=dict)
    modules: dict[str, Module] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    # (type_name, member_name) → field/method DeclKey
    type_members: dict[tuple[str, str], DeclKey] = field(default_factory=dict)
    # child type → parent type (inherits)
    type_parents: dict[str, str] = field(default_factory=dict)
    # Stack of enclosing class/entity names while walking members.
    enclosing_types: list[str] = field(default_factory=list)

    def sites_for(self, decl: DeclKey) -> list[RefSite]:
        return list(self.sites_by_decl.get(decl, []))

def _file_key(path: Path) -> str:
    return str(path.resolve())


def _span_end_col(span: Span | None, name: str) -> int:
    if span is None:
        return 1 + len(name)
    if span.end_column is not None:
        return span.end_column
    return span.column + max(len(name), 1)


def _name_span(node: Any, name: str) -> Span:
    ns = getattr(node, "name_span", None)
    if isinstance(ns, Span):
        return ns
    sp = getattr(node, "span", None)
    if isinstance(sp, Span):
        # Heuristic: declaration keyword span — search token on same line later.
        return Span(sp.line, sp.column, sp.line, sp.column + max(len(name), 1))
    return Span(1, 1, 1, 1 + len(name))


def _recover_name_span(source: str, approx: Span, name: str) -> Span:
    """Find IDENT ``name`` on/near ``approx.line`` when name_span was missing."""
    try:
        tokens = tokenize(source)
    except Exception:
        return approx
    for tok in tokens:
        if tok.line < approx.line:
            continue
        if tok.line > approx.line + 2:
            break
        if tok.text == name:
            return Span(tok.line, tok.column, tok.line, tok.column + len(tok.text))
    return approx


def _add_site(index: RefIndex, site: RefSite) -> None:
    index.sites_by_decl.setdefault(site.decl, []).append(site)
    index.at_position[(site.file, site.line, site.column)] = site.decl


def _declare(
    index: RefIndex,
    scopes: list[_Scope],
    *,
    file: str,
    name: str,
    span: Span,
    kind: str,
    site_kind: str = "decl",
) -> DeclKey:
    decl = DeclKey(file=file, line=span.line, column=span.column, name=name, kind=kind)
    scopes[-1].bindings[name] = decl
    end_col = _span_end_col(span, name)
    _add_site(
        index,
        RefSite(
            file=file,
            line=span.line,
            column=span.column,
            end_column=end_col,
            kind=site_kind,
            decl=decl,
        ),
    )
    return decl


def _lookup(scopes: list[_Scope], name: str) -> DeclKey | None:
    for scope in reversed(scopes):
        if name in scope.bindings:
            return scope.bindings[name]
    return None


def _use_ident(index: RefIndex, scopes: list[_Scope], file: str, expr: Identifier) -> None:
    if expr.name in {"self", "this"} or expr.name in KEYWORDS:
        return
    decl = _lookup(scopes, expr.name)
    if decl is None:
        return
    sp = expr.span or Span(1, 1)
    end_col = _span_end_col(sp, expr.name)
    _add_site(
        index,
        RefSite(
            file=file,
            line=sp.line,
            column=sp.column,
            end_column=end_col,
            kind="use",
            decl=decl,
        ),
    )


def _base_type_name(type_str: str | None) -> str | None:
    if not type_str:
        return None
    text = type_str.strip()
    if not text:
        return None
    m = _BASE_TYPE_RE.match(text)
    if m:
        return m.group(1)
    # Strip array suffix: int[], Rekenmachine[]
    if "[" in text:
        text = text.split("[", 1)[0].strip()
    m2 = _IDENT_TYPE_RE.match(text)
    return m2.group(1) if m2 else None


def _lookup_var_type(scopes: list[_Scope], name: str) -> str | None:
    for scope in reversed(scopes):
        if name in scope.var_types:
            return scope.var_types[name]
    return None


def _lookup_member(index: RefIndex, type_name: str, attr: str) -> DeclKey | None:
    seen: set[str] = set()
    cur: str | None = type_name
    while cur and cur not in seen:
        seen.add(cur)
        hit = index.type_members.get((cur, attr))
        if hit is not None:
            return hit
        cur = index.type_parents.get(cur)
    return None


def _receiver_type(index: RefIndex, scopes: list[_Scope], obj: Expr | None) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, Identifier):
        if obj.name in {"self", "this"}:
            return index.enclosing_types[-1] if index.enclosing_types else None
        typed = _lookup_var_type(scopes, obj.name)
        if typed:
            return typed
        # Bare type name used as value (rare); Call path handles ctors.
        decl = _lookup(scopes, obj.name)
        if decl is not None and decl.kind in {"class", "entity", "struct", "data", "enum"}:
            return obj.name
        return None
    if isinstance(obj, Call) and isinstance(obj.callee, Identifier):
        name = obj.callee.name
        decl = _lookup(scopes, name)
        if decl is not None and decl.kind in {"class", "entity", "struct", "data"}:
            return name
        if name[:1].isupper():
            return name
    if isinstance(obj, Member):
        # Chained a.b.c — only resolve when b is a field with a known type later; MVP skip.
        return None
    return None


def _member_name_span(source: str, approx: Span, name: str) -> Span:
    """Prefer the identifier after '.' on the same line as ``approx``."""
    mspan = _recover_name_span(source, Span(approx.line, approx.column), name)
    try:
        line = source.splitlines()[approx.line - 1]
        search_from = max(approx.column - 1, 0)
        dot = line.find(".", search_from)
        if dot < 0:
            dot = line.rfind(".", 0, min(len(line), search_from + 80))
        if dot >= 0:
            rest = line[dot + 1 :]
            if rest.startswith(name) and (len(rest) == len(name) or not rest[len(name)].isalnum() and rest[len(name)] != "_"):
                col = dot + 2
                return Span(approx.line, col, approx.line, col + len(name))
    except Exception:
        pass
    return mspan


def _add_use_site(
    index: RefIndex,
    *,
    file: str,
    span: Span,
    name: str,
    decl: DeclKey,
) -> None:
    _add_site(
        index,
        RefSite(
            file=file,
            line=span.line,
            column=span.column,
            end_column=_span_end_col(span, name),
            kind="use",
            decl=decl,
        ),
    )


def _use_type_name(
    index: RefIndex,
    scopes: list[_Scope],
    file: str,
    type_str: str | None,
    approx: Span,
) -> None:
    base = _base_type_name(type_str)
    if not base or base in KEYWORDS or base in _PRIMITIVE_TYPES:
        return
    decl = _lookup(scopes, base)
    if decl is None or decl.kind not in {"class", "entity", "struct", "data", "enum"}:
        return
    source = index.sources.get(file, "")
    span = _recover_name_span(source, approx, base)
    _add_use_site(index, file=file, span=span, name=base, decl=decl)


def _bind_var_type(scopes: list[_Scope], name: str, type_str: str | None) -> None:
    base = _base_type_name(type_str)
    if base and base not in _PRIMITIVE_TYPES and name:
        scopes[-1].var_types[name] = base


def _use_member_attr(
    index: RefIndex,
    scopes: list[_Scope],
    file: str,
    expr: Member,
) -> None:
    source = index.sources.get(file, "")
    sp = expr.span or Span(1, 1)
    mspan = _member_name_span(source, sp, expr.name)
    rtype = _receiver_type(index, scopes, expr.object)
    if rtype:
        decl = _lookup_member(index, rtype, expr.name)
        if decl is not None:
            _add_use_site(index, file=file, span=mspan, name=expr.name, decl=decl)
            return
    # Attribute name may be an enum member (Color.RED).
    for decl in index.sites_by_decl:
        if decl.name == expr.name and decl.kind == "enum_member" and decl.file == file:
            _add_use_site(index, file=file, span=mspan, name=expr.name, decl=decl)
            return


def _use_lvalue_path(
    index: RefIndex,
    scopes: list[_Scope],
    file: str,
    path: str,
    approx: Span,
) -> None:
    """Record uses for dotted assign targets like ``self.getalA`` / ``rm.field``."""
    if "." not in path or "[" in path:
        return
    parts = path.split(".")
    if len(parts) != 2:
        return
    head, attr = parts[0], parts[1]
    if head in {"self", "this"}:
        rtype = index.enclosing_types[-1] if index.enclosing_types else None
    else:
        rtype = _lookup_var_type(scopes, head)
    if not rtype:
        return
    decl = _lookup_member(index, rtype, attr)
    if decl is None:
        return
    source = index.sources.get(file, "")
    mspan = _member_name_span(source, approx, attr)
    _add_use_site(index, file=file, span=mspan, name=attr, decl=decl)


def _try_parse_expr(text: str) -> Expr | None:
    try:
        from .. import parse as parse_mod

        tokens = tokenize(text.strip())
        p = parse_mod._Tok(tokens)
        return parse_mod._parse_expression(p)
    except Exception:
        return None


def _walk_interp_hole(
    index: RefIndex,
    scopes: list[_Scope],
    file: str,
    hole: str,
    *,
    line: int,
    hole_col: int,
) -> None:
    """Walk a ``{expr}`` hole; spans remapped onto the host string line."""
    expr = _try_parse_expr(hole)
    if expr is None:
        return

    def remap_span(name: str, prefer_after_dot: bool = False) -> Span:
        idx = -1
        if prefer_after_dot:
            dot = hole.rfind("." + name)
            if dot >= 0:
                idx = dot + 1
        if idx < 0:
            idx = hole.find(name)
        if idx < 0:
            return Span(line, hole_col, line, hole_col + len(name))
        col = hole_col + idx
        return Span(line, col, line, col + len(name))

    def walk(node: Expr | None) -> None:
        if node is None:
            return
        if isinstance(node, Identifier):
            if node.name in {"self", "this"} or node.name in KEYWORDS:
                return
            decl = _lookup(scopes, node.name)
            if decl is None:
                return
            _add_use_site(index, file=file, span=remap_span(node.name), name=node.name, decl=decl)
            return
        if isinstance(node, Member):
            walk(node.object)
            rtype = _receiver_type(index, scopes, node.object)
            if rtype:
                decl = _lookup_member(index, rtype, node.name)
                if decl is not None:
                    _add_use_site(
                        index,
                        file=file,
                        span=remap_span(node.name, prefer_after_dot=True),
                        name=node.name,
                        decl=decl,
                    )
                    return
            for decl in index.sites_by_decl:
                if decl.name == node.name and decl.kind == "enum_member" and decl.file == file:
                    _add_use_site(
                        index,
                        file=file,
                        span=remap_span(node.name, prefer_after_dot=True),
                        name=node.name,
                        decl=decl,
                    )
                    return
            return
        if isinstance(node, Call):
            walk(node.callee)
            for a in node.args or []:
                val = getattr(a, "value", None) if type(a).__name__ == "KeywordArg" else a
                if isinstance(val, Expr):
                    walk(val)
                elif isinstance(a, Expr):
                    walk(a)
            return
        if isinstance(node, BinaryOp):
            walk(node.left)
            walk(node.right)
            return
        if isinstance(node, UnaryOp):
            walk(node.operand)
            return
        if isinstance(node, Index):
            walk(node.object)
            walk(node.index)
            return

    walk(expr)


def _walk_interpolated_string(
    index: RefIndex,
    scopes: list[_Scope],
    file: str,
    expr: InterpolatedString,
) -> None:
    raw = expr.raw or ""
    sp = expr.span or Span(1, 1)
    for m in _HOLE_RE.finditer(raw):
        hole = m.group(1)
        # ``raw`` starts at ``sp.column``; group(1) is the hole body offset in raw.
        hole_col = sp.column + m.start(1)
        _walk_interp_hole(
            index,
            scopes,
            file,
            hole,
            line=sp.line,
            hole_col=hole_col,
        )


def _register_type_member(index: RefIndex, type_name: str, member_name: str, decl: DeclKey) -> None:
    if type_name and member_name and member_name != "__init__":
        index.type_members[(type_name, member_name)] = decl


def _walk_expr(index: RefIndex, scopes: list[_Scope], file: str, expr: Expr | None) -> None:
    if expr is None:
        return
    if isinstance(expr, Identifier):
        _use_ident(index, scopes, file, expr)
        return
    if isinstance(expr, BinaryOp):
        _walk_expr(index, scopes, file, expr.left)
        _walk_expr(index, scopes, file, expr.right)
        return
    if isinstance(expr, UnaryOp):
        _walk_expr(index, scopes, file, expr.operand)
        return
    if isinstance(expr, Call):
        _walk_expr(index, scopes, file, expr.callee)
        for a in expr.args:
            val = getattr(a, "value", None) if type(a).__name__ == "KeywordArg" else a
            if isinstance(val, Expr):
                _walk_expr(index, scopes, file, val)
            elif isinstance(a, Expr):
                _walk_expr(index, scopes, file, a)
        return
    if isinstance(expr, Member):
        _walk_expr(index, scopes, file, expr.object)
        _use_member_attr(index, scopes, file, expr)
        return
    if isinstance(expr, InterpolatedString):
        _walk_interpolated_string(index, scopes, file, expr)
        return
    if isinstance(expr, Index):
        _walk_expr(index, scopes, file, expr.object)
        _walk_expr(index, scopes, file, expr.index)
        return
    if isinstance(expr, SwitchExpr):
        _walk_expr(index, scopes, file, expr.subject)
        for case in expr.cases:
            scopes.append(_Scope())
            for label in case.labels:
                if isinstance(label, ResultPattern) and label.binding:
                    _declare(
                        index,
                        scopes,
                        file=file,
                        name=label.binding,
                        span=label.binding_span or label.span or Span(1, 1),
                        kind="result_pattern",
                    )
            _walk_expr(index, scopes, file, case.value)
            if case.body:
                _walk_block(index, scopes, file, case.body, nest=False)
            scopes.pop()
        return
    if isinstance(expr, LambdaExpr):
        scopes.append(_Scope())
        for p in expr.params or []:
            if p:
                _declare(
                    index,
                    scopes,
                    file=file,
                    name=p,
                    span=expr.span or Span(1, 1),
                    kind="param",
                )
        if isinstance(expr.body, Block):
            _walk_block(index, scopes, file, expr.body, nest=False)
        else:
            _walk_expr(index, scopes, file, expr.body)  # type: ignore[arg-type]
        scopes.pop()
        return
    # Generic: walk known attributes
    for attr in ("value", "left", "right", "operand", "cond", "target", "elements"):
        child = getattr(expr, attr, None)
        if isinstance(child, list):
            for c in child:
                if isinstance(c, Expr):
                    _walk_expr(index, scopes, file, c)
        elif isinstance(child, Expr):
            _walk_expr(index, scopes, file, child)
    entries = getattr(expr, "entries", None)
    if isinstance(entries, list):
        for pair in entries:
            if isinstance(pair, tuple) and len(pair) == 2:
                _walk_expr(index, scopes, file, pair[0])
                _walk_expr(index, scopes, file, pair[1])



def _walk_block(
    index: RefIndex,
    scopes: list[_Scope],
    file: str,
    block: Block | None,
    *,
    nest: bool = False,
) -> None:
    if block is None:
        return
    if nest:
        scopes.append(_Scope())
    for stmt in block.statements or []:
        _walk_stmt(index, scopes, file, stmt)
    if nest:
        scopes.pop()


def _walk_stmt(index: RefIndex, scopes: list[_Scope], file: str, stmt: Any) -> None:
    source = index.sources.get(file, "")
    if isinstance(stmt, ImportStmt):
        names = list(stmt.names) if stmt.names else ([stmt.name] if stmt.name else [])
        if stmt.kind == "as" and stmt.alias:
            names = [stmt.alias]
        for n in names:
            if not n or n == "all":
                continue
            # Import creates a local binding; may later alias to remote decl.
            approx = stmt.span or Span(1, 1)
            span = _recover_name_span(source, approx, n)
            remote = index.export_bindings.get((stmt.module, n))
            if remote is not None:
                scopes[-1].bindings[n] = remote
                end_col = _span_end_col(span, n)
                _add_site(
                    index,
                    RefSite(
                        file=file,
                        line=span.line,
                        column=span.column,
                        end_column=end_col,
                        kind="import",
                        decl=remote,
                    ),
                )
            else:
                _declare(
                    index,
                    scopes,
                    file=file,
                    name=n,
                    span=span,
                    kind="import",
                    site_kind="import",
                )
        return
    if isinstance(stmt, FunctionDef):
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.name)
        _declare(index, scopes, file=file, name=stmt.name, span=span, kind="function")
        scopes.append(_Scope())
        for i, pname in enumerate(stmt.params):
            # Param spans approximate: recover on function line
            psp = _recover_name_span(source, span, pname)
            _declare(index, scopes, file=file, name=pname, span=psp, kind="param")
            ptypes = getattr(stmt, "param_types", None) or []
            if i < len(ptypes):
                _use_type_name(index, scopes, file, ptypes[i], span)
                _bind_var_type(scopes, pname, ptypes[i])
        ret = getattr(stmt, "return_type", None)
        if ret:
            _use_type_name(index, scopes, file, ret, span)
        _walk_block(index, scopes, file, stmt.body, nest=False)
        scopes.pop()
        return
    if isinstance(stmt, (ClassDef, EntityDef)):
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.name)
        kind = "class" if isinstance(stmt, ClassDef) else "entity"
        _declare(index, scopes, file=file, name=stmt.name, span=span, kind=kind)
        parent = getattr(stmt, "parent", "") or ""
        if parent:
            index.type_parents[stmt.name] = parent
            _use_type_name(index, scopes, file, parent, span)
        for base in getattr(stmt, "bases", None) or []:
            if base:
                _use_type_name(index, scopes, file, base, span)
        scopes.append(_Scope())
        index.enclosing_types.append(stmt.name)
        for f in stmt.fields or []:
            fspan = f.name_span or _recover_name_span(source, f.span or span, f.name)
            fdecl = _declare(index, scopes, file=file, name=f.name, span=fspan, kind="field")
            _register_type_member(index, stmt.name, f.name, fdecl)
            ftype = getattr(f, "type_name", None) or getattr(f, "type", None)
            if ftype:
                _use_type_name(index, scopes, file, ftype, fspan)
                _bind_var_type(scopes, f.name, ftype)
            _walk_expr(index, scopes, file, f.default)
        for m in stmt.methods or []:
            mspan = m.name_span or _recover_name_span(source, m.span or span, m.name)
            # Constructors parse as ``__init__``; keep decl kind method for sites.
            mdecl = _declare(index, scopes, file=file, name=m.name, span=mspan, kind="method")
            _register_type_member(index, stmt.name, m.name, mdecl)
            scopes.append(_Scope())
            for i, pname in enumerate(m.params):
                psp = _recover_name_span(source, mspan, pname)
                _declare(index, scopes, file=file, name=pname, span=psp, kind="param")
                ptypes = getattr(m, "param_types", None) or []
                if i < len(ptypes):
                    _use_type_name(index, scopes, file, ptypes[i], mspan)
                    _bind_var_type(scopes, pname, ptypes[i])
            ret = getattr(m, "return_type", None)
            if ret:
                _use_type_name(index, scopes, file, ret, mspan)
            _walk_block(index, scopes, file, m.body, nest=False)
            scopes.pop()
        index.enclosing_types.pop()
        scopes.pop()
        return
    if isinstance(stmt, (StructDef, DataDef, EnumDef)):
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.name)
        kind = "struct" if isinstance(stmt, StructDef) else ("data" if isinstance(stmt, DataDef) else "enum")
        _declare(index, scopes, file=file, name=stmt.name, span=span, kind=kind)
        if isinstance(stmt, EnumDef):
            for mem in stmt.members or []:
                mspan = mem.name_span or _recover_name_span(source, mem.span or span, mem.name)
                _declare(index, scopes, file=file, name=mem.name, span=mspan, kind="enum_member")
        else:
            for f in getattr(stmt, "fields", None) or []:
                fname = getattr(f, "name", "") or ""
                if not fname:
                    continue
                fspan = getattr(f, "name_span", None) or _recover_name_span(
                    source, getattr(f, "span", None) or span, fname
                )
                fdecl = _declare(index, scopes, file=file, name=fname, span=fspan, kind="field")
                _register_type_member(index, stmt.name, fname, fdecl)
        return
    if isinstance(stmt, AssignStmt) and stmt.declare_type is not None:
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.name)
        _use_type_name(index, scopes, file, stmt.declare_type, approx)
        _declare(index, scopes, file=file, name=stmt.name, span=span, kind="var")
        _bind_var_type(scopes, stmt.name, stmt.declare_type)
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, AssignStmt):
        # assignment to existing name — treat lhs simple name as use
        if "." not in stmt.name and "[" not in stmt.name:
            decl = _lookup(scopes, stmt.name)
            if decl is not None:
                approx = stmt.span or Span(1, 1)
                span = _recover_name_span(source, approx, stmt.name)
                _add_site(
                    index,
                    RefSite(
                        file=file,
                        line=span.line,
                        column=span.column,
                        end_column=_span_end_col(span, stmt.name),
                        kind="use",
                        decl=decl,
                    ),
                )
        else:
            _use_lvalue_path(
                index,
                scopes,
                file,
                stmt.name,
                stmt.span or Span(1, 1),
            )
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, ArrayDecl):
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.name)
        _declare(index, scopes, file=file, name=stmt.name, span=span, kind="var")
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, (SharedDecl, AtomicDecl)):
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.name)
        _declare(index, scopes, file=file, name=stmt.name, span=span, kind="var")
        dtype = getattr(stmt, "type_name", None) or getattr(stmt, "declare_type", None)
        if dtype:
            _use_type_name(index, scopes, file, dtype, approx)
            _bind_var_type(scopes, stmt.name, dtype)
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, AugAssignStmt):
        if "." not in stmt.name and "[" not in stmt.name:
            decl = _lookup(scopes, stmt.name)
            if decl is not None:
                approx = stmt.span or Span(1, 1)
                span = _recover_name_span(source, approx, stmt.name)
                _add_site(
                    index,
                    RefSite(
                        file=file,
                        line=span.line,
                        column=span.column,
                        end_column=_span_end_col(span, stmt.name),
                        kind="use",
                        decl=decl,
                    ),
                )
        else:
            _use_lvalue_path(
                index,
                scopes,
                file,
                stmt.name,
                stmt.span or Span(1, 1),
            )
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, PrintStmt):
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, ReturnStmt):
        _walk_expr(index, scopes, file, stmt.value)
        return
    if isinstance(stmt, IfStmt):
        _walk_expr(index, scopes, file, stmt.cond)
        _walk_block(index, scopes, file, stmt.then_body, nest=True)
        if isinstance(stmt.else_body, IfStmt):
            _walk_stmt(index, scopes, file, stmt.else_body)
        else:
            _walk_block(index, scopes, file, stmt.else_body, nest=True)
        return
    if isinstance(stmt, WhileStmt):
        _walk_expr(index, scopes, file, stmt.cond)
        _walk_block(index, scopes, file, stmt.body, nest=True)
        return
    if isinstance(stmt, ForEachStmt):
        _walk_expr(index, scopes, file, stmt.iterable)
        scopes.append(_Scope())
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.var)
        _declare(index, scopes, file=file, name=stmt.var, span=span, kind="foreach")
        _walk_block(index, scopes, file, stmt.body, nest=False)
        scopes.pop()
        return
    if isinstance(stmt, ForRangeStmt):
        _walk_expr(index, scopes, file, stmt.start)
        _walk_expr(index, scopes, file, stmt.stop)
        scopes.append(_Scope())
        approx = stmt.name_span or stmt.span or Span(1, 1)
        span = stmt.name_span or _recover_name_span(source, approx, stmt.var)
        _declare(index, scopes, file=file, name=stmt.var, span=span, kind="forrange")
        _walk_block(index, scopes, file, stmt.body, nest=False)
        scopes.pop()
        return
    if isinstance(stmt, SwitchStmt):
        _walk_expr(index, scopes, file, stmt.subject)
        for case in stmt.cases or []:
            has_pat = any(
                isinstance(label, ResultPattern) and label.binding
                for label in case.labels
            )
            nest_arm = bool(case.brace_scoped) or has_pat
            if nest_arm:
                scopes.append(_Scope())
            for label in case.labels:
                if isinstance(label, ResultPattern) and label.binding:
                    _declare(
                        index,
                        scopes,
                        file=file,
                        name=label.binding,
                        span=label.binding_span or label.span or Span(1, 1),
                        kind="result_pattern",
                    )
            _walk_expr(index, scopes, file, case.value)
            _walk_block(index, scopes, file, case.body, nest=False)
            if nest_arm:
                scopes.pop()
        return
    if isinstance(stmt, Block):
        _walk_block(index, scopes, file, stmt, nest=True)
        return
    # Expression statement / opaque
    val = getattr(stmt, "value", None)
    if isinstance(val, Expr):
        _walk_expr(index, scopes, file, val)
    expr = getattr(stmt, "expr", None)
    if isinstance(expr, Expr):
        _walk_expr(index, scopes, file, expr)


# Populated during build for cross-file imports.
RefIndex.export_bindings = {}  # type: ignore[attr-defined]


def _collect_exports(path: Path, mod: Module) -> dict[str, DeclKey]:
    """Map export name → DeclKey for package/global top-level decls."""
    file = _file_key(path)
    source = path.read_text(encoding="utf-8")
    out: dict[str, DeclKey] = {}
    for stmt in mod.body:
        vis = getattr(stmt, "visibility", "") or ""
        if vis not in {"package", "global"}:
            continue
        name = getattr(stmt, "name", "") or ""
        if not name:
            continue
        approx = getattr(stmt, "name_span", None) or getattr(stmt, "span", None) or Span(1, 1)
        span = approx if getattr(stmt, "name_span", None) else _recover_name_span(source, approx, name)
        kind = type(stmt).__name__.replace("Def", "").lower()
        if isinstance(stmt, FunctionDef):
            kind = "function"
        elif isinstance(stmt, AssignStmt):
            kind = "var"
        out[name] = DeclKey(file=file, line=span.line, column=span.column, name=name, kind=kind)
    return out


def build_index(entry: Path, *, entry_source: str | None = None) -> RefIndex:
    """Build binding-aware index for ``entry`` and its resolved .pys import graph.

    When ``entry_source`` is set (IDE ``--stdin`` live buffer), that text is used
    for ``entry`` instead of reading the file from disk.
    """
    entry = entry.resolve()
    index = RefIndex()
    index.export_bindings = {}  # type: ignore[attr-defined]

    texts: dict[Path, str] = {}
    modules: dict[Path, Module] = {}

    def load(path: Path) -> Module | None:
        path = path.resolve()
        if path in modules:
            return modules[path]
        try:
            if path == entry and entry_source is not None:
                text = entry_source
            else:
                text = path.read_text(encoding="utf-8")
            mod = parse_program(text)
        except Exception:
            return None
        texts[path] = text
        modules[path] = mod
        index.sources[_file_key(path)] = text
        index.modules[_file_key(path)] = mod
        return mod

    load(entry)
    # Discover imported .pys modules from entry (and transitively via resolver paths).
    try:
        imported = discover_imported_modules(entry)
    except Exception:
        imported = {}
    for ipath in imported:
        if isinstance(ipath, Path) and str(ipath).endswith(".pys"):
            load(Path(ipath))

    # Same-package peers (folder siblings, or mirrored dirs under pys.toml source_roots).
    from ..project_manifest import package_peer_files

    for sib in package_peer_files(entry):
        load(sib)

    # First pass: collect exports
    export_by_module_stem: dict[str, dict[str, DeclKey]] = {}
    for path, mod in modules.items():
        export_by_module_stem[path.stem] = _collect_exports(path, mod)

    # Map import module ref → exports
    for path, mod in modules.items():
        for stmt in mod.body:
            if not isinstance(stmt, ImportStmt):
                continue
            mod_ref = (stmt.module or "").replace(".pys", "").split("/")[-1].split(".")[-1]
            exports = export_by_module_stem.get(mod_ref, {})
            for n, decl in exports.items():
                index.export_bindings[(stmt.module, n)] = decl  # type: ignore[attr-defined]
                index.export_bindings[(mod_ref, n)] = decl  # type: ignore[attr-defined]

    # Second pass: walk with scopes
    for path, mod in modules.items():
        file = _file_key(path)
        scopes = [_Scope()]
        for stmt in mod.body:
            _walk_stmt(index, scopes, file, stmt)

    return index


def resolve_at(index: RefIndex, file: Path | str, line: int, column: int) -> DeclKey | None:
    """Resolve declaration under cursor (1-based line/column).

    ``end_column`` on sites is exclusive (span end). A caret sitting on that
    exclusive end — typical after a left-to-right word selection in the IDE —
    still resolves to the site.
    """
    fk = _file_key(Path(file))
    # Exact match
    decl = index.at_position.get((fk, line, column))
    if decl is not None:
        return decl
    # Cursor inside an identifier (or on its exclusive end column).
    best: RefSite | None = None
    for sites in index.sites_by_decl.values():
        for site in sites:
            if site.file != fk or site.line != line:
                continue
            if site.column <= column <= site.end_column:
                if best is None or site.column > best.column:
                    best = site
    return best.decl if best else None


def find_references(
    source_path: Path,
    *,
    symbol: str | None = None,
    line: int | None = None,
    column: int | None = None,
) -> list[dict[str, Any]]:
    """Binding-aware references for IDE Find Usages / rename.

    Prefer ``line``+``column`` (1-based). If only ``symbol`` is given, resolve
    the declaration named ``symbol`` visible from the entry file's top level /
    imports (first matching decl).
    """
    source_path = source_path.resolve()
    workspace = workspace_root_from_env()
    if workspace is not None:
        contained = resolve_workspace_path(source_path, workspace)
        if contained is None:
            return []
        source_path = contained

    index = build_index(source_path)
    decl: DeclKey | None = None
    if line is not None and column is not None:
        decl = resolve_at(index, source_path, line, column)
    if decl is None and symbol:
        name = symbol.split(".")[-1]
        # Prefer decl in entry file, then any
        candidates = [
            d
            for d in index.sites_by_decl
            if d.name == name
            and d.kind
            in {
                "function",
                "var",
                "class",
                "struct",
                "entity",
                "enum",
                "enum_member",
                "method",
                "field",
                "param",
                "foreach",
                "forrange",
            }
        ]
        for d in candidates:
            if d.file == _file_key(source_path):
                decl = d
                break
        if decl is None and candidates:
            decl = candidates[0]
    if decl is None:
        return []
    hits = []
    seen: set[tuple[str, int, int]] = set()
    for site in index.sites_for(decl):
        key = (site.file, site.line, site.column)
        if key in seen:
            continue
        seen.add(key)
        hits.append(
            {
                "file": site.file,
                "line": site.line,
                "column": site.column,
                "end_column": site.end_column,
                "kind": site.kind,
            }
        )
    hits.sort(key=lambda h: (h["file"], h["line"], h["column"]))
    return hits
