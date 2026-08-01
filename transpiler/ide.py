"""IDE helpers: symbol location for go-to-definition / highlighting.

Uses the AST pipeline (parse + ImportResolver + compile_pys).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .ast_nodes import (
    AssignStmt,
    Call,
    ForEachStmt,
    Identifier,
    ImportStmt,
    Member,
    Module,
)
from .imports import ImportResolver, module_info_from_ast, pys_import_line
from .parse import parse_program
from .pipeline import compile_pys
from .pytypes import (
    _find_class_in_package,
    _usage_tips_for,
    infer_call_return_info,
    locate_attr_path,
    locate_type_definition,
)
from .transpiler import TranspileError
from .workspace import resolve_workspace_path, workspace_root_from_env

_PRIMITIVES = {"int", "float", "char", "string", "bool", "list", "dict", "tuple", "set"}


def _error_dict(exc: TranspileError) -> dict:
    return {
        "message": exc.args[0] if exc.args else str(exc),
        "line": exc.line_number,
        "column": exc.column,
        "code_line": exc.code_line,
        "code": getattr(exc, "code", None),
        "suggested_fix": getattr(exc, "suggested_fix", None),
        "tips": list(getattr(exc, "tips", None) or []),
        "source_file": str(exc.source_file) if exc.source_file else None,
    }


def _base_type(type_name: str) -> str:
    name = (type_name or "").strip()
    if "<" in name:
        name = name.split("<", 1)[0]
    if name.endswith("[]"):
        name = name[:-2]
    return name


def _call_receiver_method(expr: Any) -> tuple[str, str | None] | None:
    """Return (receiver_expr, method_or_None) for Call nodes used by pytypes."""
    if not isinstance(expr, Call):
        return None
    callee = expr.callee
    if isinstance(callee, Identifier):
        return callee.name, None
    if isinstance(callee, Member):
        parts: list[str] = []
        cur: Any = callee
        method = callee.name
        obj = callee.object
        while isinstance(obj, Member):
            parts.append(obj.name)
            obj = obj.object
        if isinstance(obj, Identifier):
            parts.append(obj.name)
            parts.reverse()
            if parts:
                # Member chain: demo.make → recv=demo, method=make
                # or mysql.connector.connect → recv=mysql.connector, method=None style
                if len(parts) == 1:
                    return parts[0], method
                return ".".join(parts + [method]), None
        return None
    return None


def _seed_resolver(
    tree: Module,
    source: str,
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
) -> ImportResolver:
    resolver = ImportResolver(
        source,
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    for stmt in tree.body:
        if not isinstance(stmt, ImportStmt):
            continue
        line = pys_import_line(stmt)
        if not line:
            continue
        try:
            resolver.translate_import_statement(
                line, stmt.span.line if stmt.span else 1, line
            )
        except TranspileError:
            raise
        except Exception:
            continue
    return resolver


def _register_type(
    type_name: str,
    *,
    resolver: ImportResolver,
    site_paths: list[Path],
    validated_types: set[str],
    type_definitions: dict[str, tuple[Path, int, int]],
) -> bool:
    base = _base_type(type_name)
    if not base:
        return False
    if base in _PRIMITIVES:
        validated_types.add(base)
        return True
    if base in resolver.class_parents or base in resolver.interfaces or base in resolver.exports:
        validated_types.add(base)
        if base in resolver.symbol_locations:
            path, line, col = resolver.symbol_locations[base]
            type_definitions.setdefault(base, (path, line, col))
        return True
    if base in resolver.type_modules:
        validated_types.add(base)
        located = locate_type_definition(
            base,
            type_modules=resolver.type_modules,
            site_paths=site_paths,
            allow_runtime_imports=resolver.allow_runtime_introspection,
        )
        if located:
            type_definitions[base] = located
        return True
    for mod in sorted(set(resolver.imported_modules.values())):
        cls = _find_class_in_package(
            mod,
            base,
            site_paths,
            allow_runtime_imports=resolver.allow_runtime_introspection,
        )
        if isinstance(cls, type):
            resolver.type_modules[base] = cls.__module__
            validated_types.add(base)
            located = locate_type_definition(
                base,
                type_modules=resolver.type_modules,
                site_paths=site_paths,
                allow_runtime_imports=resolver.allow_runtime_introspection,
            )
            if located:
                type_definitions[base] = located
            return True
    return False


def _collect_hints_and_types(
    tree: Module,
    resolver: ImportResolver,
    site_paths: list[Path],
) -> tuple[dict[str, str], dict[str, str], list[dict], set[str], dict[str, tuple[Path, int, int]]]:
    variable_types = dict(resolver.variable_types)
    collection_element_types: dict[str, str] = {}
    hints: list[dict] = []
    validated_types = set(_PRIMITIVES)
    type_definitions = dict(resolver.type_definitions)

    for name in list(resolver.class_parents) + list(resolver.interfaces):
        _register_type(
            name,
            resolver=resolver,
            site_paths=site_paths,
            validated_types=validated_types,
            type_definitions=type_definitions,
        )

    for stmt in tree.body:
        if isinstance(stmt, AssignStmt):
            line = stmt.span.line if stmt.span else 1
            if stmt.declare_type and stmt.declare_type != "var":
                base = _base_type(stmt.declare_type)
                variable_types[stmt.name] = stmt.declare_type
                _register_type(
                    base,
                    resolver=resolver,
                    site_paths=site_paths,
                    validated_types=validated_types,
                    type_definitions=type_definitions,
                )
            call = _call_receiver_method(stmt.value)
            if call is not None:
                recv, method = call
                info = infer_call_return_info(
                    recv,
                    method,
                    variable_types=variable_types,
                    imported_modules=resolver.imported_modules,
                    site_paths=site_paths,
                    type_modules=resolver.type_modules,
                    allow_runtime_imports=resolver.allow_runtime_introspection,
                )
                if info is not None:
                    if info.element_type and info.pys_type in {"list", "set", "tuple", "dict"}:
                        collection_element_types[stmt.name] = info.element_type
                    if info.from_external and info.weak and (
                        not stmt.declare_type or _base_type(stmt.declare_type) in {"list", "dict", "tuple", "set"}
                    ):
                        # Bare `list rows = …` still gets weak-library hint; generics suppress it.
                        if not (stmt.declare_type and "<" in stmt.declare_type):
                            tips = _usage_tips_for(info.pys_type, info.element_type, stmt.name)
                            hints.append(
                                {
                                    "line": line,
                                    "column": 1,
                                    "code": "pys.untyped-library",
                                    "message": (
                                        f"'{stmt.name}' comes from a Python library with weak/untyped "
                                        f"return information. Prefer treating it as typed in PYS."
                                        + (
                                            f" Best element/row type for this API: `{info.element_type}`."
                                            if info.element_type
                                            else ""
                                        )
                                    ),
                                    "tips": tips,
                                    "suggested_loop": (
                                        f"loop ({info.element_type} x in {stmt.name})"
                                        if info.pys_type == "list" and info.element_type
                                        else None
                                    ),
                                    "element_type": info.element_type,
                                    "pys_type": info.pys_type,
                                }
                            )
                    if not stmt.declare_type:
                        variable_types.setdefault(stmt.name, info.pys_type)
            elif stmt.declare_type:
                variable_types[stmt.name] = stmt.declare_type

        elif isinstance(stmt, ForEachStmt):
            line = stmt.span.line if stmt.span else 1
            coll = None
            if isinstance(stmt.iterable, Identifier):
                coll = stmt.iterable.name
            if coll and stmt.var and not stmt.var_type:
                elem = collection_element_types.get(coll)
                if elem:
                    hints.append(
                        {
                            "line": line,
                            "column": 1,
                            "code": "pys.untyped-loop-var",
                            "message": (
                                f"Loop variable '{stmt.var}' has no type; "
                                f"collection '{coll}' elements look like `{elem}`."
                            ),
                            "suggested_loop": f"loop ({elem} {stmt.var} in {coll})",
                            "element_type": elem,
                        }
                    )

    return variable_types, collection_element_types, hints, validated_types, type_definitions


def analyze_file(
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
) -> dict:
    workspace_root = workspace_root_from_env()
    if workspace_root is not None:
        contained = resolve_workspace_path(source_path, workspace_root)
        if contained is None:
            raise TranspileError(
                f"Source path resolves outside the workspace: {source_path}"
            )
        source_path = contained
    else:
        source_path = source_path.resolve()
    source = source_path.read_text(encoding="utf-8")
    error = None
    try:
        compile_pys(
            source,
            source_path=source_path,
            allow_runtime_introspection=allow_runtime_introspection,
        )
    except TranspileError as exc:
        error = _error_dict(exc)

    try:
        tree = parse_program(source)
    except TranspileError as exc:
        if error is None:
            error = _error_dict(exc)
        return {
            "ok": False,
            "error": error,
            "hints": [],
            "symbols": {},
            "variable_types": {},
            "type_modules": {},
            "imported_modules": {},
            "collection_element_types": {},
            "validated_types": [],
            "class_parents": {},
            "method_locations": {},
            "_site_paths": [],
        }

    resolver = _seed_resolver(
        tree,
        source,
        source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    site_paths = resolver._deps_paths()
    info = module_info_from_ast(source_path, tree)

    (
        variable_types,
        collection_element_types,
        hints,
        validated_types,
        type_definitions,
    ) = _collect_hints_and_types(tree, resolver, site_paths)

    symbols = {
        name: {"file": str(path), "line": line, "column": col, "kind": "symbol"}
        for name, (path, line, col) in {**info.symbol_locations, **resolver.symbol_locations}.items()
    }
    method_locations = {
        cls: {
            method: {"file": str(path), "line": line, "column": col, "kind": "method"}
            for method, (path, line, col) in methods.items()
        }
        for cls, methods in {**info.method_locations, **resolver.method_locations}.items()
    }

    for type_name in set(resolver.type_modules) | set(type_definitions) | set(validated_types):
        if type_name in _PRIMITIVES:
            continue
        located = type_definitions.get(type_name)
        if located is None and type_name in resolver.type_modules:
            located = locate_type_definition(
                type_name,
                type_modules=resolver.type_modules,
                site_paths=site_paths,
                allow_runtime_imports=resolver.allow_runtime_introspection,
            )
            if located:
                type_definitions[type_name] = located
        if located:
            path, line, col = located
            symbols[type_name] = {
                "file": str(path),
                "line": line,
                "column": col,
                "kind": "type",
            }

    class_parents = {**info.class_parents, **resolver.class_parents}

    return {
        "ok": error is None,
        "error": error,
        "hints": hints,
        "symbols": symbols,
        "variable_types": variable_types,
        "type_modules": dict(resolver.type_modules),
        "imported_modules": dict(resolver.imported_modules),
        "collection_element_types": collection_element_types,
        "validated_types": sorted(validated_types),
        "class_parents": class_parents,
        "method_locations": method_locations,
        "_site_paths": [str(p) for p in site_paths],
        "_allow_runtime_introspection": allow_runtime_introspection,
    }


def _lookup_pys_method(analysis: dict, type_name: str, method: str) -> dict | None:
    """Find method location on a PYS class, walking parents."""
    parents = analysis.get("class_parents") or {}
    method_locations = analysis.get("method_locations") or {}
    seen: set[str] = set()
    current: str | None = type_name
    while current and current not in seen:
        seen.add(current)
        methods = method_locations.get(current) or {}
        if method in methods:
            return methods[method]
        current = parents.get(current)
    return None


def lookup_symbol(analysis: dict, symbol: str) -> dict | None:
    """Resolve a bare name or dotted path to a location dict."""
    symbol = (symbol or "").strip()
    if not symbol:
        return None
    loc = analysis.get("symbols", {}).get(symbol)
    if loc:
        return loc

    if "." in symbol and re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", symbol):
        parts = symbol.split(".")
        if len(parts) == 2:
            head, method = parts
            variable_types = analysis.get("variable_types") or {}
            type_name = variable_types.get(head, head)
            if type_name.startswith("list<"):
                type_name = "list"
            elif type_name.startswith("dict<"):
                type_name = "dict"
            pys_loc = _lookup_pys_method(analysis, _base_type(type_name), method)
            if pys_loc:
                return pys_loc

    site_paths = [Path(p) for p in analysis.get("_site_paths") or []]
    located = locate_attr_path(
        symbol,
        imported_modules=analysis.get("imported_modules") or {},
        site_paths=site_paths,
        variable_types=analysis.get("variable_types") or {},
        type_modules=analysis.get("type_modules") or {},
        allow_runtime_imports=bool(analysis.get("_allow_runtime_introspection", False)),
    )
    if not located:
        return None
    path, line, col, kind = located
    return {"file": str(path), "line": line, "column": col, "kind": kind}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 1:
        print(json.dumps({"ok": False, "message": "Usage: python -m transpiler.ide <file.pys> [symbol]"}))
        return 2
    path = Path(argv[0])
    try:
        result = analyze_file(path)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}, "validated_types": [], "symbols": {}}))
        return 1
    if len(argv) >= 2:
        symbol = argv[1]
        loc = lookup_symbol(result, symbol)
        print(
            json.dumps(
                {
                    "ok": loc is not None,
                    "symbol": symbol,
                    "location": loc,
                    "types": result.get("variable_types"),
                    "validated_types": result.get("validated_types"),
                }
            )
        )
    else:
        public = {k: v for k, v in result.items() if not k.startswith("_")}
        print(json.dumps(public))
    return 0 if result.get("ok") or len(argv) >= 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
