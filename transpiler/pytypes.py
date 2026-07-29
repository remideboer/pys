"""Introspect return types from installed Python packages (pys.deps site paths)."""

from __future__ import annotations

import ast
import importlib
import re
import sys
import types
import typing
from pathlib import Path
from types import ModuleType
from typing import Any, get_args, get_origin


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
    return False


def _drop_module_tree(module_name: str) -> None:
    prefix = module_name + "."
    for key in list(sys.modules):
        if key == module_name or key.startswith(prefix):
            del sys.modules[key]


def import_module_from_sites(module_name: str, site_paths: list[Path]) -> ModuleType | None:
    with _with_sys_path(site_paths):
        try:
            if module_name in sys.modules:
                existing = sys.modules[module_name]
                file = getattr(existing, "__file__", None)
                # Reload when a deps site provides this module but the cached
                # copy came from a different path (common in tests / flyweight swaps).
                if (
                    file
                    and site_paths
                    and _site_has_module(module_name, site_paths)
                    and not _path_under_sites(Path(file), site_paths)
                ):
                    _drop_module_tree(module_name)
                else:
                    return existing
            return importlib.import_module(module_name)
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
) -> str | None:
    """Infer PYS type name for receiver.method(...) or module.attr(...).

    imported_modules maps top-level import name -> python module path (e.g. mysql -> mysql)
    type_modules maps type name -> python module that defines it (for locating methods on instances)
    """
    recv = receiver_expr.strip()
    # mysql.connector.connect → module attr chain ending in call target
    if method_name is None:
        # full call on dotted path: mysql.connector.connect
        if "." not in recv:
            return None
        head, *rest = recv.split(".")
        mod_name = imported_modules.get(head)
        if not mod_name:
            return None
        module = import_module_from_sites(mod_name, site_paths)
        if module is None:
            return None
        target = resolve_attr_chain(module, rest)
        ann = _get_return_annotation(target)
        pys = _annotation_to_pys_type(ann)
        if pys:
            _remember_type_origin(pys, target, type_modules)
        return pys

    # mydb.cursor → instance method; receiver has a known type
    recv_type = variable_types.get(recv)
    if recv_type:
        origin_mod = type_modules.get(recv_type)
        if origin_mod:
            module = import_module_from_sites(origin_mod, site_paths)
            if module is not None:
                cls = getattr(module, recv_type, None)
                if cls is None:
                    # search submodule exports
                    cls = _find_class_in_package(origin_mod, recv_type, site_paths)
                if cls is not None:
                    target = getattr(cls, method_name, None)
                    ann = _get_return_annotation(target)
                    pys = _annotation_to_pys_type(ann)
                    if pys:
                        _remember_type_origin(pys, target, type_modules, fallback_module=origin_mod)
                    return pys

    # mysql.connector — treat as module path + attribute
    if "." in recv:
        head, *rest = recv.split(".")
        mod_name = imported_modules.get(head)
        if mod_name:
            module = import_module_from_sites(mod_name, site_paths)
            if module is not None:
                parent = resolve_attr_chain(module, rest)
                target = getattr(parent, method_name, None) if parent is not None else None
                ann = _get_return_annotation(target)
                pys = _annotation_to_pys_type(ann)
                if pys:
                    _remember_type_origin(pys, target, type_modules)
                return pys
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


def _find_class_in_package(package: str, class_name: str, site_paths: list[Path]) -> Any | None:
    module = import_module_from_sites(package, site_paths)
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
                sub = import_module_from_sites(info.name, site_paths)
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


def locate_type_definition(
    type_name: str,
    *,
    type_modules: dict[str, str],
    site_paths: list[Path],
) -> tuple[Path, int, int] | None:
    """Return (file, line, column) for a class/type definition if found."""
    module_name = type_modules.get(type_name)
    candidates = [module_name] if module_name else []
    # Also try common patterns
    if not candidates:
        return None
    for mod_name in candidates:
        module = import_module_from_sites(mod_name, site_paths)
        if module is None:
            continue
        cls = getattr(module, type_name, None)
        if cls is None:
            cls = _find_class_in_package(mod_name.split(".")[0], type_name, site_paths)
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
            module = import_module_from_sites(mod_name, site_paths)
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
        module = import_module_from_sites(mod_name, site_paths)
        if module is None:
            return None
        return locate_python_object(resolve_attr_chain(module, rest) if rest else module)

    origin = type_modules.get(recv_type)
    if not origin:
        return None
    module = import_module_from_sites(origin, site_paths)
    if module is None:
        return None
    cls = getattr(module, recv_type, None)
    if cls is None:
        cls = _find_class_in_package(origin.split(".")[0], recv_type, site_paths)
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
