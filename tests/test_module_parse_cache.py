"""Module parse results are memoized, so edits must never be served stale."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler import parse as parse_mod
from transpiler.pipeline import compile_pys
from transpiler.transpiler import transpile_with_modules


def _write_main(tmp_path: Path) -> Path:
    main = tmp_path / "main.pys"
    main.write_text("import all from funcs.pys\ngreet(\"student\")\n", encoding="utf-8")
    return main


def test_edited_import_is_retranspiled(tmp_path: Path) -> None:
    funcs = tmp_path / "funcs.pys"
    funcs.write_text(
        "global function greet(name){\n    print(name)\n}\n",
        encoding="utf-8",
    )
    main = _write_main(tmp_path)

    assert "def greet(name):" in transpile_with_modules(main)["funcs"]

    funcs.write_text(
        "global function greet(name){\n    print(\"hello \" + name)\n}\n"
        "global function farewell(){\n    print(\"bye\")\n}\n",
        encoding="utf-8",
    )

    modules = transpile_with_modules(main)
    assert "def farewell():" in modules["funcs"]
    assert "hello " in modules["funcs"]
    assert "from funcs import farewell, greet\n" in modules["main"]


def test_each_file_is_parsed_once_per_compile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sem and emit build separate resolvers; they must share parses, not repeat them.

    Counting parses (rather than timing) keeps this guard deterministic.
    """
    (tmp_path / "funcs.pys").write_text(
        "global function greet(name){\n    print(name)\n}\n",
        encoding="utf-8",
    )
    main = _write_main(tmp_path)

    parsed: list[str] = []
    original = parse_mod.parse_program

    def counting_parse_program(source: str):
        parsed.append(source)
        return original(source)

    monkeypatch.setattr(parse_mod, "parse_program", counting_parse_program)
    compile_pys(main.read_text(encoding="utf-8"), source_path=main)

    # main: once for the tree that sem/emit walk, once for its export metadata.
    # funcs: once for its export metadata.
    assert len(parsed) == 3, f"expected 3 parses, got {len(parsed)}"


def test_same_name_in_separate_directories_stays_distinct(tmp_path: Path) -> None:
    """Cache keys include the path, so identically named modules must not collide."""
    outputs = {}
    for index, folder in enumerate(("a", "b")):
        pkg = tmp_path / folder
        pkg.mkdir()
        (pkg / "funcs.pys").write_text(
            f"global function greet(name){{\n    print({index})\n}}\n",
            encoding="utf-8",
        )
        outputs[folder] = transpile_with_modules(_write_main(pkg))["funcs"]

    assert "print(_pys_format(0))" in outputs["a"]
    assert "print(_pys_format(1))" in outputs["b"]
