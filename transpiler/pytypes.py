"""Introspect return types from installed Python packages (pys.deps site paths)."""

from __future__ import annotations

import ast
import importlib
import re
import sys
import types
import typing
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, get_args, get_origin


@dataclass
class InferredReturn:
    """Best-effort PYS type for a library/user call."""

    pys_type: str
    element_type: str | None = None
    from_external: bool = False
    weak: bool = False  # container/API with no precise element/shape typing


def _annotation_to_pys_type(annotation: Any) -> str | None:
    """Map a Python typing annotation to a simple PYS type name."""
    if annotation is None or annotation is type(None):
        return None

    if isinstance(annotation, str):
        return _string_annotation_to_pys_type(annotation)

    origin = get_origin(annotation)
    if origin is not None:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if origin in {typing.Union, getattr(types, "UnionType", ())}:
            names = [_annotation_to_pys_type(a) for a in args]
            names = [n for n in names if n]
            return _prefer_canonical_type(names) if names else None
        origin_name = getattr(origin, "__name__", "") or ""
        if origin in {list} or origin_name in {"list", "List"}:
            return "list"
        if origin in {dict} or origin_name in {"dict", "Dict"}:
            return "dict"
        if origin in {tuple} or origin_name in {"tuple", "Tuple"}:
            return "tuple"
        if origin in {set} or origin_name in {"set", "Set"}:
            return "set"
        if args:
            return _annotation_to_pys_type(args[0])
        return origin_name or None

    if isinstance(annotation, type):
        return annotation.__name__

    name = getattr(annotation, "__name__", None)
    return name if isinstance(name, str) else None


def _annotation_element_type(annotation: Any) -> str | None:
    """Element/value type for List[T], Sequence[T], etc."""
    if annotation is None:
        return None
    if isinstance(annotation, str):
        text = annotation.strip()
        for container in ("List", "list", "Sequence", "Iterable", "Tuple", "tuple"):
            if text.startswith(container + "[") and text.endswith("]"):
                inner = text[len(container) + 1 : -1]
                first = _split_top_level_commas(inner)[0] if inner else ""
                if first == "..." or not first:
                    return None
                return _string_annotation_to_pys_type(first)
        return None
    origin = get_origin(annotation)
    if origin is None:
        return None
    args = [a for a in get_args(annotation) if a is not type(None)]
    if not args:
        return None
    origin_name = getattr(origin, "__name__", "") or ""
    if origin in {list, tuple, set} or origin_name in {
        "list",
        "List",
        "tuple",
        "Tuple",
        "set",
        "Set",
        "Sequence",
        "Iterable",
    }:
        return _annotation_to_pys_type(args[0])
    if origin in {dict} or origin_name in {"dict", "Dict"}:
        if len(args) >= 2:
            return _annotation_to_pys_type(args[1])
    return None


def _usable_pys_element(name: str | None) -> str | None:
    """Keep only element types that are meaningful in PYS; drop RowType/Any/etc."""
    if not name:
        return None
    if name in {"int", "float", "char", "string", "bool", "list", "dict", "tuple", "set"}:
        return name
    return None


def _element_type_heuristic(recv_type: str | None, method_name: str | None) -> str | None:
    """When annotations lack element types, use common library conventions."""
    if not method_name:
        return None
    name = method_name.lower()
    if name in {"fetchall", "fetchmany"}:
        if recv_type and "dict" in recv_type.lower():
            return "dict"
        return "tuple"
    if name == "fetchone":
        if recv_type and "dict" in recv_type.lower():
            return "dict"
        return "tuple"
    return None


def _usage_tips_for(pys_type: str, element_type: str | None, var_name: str = "result") -> list[str]:
    tips: list[str] = []
    if pys_type == "list" and element_type:
        tips.append(
            f"Iterate with a typed loop variable: `loop ({element_type} x in {var_name}) {{ ... }}`"
        )
    elif pys_type in {"list", "dict", "tuple", "set"}:
        tips.append(
            f"Prefer declaring how you use `{var_name}` with an explicit element/row type when possible."
        )
    return tips


def _string_annotation_to_pys_type(text: str) -> str | None:
    text = text.strip()
    if not text or text == "None":
        return None
    # Union[A, B, C]
    union = re.fullmatch(r"Union\[(.+)\]", text)
    if union:
        parts = _split_top_level_commas(union.group(1))
        names = [_string_annotation_to_pys_type(p) for p in parts]
        names = [n for n in names if n and n != "None"]
        return _prefer_canonical_type(names) if names else None
    optional = re.fullmatch(r"Optional\[(.+)\]", text)
    if optional:
        return _string_annotation_to_pys_type(optional.group(1))
    for container, mapped in (
        ("List", "list"),
        ("list", "list"),
        ("Dict", "dict"),
        ("dict", "dict"),
        ("Tuple", "tuple"),
        ("tuple", "tuple"),
        ("Set", "set"),
        ("set", "set"),
    ):
        if text.startswith(container + "[") and text.endswith("]"):
            return mapped
    # Qualified name → last segment
    if "." in text and re.fullmatch(r"[A-Za-z_][\w.]*", text):
        return text.rsplit(".", 1)[-1]
    if re.fullmatch(r"[A-Za-z_]\w*", text):
        return text
    return None


def _split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(depth - 1, 0)
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _prefer_canonical_type(names: list[str]) -> str:
    """Prefer unprefixed class names (MySQLConnection over PooledMySQLConnection)."""
    if len(names) == 1:
        return names[0]
    # Prefer a name that is a suffix of another (MySQLConnection vs CMySQLConnection)
    plain = [n for n in names if not n.startswith(("C", "Pooled", "Async"))]
    if len(plain) == 1:
        return plain[0]
    if plain:
        return min(plain, key=len)
    return min(names, key=len)


def _with_sys_path(site_paths: list[Path]):
    class _Ctx:
        def __enter__(self):
            self.added = []
            for path in reversed(site_paths):
                text = str(path)
                if text not in sys.path:
                    sys.path.insert(0, text)
                    self.added.append(text)
            return self

        def __exit__(self, *args):
            for text in self.added:
                try:
                    sys.path.remove(text)
                except ValueError:
                    pass

    return _Ctx()


def _get_return_annotation(obj: Any) -> Any:
    annotations = getattr(obj, "__annotations__", None) or {}
    if "return" in annotations:
        return annotations["return"]
    # unwrap classmethod/staticmethod
    func = getattr(obj, "__func__", None)
    if func is not None:
        annotations = getattr(func, "__annotations__", None) or {}
        if "return" in annotations:
            return annotations["return"]
    return None


def resolve_attr_chain(root: Any, parts: list[str]) -> Any | None:
    current = root
    for part in parts:
        if current is None:
            return None
        try:
            current = getattr(current, part)
        except Exception:
            return None
    return current


def _path_under_sites(path: Path, site_paths: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for site in site_paths:
        try:
            resolved.relative_to(Path(site).resolve())
            return True
        except ValueError:
            continue
    return False


def _site_has_module(module_name: str, site_paths: list[Path]) -> bool:
    parts = module_name.split(".")
    for site in site_paths:
        base = Path(site).joinpath(*parts)
        if (base / "__init__.py").is_file() or base.with_suffix(".py").is_file():
            return True
        for suffix in (".pyd", ".so", ".dylib"):
            if base.with_suffix(suffix).is_file():
                return True
        parent = base.parent
        stem = base.name
        if parent.is_dir():
            for child in parent.iterdir():
                if child.is_file() and child.name.startswith(stem + ".") and (
                    child.suffix in {".pyd", ".so", ".dylib"} or ".so." in child.name
                ):
                    return True
    return False


def _drop_module_tree(module_name: str) -> None:
    # Drop the whole top-level package tree so a stub site package can replace
    # a previously imported real install (common when acceptance tests load
    # real deps before a unit test stubs the same name).
    root = module_name.split(".", 1)[0]
    prefix = root + "."
    for key in list(sys.modules):
        if key == root or key.startswith(prefix):
            del sys.modules[key]


def _is_stdlib_path(path: Path) -> bool:
    """True for interpreter-owned stdlib files, excluding site-packages."""
    import sysconfig

    try:
        resolved = path.resolve()
    except OSError:
        return False

    for key in ("purelib", "platlib"):
        raw = sysconfig.get_path(key)
        if not raw:
            continue
        try:
            resolved.relative_to(Path(raw).resolve())
            return False
        except ValueError:
            continue

    raw_stdlib = sysconfig.get_path("stdlib")
    if not raw_stdlib:
        return False
    try:
        resolved.relative_to(Path(raw_stdlib).resolve())
        return True
    except ValueError:
        return False


def import_module_from_sites(
    module_name: str,
    site_paths: list[Path],
    *,
    allow_runtime_imports: bool = True,
) -> ModuleType | None:
    """Import a module for typing, preferring deps sites; never trust workspace shadows.

    - If the module exists under ``site_paths``, import from there.
    - Otherwise allow stdlib / interpreter-prefix modules only (F3).
    """
    in_sites = bool(site_paths) and _site_has_module(module_name, site_paths)
    if in_sites and not allow_runtime_imports:
        return None

    def _accept(module: ModuleType) -> ModuleType | None:
        file = getattr(module, "__file__", None)
        if file is None:
            return module  # built-in / namespace without file
        path = Path(file)
        if in_sites and _path_under_sites(path, site_paths):
            return module
        if _is_stdlib_path(path):
            return module
        return None

    path_ctx = _with_sys_path(site_paths) if in_sites else _with_sys_path([])
    with path_ctx:
        try:
            if module_name in sys.modules:
                existing = sys.modules[module_name]
                file = getattr(existing, "__file__", None)
                if in_sites:
                    if not file or not _path_under_sites(Path(file), site_paths):
                        _drop_module_tree(module_name)
                    else:
                        return existing
                else:
                    accepted = _accept(existing)
                    if accepted is not None:
                        return accepted
                    # Drop a workspace-shadowed module so a later trusted import can win.
                    _drop_module_tree(module_name)
            module = importlib.import_module(module_name)
            accepted = _accept(module)
            if accepted is None:
                _drop_module_tree(module_name)
            return accepted
        except Exception:
            return None


def infer_call_return_type(
    receiver_expr: str,
    method_name: str | None,
    *,
    variable_types: dict[str, str],
    imported_modules: dict[str, str],
    site_paths: list[Path],
    type_modules: dict[str, str],
    allow_runtime_imports: bool = True,
) -> str | None:
    info = infer_call_return_info(
        receiver_expr,
        method_name,
        variable_types=variable_types,
        imported_modules=imported_modules,
        site_paths=site_paths,
        type_modules=type_modules,
        allow_runtime_imports=allow_runtime_imports,
    )
    return info.pys_type if info else None


def infer_call_return_info(
    receiver_expr: str,
    method_name: str | None,
    *,
    variable_types: dict[str, str],
    imported_modules: dict[str, str],
    site_paths: list[Path],
    type_modules: dict[str, str],
    allow_runtime_imports: bool = True,
) -> InferredReturn | None:
    """Infer PYS type (+ optional element type) for a library/module call."""
    recv = receiver_expr.strip()

    def _pack(pys: str | None, ann: Any, recv_type: str | None, external: bool) -> InferredReturn | None:
        if not pys:
            return None
        element = _usable_pys_element(_annotation_element_type(ann)) or _element_type_heuristic(
            recv_type, method_name
        )
        weak = False
        if external and pys in {"list", "dict", "tuple", "set"}:
            # Containers from Python libs are treated as weakly typed at the PYS boundary.
            weak = True
        return InferredReturn(
            pys_type=pys,
            element_type=element,
            from_external=external,
            weak=weak,
        )

    # mysql.connector.connect → module attr chain ending in call target
    if method_name is None:
        if "." not in recv:
            return None
        head, *rest = recv.split(".")
        mod_name = imported_modules.get(head)
        if not mod_name:
            return None
        module = import_module_from_sites(
            mod_name,
            site_paths,
            allow_runtime_imports=allow_runtime_imports,
        )
        if module is None:
            return None
        target = resolve_attr_chain(module, rest)
        ann = _get_return_annotation(target)
        pys = _annotation_to_pys_type(ann)
        if pys:
            # Do not record container names as type_modules origins.
            if pys not in {"list", "dict", "tuple", "set", "int", "float", "bool", "str", "string"}:
                _remember_type_origin(pys, target, type_modules)
            return _pack(pys, ann, None, external=True)
        return None

    # mydb.cursor → instance method; receiver has a known type
    recv_type = variable_types.get(recv)
    if recv_type:
        origin_mod = type_modules.get(recv_type)
        if origin_mod:
            module = import_module_from_sites(
                origin_mod,
                site_paths,
                allow_runtime_imports=allow_runtime_imports,
            )
            if module is not None:
                cls = getattr(module, recv_type, None)
                if cls is None:
                    cls = _find_class_in_package(
                        origin_mod,
                        recv_type,
                        site_paths,
                        allow_runtime_imports=allow_runtime_imports,
                    )
                if cls is not None:
                    target = getattr(cls, method_name, None)
                    ann = _get_return_annotation(target)
                    pys = _annotation_to_pys_type(ann)
                    if pys and pys not in {
                        "list",
                        "dict",
                        "tuple",
                        "set",
                        "int",
                        "float",
                        "bool",
                        "str",
                        "string",
                    }:
                        _remember_type_origin(pys, target, type_modules, fallback_module=origin_mod)
                    info = _pack(pys, ann, recv_type, external=True)
                    if info:
                        return info
                    # Annotation missing entirely — still apply DB-API heuristics
                    element = _element_type_heuristic(recv_type, method_name)
                    if element and method_name in {"fetchall", "fetchmany"}:
                        return InferredReturn(
                            pys_type="list",
                            element_type=element,
                            from_external=True,
                            weak=True,
                        )
                    if element and method_name == "fetchone":
                        return InferredReturn(
                            pys_type=element,
                            element_type=None,
                            from_external=True,
                            weak=True,
                        )

    # mysql.connector — treat as module path + attribute
    if "." in recv:
        head, *rest = recv.split(".")
        mod_name = imported_modules.get(head)
        if mod_name:
            module = import_module_from_sites(
                mod_name,
                site_paths,
                allow_runtime_imports=allow_runtime_imports,
            )
            if module is not None:
                parent = resolve_attr_chain(module, rest)
                target = getattr(parent, method_name, None) if parent is not None else None
                ann = _get_return_annotation(target)
                pys = _annotation_to_pys_type(ann)
                if pys and pys not in {
                    "list",
                    "dict",
                    "tuple",
                    "set",
                    "int",
                    "float",
                    "bool",
                    "str",
                    "string",
                }:
                    _remember_type_origin(pys, target, type_modules)
                return _pack(pys, ann, None, external=True)
    return None


def _remember_type_origin(
    pys_type: str,
    target: Any,
    type_modules: dict[str, str],
    fallback_module: str | None = None,
) -> None:
    if pys_type in type_modules:
        return
    # From a class return annotation
    ann = _get_return_annotation(target)
    if isinstance(ann, type):
        type_modules[pys_type] = ann.__module__
        return
    if fallback_module:
        type_modules[pys_type] = fallback_module


def _find_class_in_package(
    package: str,
    class_name: str,
    site_paths: list[Path],
    *,
    allow_runtime_imports: bool = True,
) -> Any | None:
    module = import_module_from_sites(
        package,
        site_paths,
        allow_runtime_imports=allow_runtime_imports,
    )
    if module is None:
        return None
    found = getattr(module, class_name, None)
    if isinstance(found, type):
        return found
    pkg_path = getattr(module, "__path__", None)
    if not pkg_path:
        return None
    try:
        from pkgutil import walk_packages

        for info in walk_packages(pkg_path, prefix=f"{package}."):
            # Skip noisy/binary extension modules that may fail to import.
            if info.name.endswith(("_cext", ".cext")):
                continue
            try:
                sub = import_module_from_sites(
                    info.name,
                    site_paths,
                    allow_runtime_imports=allow_runtime_imports,
                )
            except Exception:
                continue
            if sub is None:
                continue
            found = getattr(sub, class_name, None)
            if isinstance(found, type):
                return found
    except Exception:
        return None
    return None


def resolve_library_class(
    type_name: str,
    *,
    type_modules: dict[str, str],
    imported_modules: dict[str, str],
    site_paths: list[Path],
    allow_runtime_imports: bool = True,
) -> Any | None:
    """Resolve a class/type imported from a Python library (by name)."""
    base = (type_name or "").strip()
    if "<" in base:
        base = base.split("<", 1)[0]
    if base.endswith("[]"):
        base = base[:-2]
    if not base:
        return None

    candidates: list[str] = []
    origin = type_modules.get(base)
    if origin:
        candidates.append(origin)
    # Prefer the exact module that exported this name when recorded as a type.
    for mod in imported_modules.values():
        if mod not in candidates:
            candidates.append(mod)

    for mod_name in candidates:
        module = import_module_from_sites(
            mod_name,
            site_paths,
            allow_runtime_imports=allow_runtime_imports,
        )
        if module is None:
            continue
        found = getattr(module, base, None)
        if isinstance(found, type):
            type_modules.setdefault(base, found.__module__)
            return found
    return None


def library_type_member_status(
    type_name: str,
    member: str,
    *,
    type_modules: dict[str, str],
    imported_modules: dict[str, str],
    site_paths: list[Path],
    allow_runtime_imports: bool = True,
) -> str:
    """Classify a member check against a Python library type.

    Returns one of:
    - ``found`` — class loaded; ``member`` exists (``hasattr``, MRO-aware)
    - ``absent`` — class loaded; ``member`` does not exist
    - ``unavailable`` — type is recorded in ``type_modules`` but the class
      could not be imported in this environment
    - ``not_library`` — cannot resolve a library class for ``type_name``

    Types may be known either by explicit ``import Name from …`` (``type_modules``)
    or by resolving ``Name`` inside an imported package (e.g. ``Frame`` via
    ``import tkinter.ttk as ttk``).
    """
    cls = resolve_library_class(
        type_name,
        type_modules=type_modules,
        imported_modules=imported_modules,
        site_paths=site_paths,
        allow_runtime_imports=allow_runtime_imports,
    )
    if cls is None:
        if type_name in type_modules:
            return "unavailable"
        return "not_library"
    if not member or member.startswith("_"):
        return "absent"
    return "found" if hasattr(cls, member) else "absent"


def library_type_has_member(
    type_name: str,
    member: str,
    *,
    type_modules: dict[str, str],
    imported_modules: dict[str, str],
    site_paths: list[Path],
    allow_runtime_imports: bool = True,
) -> bool:
    """True if ``member`` is a public attribute on a library class (MRO-aware)."""
    return (
        library_type_member_status(
            type_name,
            member,
            type_modules=type_modules,
            imported_modules=imported_modules,
            site_paths=site_paths,
            allow_runtime_imports=allow_runtime_imports,
        )
        == "found"
    )


def locate_type_definition(
    type_name: str,
    *,
    type_modules: dict[str, str],
    site_paths: list[Path],
    allow_runtime_imports: bool = True,
) -> tuple[Path, int, int] | None:
    """Return (file, line, column) for a class/type definition if found."""
    module_name = type_modules.get(type_name)
    candidates = [module_name] if module_name else []
    # Also try common patterns
    if not candidates:
        return None
    for mod_name in candidates:
        module = import_module_from_sites(
            mod_name,
            site_paths,
            allow_runtime_imports=allow_runtime_imports,
        )
        if module is None:
            continue
        cls = getattr(module, type_name, None)
        if cls is None:
            cls = _find_class_in_package(
                mod_name.split(".")[0],
                type_name,
                site_paths,
                allow_runtime_imports=allow_runtime_imports,
            )
        if not isinstance(cls, type):
            continue
        located = locate_python_object(cls)
        if located:
            path, line, col, _kind = located
            return path, line, col
    return None


def locate_python_object(obj: Any) -> tuple[Path, int, int, str] | None:
    """Return (file, line, column, kind) for a module, class, function, or callable."""
    import inspect

    if obj is None:
        return None
    if inspect.ismodule(obj):
        file = getattr(obj, "__file__", None)
        if not file:
            return None
        return Path(file), 1, 1, "module"
    try:
        target = inspect.unwrap(obj) if callable(obj) else obj
    except Exception:
        target = obj
    try:
        file = Path(inspect.getfile(target))
    except Exception:
        func = getattr(obj, "__func__", None)
        if func is not None:
            return locate_python_object(func)
        return None
    line: int | None = None
    try:
        _src, start = inspect.getsourcelines(target)
        line = int(start)
    except Exception:
        if inspect.isclass(target):
            line = _class_lineno_from_source(file, target.__name__)
        elif hasattr(target, "__name__"):
            line = _def_lineno_from_source(file, target.__name__)
    if line is None:
        line = 1
    if inspect.isclass(target):
        kind = "type"
    else:
        kind = "function"
    return file, int(line), 1, kind


def locate_attr_path(
    dotted: str,
    *,
    imported_modules: dict[str, str],
    site_paths: list[Path],
    variable_types: dict[str, str] | None = None,
    type_modules: dict[str, str] | None = None,
    allow_runtime_imports: bool = True,
) -> tuple[Path, int, int, str] | None:
    """Locate a dotted path such as ``mysql.connector`` or ``mysql.connector.connect``.

    Also supports ``instance.method`` when ``variable_types`` / ``type_modules`` are known.
    Returns (file, line, column, kind) or None.
    """
    dotted = dotted.strip()
    if not dotted or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", dotted):
        return None
    parts = dotted.split(".")
    head = parts[0]
    rest = parts[1:]
    variable_types = variable_types or {}
    type_modules = type_modules or {}

    if head in imported_modules:
        # Prefer longest importable module prefix, then attribute chain
        # (submodules are often not yet attributes of the parent package).
        for i in range(len(parts), 0, -1):
            mod_name = ".".join(parts[:i])
            if i == 1:
                mod_name = imported_modules.get(head, head)
            module = import_module_from_sites(
                mod_name,
                site_paths,
                allow_runtime_imports=allow_runtime_imports,
            )
            if module is None:
                continue
            if i == len(parts):
                return locate_python_object(module)
            target = resolve_attr_chain(module, parts[i:])
            located = locate_python_object(target)
            if located:
                return located
        return None

    # instance.method / instance.attr…
    if not rest or head not in variable_types:
        return None
    recv_type = variable_types[head]
    if recv_type.startswith("module:"):
        mod_name = recv_type.split(":", 1)[1]
        module = import_module_from_sites(
            mod_name,
            site_paths,
            allow_runtime_imports=allow_runtime_imports,
        )
        if module is None:
            return None
        return locate_python_object(resolve_attr_chain(module, rest) if rest else module)

    origin = type_modules.get(recv_type)
    if not origin:
        return None
    module = import_module_from_sites(
        origin,
        site_paths,
        allow_runtime_imports=allow_runtime_imports,
    )
    if module is None:
        return None
    cls = getattr(module, recv_type, None)
    if cls is None:
        cls = _find_class_in_package(
            origin.split(".")[0],
            recv_type,
            site_paths,
            allow_runtime_imports=allow_runtime_imports,
        )
    if cls is None:
        return None
    return locate_python_object(resolve_attr_chain(cls, rest))


def inspect_getfile(obj: Any) -> str:
    import inspect

    return inspect.getfile(obj)


def _class_lineno_from_source(path: Path, class_name: str) -> int | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node.lineno
    return None


def _def_lineno_from_source(path: Path, name: str) -> int | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node.lineno
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.lineno
    return None
