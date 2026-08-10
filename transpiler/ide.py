"""IDE helpers: symbol location, Find Usages, and highlighting.

Uses the AST pipeline (parse + ImportResolver + compile_pys).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .ast_nodes import (
    AssignStmt,
    Call,
    ClassDef,
    EntityDef,
    ForEachStmt,
    FunctionDef,
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
from . import sem as sem_mod
from .transpiler import TranspileError, TranspileWarning
from .workspace import resolve_workspace_path, workspace_root_from_env

_PRIMITIVES = {
    "int",
    "float",
    "char",
    "string",
    "bool",
    "object",
    "byte",
    "nibble",
    "int16",
    "int32",
    "int64",
    "dword",
    "list",
    "dict",
    "tuple",
    "set",
    "nullable",
}


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


def _warning_dict(warn: TranspileWarning) -> dict:
    return warn.to_dict()


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


def _type_arg_strings(type_name: str) -> list[str]:
    """Return top-level generic arguments of a canonical type string."""
    text = (type_name or "").strip()
    start = text.find("<")
    if start < 0 or not text.endswith(">"):
        return []
    inner = text[start + 1 : -1]
    args: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in inner:
        if ch == "<":
            depth += 1
            current.append(ch)
        elif ch == ">":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            piece = "".join(current).strip()
            if piece:
                args.append(piece)
            current = []
        else:
            current.append(ch)
    piece = "".join(current).strip()
    if piece:
        args.append(piece)
    return args


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
    for arg in _type_arg_strings(type_name):
        _register_type(
            arg,
            resolver=resolver,
            site_paths=site_paths,
            validated_types=validated_types,
            type_definitions=type_definitions,
        )
    if base in _PRIMITIVES:
        validated_types.add(base)
        return True
    if (
        base in resolver.class_parents
        or base in resolver.interfaces
        or base in getattr(resolver, "structs", set())
        or base in getattr(resolver, "enums", set())
        or base in resolver.exports
    ):
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

    for name in (
        list(resolver.class_parents)
        + list(resolver.interfaces)
        + list(getattr(resolver, "structs", set()))
        + list(getattr(resolver, "enums", set()))
    ):
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
                variable_types[stmt.name] = stmt.declare_type
                _register_type(
                    stmt.declare_type,
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

    _bind_callable_params(
        tree,
        resolver=resolver,
        site_paths=site_paths,
        variable_types=variable_types,
        validated_types=validated_types,
        type_definitions=type_definitions,
    )
    return variable_types, collection_element_types, hints, validated_types, type_definitions


def _bind_callable_params(
    tree: Module,
    *,
    resolver: ImportResolver,
    site_paths: list[Path],
    variable_types: dict[str, str],
    validated_types: set[str],
    type_definitions: dict[str, tuple[Path, int, int]],
) -> None:
    """Map typed function/method parameters into ``variable_types`` for attr navigation.

    Enables Go to Definition on ``request.json`` when ``request`` is a ``Request``
    parameter (library navigate / runtime introspection). Duplicate names keep the
    last binding — good enough when params share the same library type.
    """

    def bind(params: list[str], param_types: list[str]) -> None:
        for i, name in enumerate(params):
            if i >= len(param_types) or not param_types[i]:
                continue
            ptype = param_types[i]
            variable_types[name] = ptype
            _register_type(
                ptype,
                resolver=resolver,
                site_paths=site_paths,
                validated_types=validated_types,
                type_definitions=type_definitions,
            )

    for stmt in tree.body:
        if isinstance(stmt, FunctionDef):
            bind(stmt.params, stmt.param_types)
        elif isinstance(stmt, (ClassDef, EntityDef)):
            for m in stmt.methods:
                bind(m.params, m.param_types)


def analyze_file(
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
    source: str | None = None,
) -> dict:
    """Analyze a ``.pys`` path for IDE diagnostics.

    ``source_path`` is always used for workspace containment, manifests, and
    symbol identity. When ``source`` is provided (unsaved editor buffer), that
    text is analyzed instead of reading the file from disk.
    """
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
    if source is None:
        source = source_path.read_text(encoding="utf-8")
    error = None
    warnings: list[dict] = []
    is_entrypoint = False
    try:
        from .project_manifest import find_manifest, load_project_main

        manifest = find_manifest(source_path)
        configured = load_project_main(manifest) if manifest is not None else None
        is_entrypoint = configured == source_path
        compile_pys(
            source,
            source_path=source_path,
            allow_runtime_introspection=allow_runtime_introspection,
            is_entrypoint=is_entrypoint,
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
            "warnings": [],
            "hints": [],
            "symbols": {},
            "variable_types": {},
            "narrowed_types": {},
            "type_modules": {},
            "imported_modules": {},
            "collection_element_types": {},
            "validated_types": [],
            "class_parents": {},
            "method_locations": {},
            "_site_paths": [],
        }

    if error is None:
        try:
            tree = sem_mod.analyze(
                tree,
                source_path=source_path,
                allow_runtime_introspection=allow_runtime_introspection,
                is_entrypoint=is_entrypoint,
            )
            warnings = [
                _warning_dict(w) for w in getattr(tree, "analysis_warnings", []) or []
            ]
        except TranspileError as exc:
            error = _error_dict(exc)

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
    struct_field_locations = {
        typ: {
            field: {"file": str(path), "line": line, "column": col, "kind": "field"}
            for field, (path, line, col) in fields.items()
        }
        for typ, fields in {
            **info.struct_field_locations,
            **getattr(resolver, "struct_field_locations", {}),
        }.items()
    }
    enum_member_locations = {
        typ: {
            member: {"file": str(path), "line": line, "column": col, "kind": "member"}
            for member, (path, line, col) in members.items()
        }
        for typ, members in {
            **info.enum_member_locations,
            **getattr(resolver, "enum_member_locations", {}),
        }.items()
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
        "warnings": warnings,
        "hints": hints,
        "symbols": symbols,
        "variable_types": variable_types,
        "narrowed_types": dict(
            getattr(tree, "analysis_narrowed_types", {}) or {}
        ),
        "type_modules": dict(resolver.type_modules),
        "imported_modules": dict(resolver.imported_modules),
        "collection_element_types": collection_element_types,
        "validated_types": sorted(validated_types),
        "class_parents": class_parents,
        "method_locations": method_locations,
        "struct_field_locations": struct_field_locations,
        "enum_member_locations": enum_member_locations,
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


def _lookup_struct_field(analysis: dict, type_name: str, field: str) -> dict | None:
    """Find a struct field declaration for ``Type.field`` or binding.field."""
    fields = (analysis.get("struct_field_locations") or {}).get(type_name) or {}
    return fields.get(field)


def _lookup_enum_member(analysis: dict, type_name: str, member: str) -> dict | None:
    """Find an enum member declaration for ``EnumName.MEMBER``."""
    members = (analysis.get("enum_member_locations") or {}).get(type_name) or {}
    return members.get(member)


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
            head, member = parts
            variable_types = analysis.get("variable_types") or {}
            type_name = variable_types.get(head, head)
            if type_name.startswith("list<"):
                type_name = "list"
            elif type_name.startswith("dict<"):
                type_name = "dict"
            base = _base_type(type_name)
            pys_loc = _lookup_pys_method(analysis, base, member)
            if pys_loc:
                return pys_loc
            field_loc = _lookup_struct_field(analysis, base, member)
            if field_loc:
                return field_loc
            enum_loc = _lookup_enum_member(analysis, base, member)
            if enum_loc:
                return enum_loc
            # EnumName.MEMBER when head is the type itself
            enum_loc = _lookup_enum_member(analysis, head, member)
            if enum_loc:
                return enum_loc

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


def find_usages(
    source_path: Path,
    symbol: str,
    *,
    line: int | None = None,
    column: int | None = None,
) -> list[dict[str, Any]]:
    """Find binding-aware identifier occurrences for Find Usages / ReferenceProvider.

    Prefer ``line`` + ``column`` (1-based) under the cursor so shadowed names
    resolve to the correct declaration. ``symbol`` is used when position is
    omitted (CLI) or as a fallback.
    """
    from .lex import KEYWORDS
    from .refactor.refs import find_references

    symbol = (symbol or "").strip()
    name = symbol.split(".")[-1] if symbol else ""
    if name and (name in KEYWORDS or name in _PRIMITIVES):
        return []
    return find_references(
        source_path,
        symbol=symbol or None,
        line=line,
        column=column,
    )


def prepare_debug(
    source_path: Path,
    out_dir: Path,
    *,
    target: str = "python",
) -> dict[str, Any]:
    """Transpile entry + imports with ``*.pysmap.json`` sidecars for DAP.

    Target-neutral prepare contract (loose coupling):
    - ``main`` / ``cwd`` / ``maps`` always present on success
    - Python adds ``python`` + ``pythonpath_prepend``
    - JavaScript adds ``runtimeExecutable`` (node or qode)

    Run-class privilege: may use runtime introspection / npm install.
    """
    from .imports import discover_imported_modules
    from .project_manifest import resolve_entrypoint
    from .transpiler import transpile_with_modules_and_maps

    if target not in ("python", "javascript"):
        return {
            "ok": False,
            "error": {
                "message": f"Unsupported debug target {target!r}",
                "line": None,
                "column": None,
            },
        }

    source_path = source_path.resolve()
    workspace = workspace_root_from_env()
    if workspace is not None:
        contained = resolve_workspace_path(source_path, workspace)
        if contained is None:
            return {
                "ok": False,
                "error": {
                    "message": "PYS file must resolve inside the workspace.",
                    "line": None,
                    "column": None,
                },
            }
        source_path = contained
    try:
        source_path = resolve_entrypoint(source_path)
    except TranspileError as exc:
        return {"ok": False, "error": _error_dict(exc)}

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        modules, maps, names = transpile_with_modules_and_maps(
            source_path,
            allow_runtime_introspection=True,
            target=target,
        )
    except TranspileError as exc:
        return {"ok": False, "error": _error_dict(exc)}
    except Exception as exc:
        return {
            "ok": False,
            "error": {"message": f"{type(exc).__name__}: {exc}"},
        }

    pys_paths: dict[str, Path] = {source_path.stem: source_path}
    for path in discover_imported_modules(
        source_path,
        allow_runtime_introspection=True,
    ):
        pys_paths[path.stem] = path

    hide_prefixes = ["_pys_", "__pys_", "_Pys"]

    if target == "javascript":
        return _prepare_debug_javascript(
            source_path=source_path,
            out_dir=out_dir,
            modules=modules,
            maps=maps,
            names=names,
            pys_paths=pys_paths,
            hide_prefixes=hide_prefixes,
        )

    map_files: dict[str, str] = {}
    for stem, python_text in modules.items():
        py_path = out_dir / f"{stem}.py"
        py_path.write_text(python_text, encoding="utf-8")
        pys = pys_paths.get(stem)
        sidecar = {
            "version": 1,
            "pys": str(pys.resolve()) if pys else "",
            "py": str(py_path),
            "lines": maps.get(stem, []),
            "names": names.get(stem, {}),
            "hidePrefixes": hide_prefixes,
        }
        map_path = out_dir / f"{stem}.pysmap.json"
        map_path.write_text(json.dumps(sidecar), encoding="utf-8")
        map_files[stem] = str(map_path)

    # Same PYTHONPATH contract as run_source: temp modules first, then pys.deps sites.
    from .deps import (
        DepsError,
        load_deps,
        resolve_python_executable,
        resolve_site_paths,
    )

    prepend_parts: list[str] = [str(out_dir)]
    python_exe = sys.executable
    try:
        deps_config = load_deps(source_path, stop_at=workspace)
        if deps_config is not None:
            python_exe = resolve_python_executable(deps_config)
            site_paths = resolve_site_paths(
                deps_config,
                build="run",
                python=python_exe,
                quiet=True,
            )
            prepend_parts.extend(str(p) for p in site_paths)
    except DepsError as exc:
        return {
            "ok": False,
            "error": {
                "message": str(exc),
                "line": None,
                "column": None,
            },
        }

    return {
        "ok": True,
        "target": "python",
        "main": str(out_dir / f"{source_path.stem}.py"),
        "cwd": str(source_path.parent),
        "maps": map_files,
        "pythonpath_prepend": os.pathsep.join(prepend_parts),
        "python": python_exe,
    }


def _prepare_debug_javascript(
    *,
    source_path: Path,
    out_dir: Path,
    modules: dict[str, str],
    maps: dict[str, list],
    names: dict[str, dict],
    pys_paths: dict[str, Path],
    hide_prefixes: list[str],
) -> dict[str, Any]:
    """Emit .mjs + js-keyed pysmaps; resolve node/qode like run_source."""
    import shutil

    from .npm_deps import (
        NpmDepsError,
        qode_executable,
        resolve_npm_environment,
        run_dir_for_source,
    )

    emit_root = out_dir
    runtime_exe: str | None = None
    try:
        npm_root = resolve_npm_environment(source_path, install=True, quiet=True)
    except NpmDepsError as exc:
        return {
            "ok": False,
            "error": {
                "message": str(exc),
                "line": None,
                "column": None,
            },
        }
    if npm_root is not None:
        emit_root = run_dir_for_source(npm_root, source_path)
        runtime_exe = qode_executable(npm_root)

    if runtime_exe is None:
        runtime_exe = shutil.which("node")
    if runtime_exe is None:
        return {
            "ok": False,
            "error": {
                "message": (
                    "Node.js (`node`) was not found on PATH. Install Node.js "
                    "to debug --target javascript programs."
                ),
                "line": None,
                "column": None,
            },
        }

    map_files: dict[str, str] = {}
    for stem, js_text in modules.items():
        js_path = emit_root / f"{stem}.mjs"
        js_path.write_text(js_text, encoding="utf-8")
        pys = pys_paths.get(stem)
        sidecar = {
            "version": 1,
            "pys": str(pys.resolve()) if pys else "",
            "js": str(js_path),
            "lines": maps.get(stem, []),
            "names": names.get(stem, {}),
            "hidePrefixes": hide_prefixes,
        }
        map_path = emit_root / f"{stem}.pysmap.json"
        map_path.write_text(json.dumps(sidecar), encoding="utf-8")
        map_files[stem] = str(map_path)

    return {
        "ok": True,
        "target": "javascript",
        "main": str(emit_root / f"{source_path.stem}.mjs"),
        "cwd": str(source_path.parent),
        "maps": map_files,
        "runtimeExecutable": runtime_exe,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) >= 1 and argv[0] == "--prepare-debug":
        if len(argv) < 3:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "message": (
                            "Usage: python -m transpiler.ide "
                            "--prepare-debug <outdir> <file.pys> "
                            "[--target python|javascript]"
                        ),
                    }
                )
            )
            return 2
        out_dir = Path(argv[1])
        path = Path(argv[2])
        target = "python"
        rest = argv[3:]
        i = 0
        while i < len(rest):
            if rest[i] == "--target" and i + 1 < len(rest):
                target = rest[i + 1]
                i += 2
            else:
                i += 1
        result = prepare_debug(path, out_dir, target=target)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if len(argv) >= 1 and argv[0] == "--refactor-plan":
        return _cli_refactor_plan(argv[1:])
    if len(argv) < 1:
        print(
            json.dumps(
                {
                    "ok": False,
                    "message": (
                            "Usage: python -m transpiler.ide <file.pys> [symbol] "
                            "[--library-sources] [--stdin] "
                            "| <file.pys> --completions --line N --column N [--stdin] "
                            "| <file.pys> --usages <symbol> [--line N --column N] "
                            "| --refactor-plan <op> <file.pys> ..."
                        ),
                }
            )
        )
        return 2
    path = Path(argv[0])
    rest = list(argv[1:])
    allow_library_sources = False
    read_stdin = False
    filtered: list[str] = []
    for arg in rest:
        if arg == "--library-sources":
            allow_library_sources = True
        elif arg == "--stdin":
            read_stdin = True
        else:
            filtered.append(arg)
    if len(filtered) >= 1 and filtered[0] == "--completions":
        line = column = 1
        rest_flags = filtered[1:]
        i = 0
        while i < len(rest_flags):
            if rest_flags[i] == "--line" and i + 1 < len(rest_flags):
                line = int(rest_flags[i + 1])
                i += 2
            elif rest_flags[i] == "--column" and i + 1 < len(rest_flags):
                column = int(rest_flags[i + 1])
                i += 2
            else:
                i += 1
        from .completions import completions_for_file

        buffer_source = sys.stdin.read() if read_stdin else None
        result = completions_for_file(
            path, line=line, column=column, source=buffer_source
        )
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if len(filtered) >= 2 and filtered[0] == "--usages":
        symbol = filtered[1]
        line = column = None
        rest_flags = filtered[2:]
        i = 0
        while i < len(rest_flags):
            if rest_flags[i] == "--line" and i + 1 < len(rest_flags):
                line = int(rest_flags[i + 1])
                i += 2
            elif rest_flags[i] == "--column" and i + 1 < len(rest_flags):
                column = int(rest_flags[i + 1])
                i += 2
            else:
                i += 1
        usages = find_usages(path, symbol, line=line, column=column)
        print(
            json.dumps(
                {
                    "ok": True,
                    "symbol": symbol,
                    "usages": usages,
                }
            )
        )
        return 0
    try:
        # Diagnostics (no symbol) stay fail-closed. Symbol lookup may opt into
        # locked pys.deps imports via --library-sources (ADR-001).
        buffer_source = sys.stdin.read() if read_stdin else None
        result = analyze_file(
            path,
            allow_runtime_introspection=bool(allow_library_sources and filtered),
            source=buffer_source,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}, "validated_types": [], "symbols": {}}))
        return 1
    if filtered:
        symbol = filtered[0]
        loc = lookup_symbol(result, symbol)
        print(
            json.dumps(
                {
                    "ok": loc is not None,
                    "symbol": symbol,
                    "location": loc,
                    "types": result.get("variable_types"),
                    "validated_types": result.get("validated_types"),
                    "library_sources": allow_library_sources,
                }
            )
        )
    else:
        public = {k: v for k, v in result.items() if not k.startswith("_")}
        print(json.dumps(public))
    return 0 if result.get("ok") or bool(filtered) else 1


def _cli_refactor_plan(argv: list[str]) -> int:
    """``--refactor-plan <op> <file.pys> [--line N --column N] [op-args…]``."""
    from .refactor.plan import plan_to_dict

    if len(argv) < 2:
        print(json.dumps({"ok": False, "message": "Usage: --refactor-plan <op> <file.pys> ..."}))
        return 2
    op = argv[0]
    path = Path(argv[1])
    args = argv[2:]
    opts: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            opts[args[i][2:].replace("-", "_")] = args[i + 1]
            i += 2
        else:
            i += 1
    line = int(opts["line"]) if "line" in opts else None
    column = int(opts["column"]) if "column" in opts else None
    try:
        if op == "rename":
            from .refactor.rename import plan_rename

            plan = plan_rename(
                path,
                line=line or 1,
                column=column or 1,
                new_name=opts.get("new_name", ""),
            )
        elif op == "extract-variable":
            from .refactor.extract import plan_extract_variable

            plan = plan_extract_variable(
                path,
                start_line=int(opts.get("start_line", line or 1)),
                start_column=int(opts.get("start_column", column or 1)),
                end_line=int(opts.get("end_line", line or 1)),
                end_column=int(opts.get("end_column", column or 1)),
                new_name=opts.get("new_name", "extracted"),
                declare_type=opts.get("declare_type", "var"),
            )
        elif op == "extract-function":
            from .refactor.extract import plan_extract_function

            plan = plan_extract_function(
                path,
                start_line=int(opts.get("start_line", line or 1)),
                end_line=int(opts.get("end_line", line or 1)),
                new_name=opts.get("new_name", "extracted"),
                visibility=opts.get("visibility", ""),
            )
        elif op == "inline-variable":
            from .refactor.inline import plan_inline_variable

            plan = plan_inline_variable(path, line=line or 1, column=column or 1)
        elif op == "inline-function":
            from .refactor.inline import plan_inline_function

            plan = plan_inline_function(path, line=line or 1, column=column or 1)
        elif op == "safe-delete":
            from .refactor.safe_delete import plan_safe_delete

            plan = plan_safe_delete(path, line=line or 1, column=column or 1)
        elif op == "introduce-parameter":
            from .refactor.introduce_parameter import plan_introduce_parameter

            plan = plan_introduce_parameter(
                path,
                line=line or 1,
                column=column or 1,
                param_name=opts.get("param_name", "param"),
                param_type=opts.get("param_type", "int"),
            )
        elif op == "create-class":
            from .refactor.create_class import plan_create_class

            plan = plan_create_class(
                path,
                line=line or 1,
                column=column or 1,
            )
        else:
            print(json.dumps({"ok": False, "message": f"Unknown refactor op {op!r}"}))
            return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "message": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps(plan_to_dict(plan)))
    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
