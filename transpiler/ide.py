"""IDE helpers: symbol location for go-to-definition / highlighting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .pytypes import locate_attr_path, locate_type_definition
from .transpiler import Parser, TranspileError


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


def analyze_file(source_path: Path) -> dict:
    source_path = source_path.resolve()
    source = source_path.read_text(encoding="utf-8")
    error = None
    try:
        parser = Parser(source, source_path=source_path)
    except TranspileError as exc:
        # Formatting errors abort __init__; retry so IDE can still resolve types/symbols.
        error = _error_dict(exc)
        parser = Parser(source, source_path=source_path, enforce_formatting=False)
    try:
        parser.parse()
    except TranspileError as exc:
        if error is None:
            error = _error_dict(exc)

    # Variable / local / function symbol declarations
    symbols = {
        name: {"file": str(path), "line": line, "column": col, "kind": "symbol"}
        for name, (path, line, col) in parser.symbol_locations.items()
    }

    # Type definitions win for type names (library class or user class)
    site_paths = parser._deps_paths()
    for type_name in set(parser.type_modules) | set(parser.type_definitions) | set(parser.validated_types):
        if type_name in {"int", "float", "char", "string", "bool", "list", "dict", "tuple", "set"}:
            continue
        located = parser.type_definitions.get(type_name)
        if located is None and type_name in parser.type_modules:
            located = locate_type_definition(
                type_name,
                type_modules=parser.type_modules,
                site_paths=site_paths,
            )
            if located:
                parser.type_definitions[type_name] = located
        if located:
            path, line, col = located
            symbols[type_name] = {
                "file": str(path),
                "line": line,
                "column": col,
                "kind": "type",
            }

    return {
        "ok": error is None,
        "error": error,
        "hints": list(parser.typing_hints),
        "symbols": symbols,
        "variable_types": dict(parser.variable_types),
        "type_modules": dict(parser.type_modules),
        "imported_modules": dict(parser.imported_modules),
        "collection_element_types": dict(parser.collection_element_types),
        "validated_types": sorted(parser.validated_types),
        "_site_paths": [str(p) for p in site_paths],
    }


def lookup_symbol(analysis: dict, symbol: str) -> dict | None:
    """Resolve a bare name or dotted path to a location dict."""
    symbol = (symbol or "").strip()
    if not symbol:
        return None
    loc = analysis.get("symbols", {}).get(symbol)
    if loc:
        return loc

    site_paths = [Path(p) for p in analysis.get("_site_paths") or []]
    located = locate_attr_path(
        symbol,
        imported_modules=analysis.get("imported_modules") or {},
        site_paths=site_paths,
        variable_types=analysis.get("variable_types") or {},
        type_modules=analysis.get("type_modules") or {},
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
        # Do not leak internal keys to the IDE
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
