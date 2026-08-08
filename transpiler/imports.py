"""`.pys` import resolution / visibility (shared by sem + emit).

Loads sibling modules via the AST parser (no legacy ``Parser``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from .ast_nodes import (
    AssignStmt,
    ClassDef,
    DataDef,
    EntityDef,
    EnumDef,
    FunctionDef,
    ImportStmt,
    InterfaceDef,
    Module,
    StructDef,
    TraitDef,
)
from .workspace import resolve_workspace_path, workspace_root_from_env


@dataclass
class ModuleInfo:
    path: Path
    python: str = ""
    exports: dict[str, str] = field(default_factory=dict)
    function_returns: dict[str, str] = field(default_factory=dict)
    function_params: dict[str, list[str]] = field(default_factory=dict)
    function_param_names: dict[str, list[str]] = field(default_factory=dict)
    constants: set[str] = field(default_factory=set)
    fixed_vars: set[str] = field(default_factory=set)
    types: dict[str, str] = field(default_factory=dict)
    class_parents: dict[str, str | None] = field(default_factory=dict)
    class_implements: dict[str, list[str]] = field(default_factory=dict)
    interfaces: set[str] = field(default_factory=set)
    class_members: dict[str, dict[str, str]] = field(default_factory=dict)
    class_methods: dict[str, dict[str, int]] = field(default_factory=dict)
    sealed_classes: set[str] = field(default_factory=set)
    class_decl_lines: dict[str, int] = field(default_factory=dict)
    symbol_locations: dict[str, tuple[Path, int, int]] = field(default_factory=dict)
    method_locations: dict[str, dict[str, tuple[Path, int, int]]] = field(default_factory=dict)
    structs: set[str] = field(default_factory=set)
    struct_type_fix: set[str] = field(default_factory=set)
    struct_fields: dict[str, list[str]] = field(default_factory=dict)
    struct_field_access: dict[str, dict[str, str]] = field(default_factory=dict)
    struct_field_types: dict[str, dict[str, str]] = field(default_factory=dict)
    struct_field_fix: dict[str, set[str]] = field(default_factory=dict)
    struct_field_defaults: dict[str, set[str]] = field(default_factory=dict)
    # type_name -> field_name -> (path, line, col)
    struct_field_locations: dict[str, dict[str, tuple[Path, int, int]]] = field(
        default_factory=dict
    )
    enums: set[str] = field(default_factory=set)
    enum_members: dict[str, list[str]] = field(default_factory=dict)
    enum_value_kinds: dict[str, str] = field(default_factory=dict)
    enum_member_values: dict[str, dict[str, str]] = field(default_factory=dict)
    # type_name -> member_name -> (path, line, col)
    enum_member_locations: dict[str, dict[str, tuple[Path, int, int]]] = field(
        default_factory=dict
    )

def _error(
    message: str,
    line_number: int = 1,
    code_line: str = "",
    column: int | None = None,
    *,
    code: str | None = None,
    suggested_fix: str | None = None,
    tips: list[str] | None = None,
) -> None:
    from .transpiler import TranspileError

    raise TranspileError(
        message,
        line_number,
        column,
        code_line,
        code=code,
        suggested_fix=suggested_fix,
        tips=tips,
    )


def pys_import_line(stmt: ImportStmt) -> str:
    if stmt.kind == "module":
        return f"import {stmt.module}"
    if stmt.kind == "as":
        return f"import {stmt.module} as {stmt.alias}"
    if stmt.kind == "all_from":
        return f"import all from {stmt.module}"
    if stmt.kind == "name_from":
        names = stmt.names or ([stmt.name] if stmt.name else [])
        return f"import {', '.join(names)} from {stmt.module}"
    return ""


@dataclass(frozen=True)
class _ParsedModule:
    """Everything the resolver needs from one file: metadata plus its import lines."""

    info: ModuleInfo
    imports: tuple[tuple[str, int], ...]


@lru_cache(maxsize=256)
def _parse_module(path: Path, source: str) -> _ParsedModule:
    """Parse a module once per (path, content).

    sem and emit each build their own resolver over the same files, so without
    this every module would be parsed several times per compile. Keying on the
    source text means an edited file is never served from a stale entry.
    """
    from .parse import parse_program

    tree = parse_program(source)
    imports: list[tuple[str, int]] = []
    for stmt in tree.body:
        if not isinstance(stmt, ImportStmt):
            continue
        line = pys_import_line(stmt)
        if line:
            imports.append((line, stmt.span.line if stmt.span else 1))
    return _ParsedModule(module_info_from_ast(path, tree), tuple(imports))


def clear_parse_cache() -> None:
    """Drop memoized module parses (only needed when caching itself is under test)."""
    _parse_module.cache_clear()


def extract_module_info(path: Path, source: str) -> ModuleInfo:
    """Build export / type metadata from an AST parse of ``source``."""
    from .parse import parse_program

    tree = parse_program(source)
    return module_info_from_ast(path, tree)


def module_info_from_ast(path: Path, tree: Module) -> ModuleInfo:
    exports: dict[str, str] = {}
    function_returns: dict[str, str] = {}
    function_params: dict[str, list[str]] = {}
    function_param_names: dict[str, list[str]] = {}
    constants: set[str] = set()
    fixed_vars: set[str] = set()
    types: dict[str, str] = {}
    class_parents: dict[str, str | None] = {}
    class_implements: dict[str, list[str]] = {}
    interfaces: set[str] = set()
    class_members: dict[str, dict[str, str]] = {}
    class_methods: dict[str, dict[str, int]] = {}
    sealed_classes: set[str] = set()
    class_decl_lines: dict[str, int] = {}
    symbol_locations: dict[str, tuple[Path, int, int]] = {}
    method_locations: dict[str, dict[str, tuple[Path, int, int]]] = {}
    structs: set[str] = set()
    struct_type_fix: set[str] = set()
    struct_fields: dict[str, list[str]] = {}
    struct_field_access: dict[str, dict[str, str]] = {}
    struct_field_types: dict[str, dict[str, str]] = {}
    struct_field_fix: dict[str, set[str]] = {}
    struct_field_defaults: dict[str, set[str]] = {}
    struct_field_locations: dict[str, dict[str, tuple[Path, int, int]]] = {}
    enums: set[str] = set()
    enum_members: dict[str, list[str]] = {}
    enum_value_kinds: dict[str, str] = {}
    enum_member_values: dict[str, dict[str, str]] = {}
    enum_member_locations: dict[str, dict[str, tuple[Path, int, int]]] = {}

    iface_names = {s.name for s in tree.body if isinstance(s, InterfaceDef)}

    for stmt in tree.body:
        line = stmt.span.line if stmt.span else 1
        col = stmt.span.column if stmt.span else 1
        if isinstance(stmt, FunctionDef):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            function_returns[stmt.name] = stmt.return_type
            function_params[stmt.name] = list(stmt.param_types)
            function_param_names[stmt.name] = list(stmt.params)
            symbol_locations[stmt.name] = (path, line, col)
        elif isinstance(stmt, InterfaceDef):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            interfaces.add(stmt.name)
            class_methods[stmt.name] = dict(stmt.method_arities)
            symbol_locations[stmt.name] = (path, line, col)
            class_decl_lines[stmt.name] = line
        elif isinstance(stmt, TraitDef):
            # Traits are exportable symbols for go-to, but not nominal types.
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            symbol_locations[stmt.name] = (path, line, col)
            class_decl_lines[stmt.name] = line
        elif isinstance(stmt, StructDef):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            symbol_locations[stmt.name] = (path, line, col)
            structs.add(stmt.name)
            if stmt.type_fix:
                struct_type_fix.add(stmt.name)
            order: list[str] = []
            access: dict[str, str] = {}
            ftypes: dict[str, str] = {}
            ffix: set[str] = set()
            fdefaults: set[str] = set()
            flocs: dict[str, tuple[Path, int, int]] = {}
            for f in stmt.fields:
                order.append(f.name)
                access[f.name] = "public"
                ftypes[f.name] = f.type_name
                if f.is_fix or stmt.type_fix:
                    ffix.add(f.name)
                if f.default is not None:
                    fdefaults.add(f.name)
                fl = f.span.line if f.span else line
                fc = f.span.column if f.span else col
                flocs[f.name] = (path, fl, fc)
            struct_fields[stmt.name] = order
            struct_field_access[stmt.name] = access
            struct_field_types[stmt.name] = ftypes
            struct_field_fix[stmt.name] = ffix
            struct_field_defaults[stmt.name] = fdefaults
            struct_field_locations[stmt.name] = flocs
        elif isinstance(stmt, DataDef):
            # `data` is indexed like a fully-fix struct for cross-file typing/copy.
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            symbol_locations[stmt.name] = (path, line, col)
            structs.add(stmt.name)
            struct_type_fix.add(stmt.name)
            order = []
            access = {}
            ftypes = {}
            ffix = set()
            fdefaults = set()
            flocs = {}
            for f in stmt.fields:
                order.append(f.name)
                access[f.name] = "public"
                ftypes[f.name] = f.type_name
                ffix.add(f.name)
                if f.default is not None:
                    fdefaults.add(f.name)
                fl = f.span.line if f.span else line
                fc = f.span.column if f.span else col
                flocs[f.name] = (path, fl, fc)
            struct_fields[stmt.name] = order
            struct_field_access[stmt.name] = access
            struct_field_types[stmt.name] = ftypes
            struct_field_fix[stmt.name] = ffix
            struct_field_defaults[stmt.name] = fdefaults
            struct_field_locations[stmt.name] = flocs
        elif isinstance(stmt, EnumDef):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            symbol_locations[stmt.name] = (path, line, col)
            class_decl_lines[stmt.name] = line
            enums.add(stmt.name)
            order_m: list[str] = []
            mvals: dict[str, str] = {}
            mlocs: dict[str, tuple[Path, int, int]] = {}
            has_vals = [m.value is not None for m in stmt.members]
            kind = "auto"
            if has_vals and all(has_vals):
                from .ast_nodes import Literal as AstLiteral

                kinds = {
                    m.value.kind
                    for m in stmt.members
                    if isinstance(m.value, AstLiteral)
                }
                kind = next(iter(kinds), "auto") if len(kinds) == 1 else "auto"
            for m in stmt.members:
                order_m.append(m.name)
                ml = m.span.line if m.span else line
                mc = m.span.column if m.span else col
                mlocs[m.name] = (path, ml, mc)
                if m.value is not None and hasattr(m.value, "text"):
                    mvals[m.name] = m.value.text  # type: ignore[attr-defined]
            enum_members[stmt.name] = order_m
            enum_value_kinds[stmt.name] = kind
            enum_member_values[stmt.name] = mvals
            enum_member_locations[stmt.name] = mlocs
        elif isinstance(stmt, ClassDef):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            symbol_locations[stmt.name] = (path, line, col)
            class_decl_lines[stmt.name] = line
            if stmt.sealed or getattr(stmt, "closed", False):
                sealed_classes.add(stmt.name)
            parent: str | None = None
            implements: list[str] = []
            for b in stmt.bases:
                if b in iface_names:
                    implements.append(b)
                elif parent is None:
                    parent = b
                else:
                    implements.append(b)
            class_parents[stmt.name] = parent
            if implements:
                class_implements[stmt.name] = implements
            members: dict[str, str] = {}
            methods: dict[str, int] = {}
            mlocs: dict[str, tuple[Path, int, int]] = {}
            for f in stmt.fields:
                members[f.name] = f.access or "module"
            for m in stmt.methods:
                methods[m.name] = len(m.params)
                members[m.name] = m.access or "module"
                ml = m.span.line if m.span else line
                mc = m.span.column if m.span else col
                mlocs[m.name] = (path, ml, mc)
            class_members[stmt.name] = members
            class_methods[stmt.name] = methods
            method_locations[stmt.name] = mlocs
        elif isinstance(stmt, EntityDef):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            symbol_locations[stmt.name] = (path, line, col)
            class_decl_lines[stmt.name] = line
            class_parents[stmt.name] = stmt.parent or None
            members = {}
            methods = {}
            mlocs = {}
            for f in stmt.fields:
                members[f.name] = f.access or "module"
            for m in stmt.methods:
                methods[m.name] = len(m.params)
                members[m.name] = m.access or "module"
                ml = m.span.line if m.span else line
                mc = m.span.column if m.span else col
                mlocs[m.name] = (path, ml, mc)
            class_members[stmt.name] = members
            class_methods[stmt.name] = methods
            method_locations[stmt.name] = mlocs
        elif isinstance(stmt, AssignStmt) and (stmt.is_const or stmt.is_fix):
            vis = stmt.visibility or "module"
            exports[stmt.name] = vis
            if stmt.is_const:
                constants.add(stmt.name)
            if stmt.is_fix:
                fixed_vars.add(stmt.name)
            if stmt.declare_type and stmt.declare_type not in {"var", "const", "fix"}:
                types[stmt.name] = stmt.declare_type
            symbol_locations[stmt.name] = (path, line, col)

    return ModuleInfo(
        path=path,
        exports=exports,
        function_returns=function_returns,
        function_params=function_params,
        function_param_names=function_param_names,
        constants=constants,
        fixed_vars=fixed_vars,
        types=types,
        class_parents=class_parents,
        class_implements=class_implements,
        interfaces=interfaces,
        class_members=class_members,
        class_methods=class_methods,
        sealed_classes=sealed_classes,
        class_decl_lines=class_decl_lines,
        symbol_locations=symbol_locations,
        method_locations=method_locations,
        structs=structs,
        struct_type_fix=struct_type_fix,
        struct_fields=struct_fields,
        struct_field_access=struct_field_access,
        struct_field_types=struct_field_types,
        struct_field_fix=struct_field_fix,
        struct_field_defaults=struct_field_defaults,
        struct_field_locations=struct_field_locations,
        enums=enums,
        enum_members=enum_members,
        enum_value_kinds=enum_value_kinds,
        enum_member_values=enum_member_values,
        enum_member_locations=enum_member_locations,
    )


class ImportResolver:
    """Resolve PYS / external imports and track visibility for sem + emit."""

    def __init__(
        self,
        source: str,
        *,
        source_path: Path | None = None,
        module_cache: dict[Path, ModuleInfo] | None = None,
        transpiling: set[Path] | None = None,
        allow_runtime_introspection: bool = False,
    ) -> None:
        self.source = source
        self.source_path = source_path.resolve() if source_path is not None else None
        workspace_root = workspace_root_from_env()
        if self.source_path is not None and workspace_root is not None:
            contained = resolve_workspace_path(self.source_path, workspace_root)
            if contained is None:
                from .transpiler import TranspileError

                raise TranspileError(
                    f"Source path resolves outside the workspace: {self.source_path}"
                )
            self.source_path = contained
        self.module_cache = module_cache if module_cache is not None else {}
        self.transpiling = transpiling if transpiling is not None else set()
        self.allow_runtime_introspection = allow_runtime_introspection
        self.exports: dict[str, str] = {}
        self.function_returns: dict[str, str] = {}
        self.function_params: dict[str, list[str]] = {}
        self.function_param_names: dict[str, list[str]] = {}
        self.constants: set[str] = set()
        self.fixed_vars: set[str] = set()
        self.imported_names: set[str] = set()
        self.declared_variables: set[str] = set()
        self.seen_module_names: dict[str, tuple[str, str, bool]] = {}
        self.variable_types: dict[str, str] = {}
        self.class_parents: dict[str, str | None] = {}
        self.class_implements: dict[str, list[str]] = {}
        self.interfaces: set[str] = set()
        self.class_members: dict[str, dict[str, str]] = {}
        self.class_methods: dict[str, dict[str, int]] = {}
        self.sealed_classes: set[str] = set()
        self.imported_modules: dict[str, str] = {}
        self.type_modules: dict[str, str] = {}
        self.type_definitions: dict[str, tuple[Path, int, int]] = {}
        self.symbol_locations: dict[str, tuple[Path, int, int]] = {}
        self.method_locations: dict[str, dict[str, tuple[Path, int, int]]] = {}
        self.structs: set[str] = set()
        self.struct_type_fix: set[str] = set()
        self.struct_fields: dict[str, list[str]] = {}
        self.struct_field_access: dict[str, dict[str, str]] = {}
        self.struct_field_types: dict[str, dict[str, str]] = {}
        self.struct_field_fix: dict[str, set[str]] = {}
        self.struct_field_defaults: dict[str, set[str]] = {}
        self.struct_field_locations: dict[str, dict[str, tuple[Path, int, int]]] = {}
        self.enums: set[str] = set()
        self.enum_members: dict[str, list[str]] = {}
        self.enum_value_kinds: dict[str, str] = {}
        self.enum_member_values: dict[str, dict[str, str]] = {}
        self.enum_member_locations: dict[str, dict[str, tuple[Path, int, int]]] = {}
        self._deps_site_paths: list[Path] | None = None
        self._deps_site_paths_loaded = False

        if self.source_path is not None:
            info = _parse_module(self.source_path, source).info
            self.exports = dict(info.exports)
            self.function_returns = dict(info.function_returns)
            self.function_params = {
                name: list(params) for name, params in info.function_params.items()
            }
            self.function_param_names = {
                name: list(names) for name, names in info.function_param_names.items()
            }
            self.constants = set(info.constants)
            self.fixed_vars = set(info.fixed_vars)
            self.class_parents = dict(info.class_parents)
            self.class_implements = dict(info.class_implements)
            self.interfaces = set(info.interfaces)
            self.class_members = dict(info.class_members)
            self.class_methods = dict(info.class_methods)
            self.sealed_classes = set(info.sealed_classes)
            self.symbol_locations = dict(info.symbol_locations)
            self.method_locations = {c: dict(m) for c, m in info.method_locations.items()}
            self.structs = set(info.structs)
            self.struct_type_fix = set(info.struct_type_fix)
            self.struct_fields = {k: list(v) for k, v in info.struct_fields.items()}
            self.struct_field_access = {k: dict(v) for k, v in info.struct_field_access.items()}
            self.struct_field_types = {k: dict(v) for k, v in info.struct_field_types.items()}
            self.struct_field_fix = {k: set(v) for k, v in info.struct_field_fix.items()}
            self.struct_field_defaults = {k: set(v) for k, v in info.struct_field_defaults.items()}
            self.struct_field_locations = {
                k: dict(v) for k, v in info.struct_field_locations.items()
            }
            self.enums = set(info.enums)
            self.enum_members = {k: list(v) for k, v in info.enum_members.items()}
            self.enum_value_kinds = dict(info.enum_value_kinds)
            self.enum_member_values = {
                k: dict(v) for k, v in info.enum_member_values.items()
            }
            self.enum_member_locations = {
                k: dict(v) for k, v in info.enum_member_locations.items()
            }
            for name, t in info.types.items():
                self.variable_types[name] = t
            self.declared_variables |= set(info.exports)

    def _deps_paths(self) -> list[Path]:
        if self._deps_site_paths_loaded:
            return self._deps_site_paths or []
        self._deps_site_paths_loaded = True
        self._deps_site_paths = []
        if self.source_path is None:
            return []
        from .deps import DepsError, ensure_site_paths_for

        try:
            # Read-only: never pip-install during transpile/IDE validation.
            # Run (transpiler.run_source) still installs via resolve_site_paths.
            self._deps_site_paths = ensure_site_paths_for(
                self.source_path, build="run", quiet=True, install=False
            )
        except DepsError:
            self._deps_site_paths = []
        return self._deps_site_paths

    def _find_pys_module_path(self, module_ref: str) -> Path | None:
        ref = module_ref.strip().strip("\"'")
        if not ref:
            return None
        path = Path(ref)
        pathish = (
            "/" in ref
            or "\\" in ref
            or ref.startswith(".")
            or path.suffix.lower() == ".pys"
        )
        if not pathish and "." in ref:
            # Dotted Python-style names are not .pys file paths.
            return None
        if path.suffix.lower() != ".pys":
            path = path.with_suffix(".pys")
        if not path.is_absolute():
            base = self.source_path.parent if self.source_path is not None else Path.cwd()
            candidate = (base / path)
            workspace_root = workspace_root_from_env()
            if workspace_root is not None:
                resolved = resolve_workspace_path(candidate, workspace_root)
                if resolved is not None:
                    return resolved
            else:
                try:
                    return candidate.resolve(strict=True)
                except OSError:
                    pass
            # Bare module (e.g. `config`): resolve among same-package peers under
            # pys.toml [source_roots] so tests/ can import src/ without relative paths.
            if self.source_path is not None and not (
                "/" in ref or "\\" in ref or ref.startswith(".")
            ):
                from .project_manifest import package_peer_files

                stem = path.stem
                here = self.source_path.resolve()
                for peer in package_peer_files(here):
                    if peer.stem == stem and peer != here:
                        return peer
            return None

        workspace_root = workspace_root_from_env()
        if workspace_root is not None:
            return resolve_workspace_path(path, workspace_root)
        try:
            path = path.resolve(strict=True)
        except OSError:
            return None
        return path

    def _same_package(self, other: Path) -> bool:
        # source_path / ModuleInfo.path are already resolved; re-resolve here was
        # hundreds of filesystem hits per analyze with no semantic gain.
        # With pys.toml [source_roots], package identity is root-relative (ADR-017).
        if self.source_path is None:
            return False
        from .project_manifest import same_package

        return same_package(self.source_path, other)

    def _load_module(self, module_path: Path) -> ModuleInfo:
        from .transpiler import TranspileError

        path = module_path.resolve()
        if path in self.module_cache:
            return self.module_cache[path]
        if path in self.transpiling:
            raise TranspileError(f"Circular import involving '{path.name}'.")
        self.transpiling.add(path)
        try:
            source = path.read_text(encoding="utf-8")
            parsed = _parse_module(path, source)
            info = parsed.info
            # Recurse into the child's imports so transpile_with_modules discovers
            # the full dependency graph.
            child = ImportResolver(
                source,
                source_path=path,
                module_cache=self.module_cache,
                transpiling=self.transpiling,
                allow_runtime_introspection=self.allow_runtime_introspection,
            )
            for line, line_number in parsed.imports:
                child.translate_import_statement(line, line_number, line)
            self.module_cache[path] = info
            return info
        finally:
            self.transpiling.discard(path)

    def _visible_exports_for_import(self, info: ModuleInfo) -> list[str]:
        names: list[str] = []
        for name, visibility in info.exports.items():
            if visibility == "module":
                continue
            if visibility == "package" and not self._same_package(info.path):
                continue
            if visibility in {"package", "global"}:
                names.append(name)
        return sorted(names)

    def _record_seen_module_exports(self, info: ModuleInfo, imported: list[str]) -> None:
        visible = set(self._visible_exports_for_import(info))
        imported_set = set(imported)
        for name in imported_set:
            self.imported_names.add(name)
            self.declared_variables.add(name)
            if name in info.types:
                self.variable_types[name] = info.types[name]
            if name in info.function_returns:
                self.function_returns[name] = info.function_returns[name]
            if name in info.function_params:
                self.function_params[name] = list(info.function_params[name])
            if name in info.function_param_names:
                self.function_param_names[name] = list(info.function_param_names[name])
            if name in info.constants:
                self.constants.add(name)
            if name in info.fixed_vars:
                self.fixed_vars.add(name)
            if name in info.symbol_locations:
                self.symbol_locations[name] = info.symbol_locations[name]
            self.seen_module_names.pop(name, None)
        for name, visibility in info.exports.items():
            accessible = name in visible
            if name in imported_set:
                continue
            if name in self.imported_names or name in self.exports:
                continue
            self.seen_module_names[name] = (info.path.name, visibility, accessible)
        to_merge: set[str] = set(imported_set)
        merged: set[str] = set()
        while to_merge:
            name = to_merge.pop()
            if name in merged:
                continue
            merged.add(name)
            if name in info.class_parents:
                self.class_parents[name] = info.class_parents[name]
                parent = info.class_parents[name]
                if parent and parent not in merged:
                    to_merge.add(parent)
            if name in info.class_implements:
                self.class_implements[name] = info.class_implements[name]
                for iface in info.class_implements[name]:
                    if iface not in merged:
                        to_merge.add(iface)
            if name in info.interfaces:
                self.interfaces.add(name)
            if name in info.class_members:
                self.class_members[name] = info.class_members[name]
            if name in info.class_methods:
                self.class_methods[name] = info.class_methods[name]
            if name in info.method_locations:
                self.method_locations[name] = dict(info.method_locations[name])
            if name in info.sealed_classes:
                self.sealed_classes.add(name)
            if name in info.structs:
                self.structs.add(name)
                if name in info.struct_type_fix:
                    self.struct_type_fix.add(name)
                self.struct_fields[name] = list(info.struct_fields.get(name, []))
                self.struct_field_access[name] = dict(info.struct_field_access.get(name, {}))
                self.struct_field_types[name] = dict(info.struct_field_types.get(name, {}))
                self.struct_field_fix[name] = set(info.struct_field_fix.get(name, set()))
                self.struct_field_defaults[name] = set(
                    info.struct_field_defaults.get(name, set())
                )
                self.struct_field_locations[name] = dict(
                    info.struct_field_locations.get(name, {})
                )
            if name in info.enums:
                self.enums.add(name)
                self.enum_members[name] = list(info.enum_members.get(name, []))
                self.enum_value_kinds[name] = info.enum_value_kinds.get(name, "auto")
                self.enum_member_values[name] = dict(
                    info.enum_member_values.get(name, {})
                )
                self.enum_member_locations[name] = dict(
                    info.enum_member_locations.get(name, {})
                )
            if name in info.class_decl_lines:
                self.type_definitions[name] = (info.path, info.class_decl_lines[name], 1)

    def _translate_external_import(
        self,
        module_ref: str,
        names: list[str] | None,
        line_number: int,
        raw_line: str,
        alias: str | None = None,
    ) -> str | None:
        from .deps import is_external_python_module, lock_declares_module

        ref = module_ref.strip().strip("\"'")
        if ref.lower().endswith(".pys"):
            return None
        present = is_external_python_module(ref, self._deps_paths())
        if (
            not present
            and not self.allow_runtime_introspection
            and self.source_path is not None
        ):
            present = lock_declares_module(self.source_path, ref)
        if not present:
            return None

        top = ref.split(".", 1)[0]
        local = alias or top
        self.imported_names.add(local)
        self.declared_variables.add(local)
        self.imported_modules[local] = ref if alias else top
        self.variable_types[local] = f"module:{ref if alias else top}"

        if names is None:
            if re.fullmatch(r"import\s+all\s+from\s+.+", raw_line.strip()):
                return f"from {ref} import *"
            if alias:
                return f"import {ref} as {alias}"
            return f"import {ref}"

        for name in names:
            self.imported_names.add(name)
            self.declared_variables.add(name)
            self.type_modules.setdefault(name, ref)
            self.variable_types[name] = "type"
        return f"from {ref} import {', '.join(names)}"

    def translate_import_statement(
        self,
        line: str,
        line_number: int = 1,
        raw_line: str | None = None,
    ) -> str | None:
        raw_line = raw_line if raw_line is not None else line
        import_all = re.fullmatch(r"import\s+all\s+from\s+(?P<module>.+)", line)
        import_name = re.fullmatch(
            r"import\s+(?P<names>[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s+from\s+(?P<module>.+)",
            line,
        )
        import_as = re.fullmatch(
            r"import\s+(?P<module>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s+as\s+(?P<alias>[A-Za-z_]\w*)",
            line,
        )
        import_module = re.fullmatch(r"import\s+(?P<module>.+)", line)
        if not (import_all or import_name or import_as or import_module):
            return None

        if self.source_path is None:
            return None

        alias: str | None = None
        if import_all:
            module_ref = import_all.group("module")
            names = None
            is_import_all = True
        elif import_name:
            raw_names = import_name.group("names")
            # `import all from …` is handled above; guard if regex ever overlaps.
            if raw_names.strip() == "all":
                return None
            module_ref = import_name.group("module")
            names = [n.strip() for n in raw_names.split(",") if n.strip()]
            is_import_all = False
        elif import_as:
            module_ref = import_as.group("module")
            names = None
            is_import_all = False
            alias = import_as.group("alias")
        elif import_module:
            module_ref = import_module.group("module")
            names = None
            is_import_all = False
        else:
            return None

        pys_path = self._find_pys_module_path(module_ref)
        if pys_path is None:
            external = self._translate_external_import(
                module_ref, names, line_number, raw_line, alias=alias
            )
            if external is not None:
                return external
            _error(
                f"Cannot find module '{module_ref}'. Expected a .pys file next to this source "
                f"or a Python package from pys.deps / the standard library.",
                line_number,
                raw_line.rstrip(),
            )

        if alias is not None:
            _error(
                "Alias imports (`import … as …`) are only supported for Python packages "
                "from pys.deps / the standard library.",
                line_number,
                raw_line.rstrip(),
            )

        info = self._load_module(pys_path)
        visible = self._visible_exports_for_import(info)
        module_name = pys_path.stem

        if names is None:
            if not visible:
                _error(
                    f"Module '{pys_path.name}' has no global/package exports visible here.",
                    line_number,
                    raw_line.rstrip(),
                )
            self._record_seen_module_exports(info, visible)
            return f"from {module_name} import {', '.join(visible)}"

        selected: list[str] = []
        for name in names:
            if name not in info.exports:
                _error(
                    f"'{name}' is not defined in module '{pys_path.name}'.",
                    line_number,
                    raw_line.rstrip(),
                )
            visibility = info.exports[name]
            if name not in visible:
                where = "this package" if visibility == "package" else "this module"
                msg = (
                    f"Cannot import '{name}' from '{pys_path.name}': it is {visibility}-scoped "
                    f"(visible only in {where})."
                )
                suggested: str | None = None
                tips: list[str] | None = None
                err_code: str | None = None
                if visibility == "package" and self.source_path is not None:
                    from .project_manifest import (
                        package_mismatch_diagnostic,
                        package_identity,
                        source_roots_for,
                    )

                    hint = package_mismatch_diagnostic(
                        importer=self.source_path,
                        declaree=pys_path,
                        symbol=name,
                    )
                    if hint:
                        msg = f"{msg}\n{hint}"
                        err_code = "pys.package-mismatch"
                        tips = [
                            "Place the test under the mirrored path for the same package "
                            "(see pys.toml [source_roots])."
                        ]
                        roots = source_roots_for(self.source_path)
                        id_dec = package_identity(pys_path, roots) if roots else None
                        id_imp = package_identity(self.source_path, roots) if roots else None
                        if roots and id_dec is not None and id_imp is not None:
                            suggested_path = (
                                id_imp.root_path / id_dec.rel_dir / self.source_path.name
                            )
                            try:
                                suggested = suggested_path.relative_to(
                                    roots.project_root
                                ).as_posix()
                            except ValueError:
                                suggested = suggested_path.as_posix()
                _error(
                    msg,
                    line_number,
                    raw_line.rstrip(),
                    code=err_code,
                    suggested_fix=suggested,
                    tips=tips,
                )
            selected.append(name)
        self._record_seen_module_exports(info, selected)
        return f"from {module_name} import {', '.join(selected)}"

    # Back-compat for callers that still use the legacy method name.
    def _translate_import_statement(
        self, line: str, line_number: int = 1, raw_line: str | None = None
    ) -> str | None:
        return self.translate_import_statement(line, line_number, raw_line)


def make_resolver(
    source: str,
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
) -> ImportResolver:
    return ImportResolver(
        source,
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )


def translate_import(resolver: Any, line: str, line_number: int = 1) -> str | None:
    return resolver.translate_import_statement(line, line_number, line)


def discover_imported_modules(
    source_path: Path,
    *,
    allow_runtime_introspection: bool = False,
) -> dict[Path, ModuleInfo]:
    """Parse entry file imports (recursively) and return the module cache."""
    source_path = source_path.resolve()
    source = source_path.read_text(encoding="utf-8")
    resolver = ImportResolver(
        source,
        source_path=source_path,
        allow_runtime_introspection=allow_runtime_introspection,
    )
    for line, line_number in _parse_module(source_path, source).imports:
        resolver.translate_import_statement(line, line_number, line)
    return resolver.module_cache
