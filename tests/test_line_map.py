"""Line maps for PYS ↔ generated Python (F-004 / DAP stepping)."""
from __future__ import annotations

from pathlib import Path

from transpiler.emit.python import emit_with_map
from transpiler.parse import parse_program
from transpiler.pipeline import compile_pys_with_map
from transpiler.sem import analyze
from transpiler.transpiler import transpile


def test_transpile_string_api_unchanged() -> None:
    source = "int x = 1\nprint(x)\n"
    assert isinstance(transpile(source), str)


def test_line_map_hits_assign_and_print() -> None:
    source = "int x = 1\nprint(x)\n"
    py, line_map, _names = compile_pys_with_map(source)
    assert "x = 1" in py
    assert "print(x)" in py
    by_pys = {e["pys"]: e["py"] for e in line_map}
    assert 1 in by_pys
    assert 2 in by_pys
    lines = py.splitlines()
    assert "x = 1" in lines[by_pys[1] - 1]
    assert "print(x)" in lines[by_pys[2] - 1]


def test_preamble_does_not_claim_false_pys_lines() -> None:
    source = "shared int c = 0\nprint(c)\n"
    py, line_map, _names = compile_pys_with_map(source)
    assert "_PysShared" in py
    assert "from concurrent.futures" in py
    # No map entry may point a preamble import line at a .pys statement.
    py_lines = py.splitlines()
    for entry in line_map:
        text = py_lines[entry["py"] - 1]
        assert not text.startswith("from concurrent")
        assert not text.startswith("class _PysShared")
        assert not text.startswith("def _pys_await")


def test_emit_with_map_matches_emit_text() -> None:
    source = "int a = 2\nint b = a + 1\nprint(b)\n"
    tree = analyze(parse_program(source))
    text, line_map, names = emit_with_map(tree)
    assert text == transpile(source)
    assert line_map
    assert all("py" in e and "pys" in e for e in line_map)
    assert names == {}


def test_function_body_lines_map(tmp_path: Path) -> None:
    source = """
function int add(int a, int b) {
    int s = a + b
    return s
}
print(add(1, 2))
"""
    py, line_map, _names = compile_pys_with_map(source)
    by_pys = {e["pys"]: e["py"] for e in line_map}
    # `int s = a + b` and `return s` should be mapped.
    assert any("s = a + b" in py.splitlines()[by_pys[p] - 1] for p in by_pys)
    assert any(py.splitlines()[by_pys[p] - 1].strip() == "return s" for p in by_pys)


def test_lambda_capture_debug_names() -> None:
    source = """
shared int hits = 0
list<int> xs = [1, 2]
xs.loop(n => {
    hits += 1
    return n
})
"""
    _py, _line_map, names = compile_pys_with_map(source)
    assert names.get("_c_hits") == "hits"
