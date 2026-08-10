"""Brace-mode indentation formatting (`pys.indent`)."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.parse import parse_program
from transpiler.pipeline import compile_pys
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError

_REPO = Path(__file__).resolve().parents[1]
_REKEN = _REPO / "tests" / "fixtures" / "rekenmachine.pys"


def _analyze(source: str):
    return analyze(parse_program(source))


def test_rekenmachine_fixture_compiles_when_indents_aligned() -> None:
    compile_pys(_REKEN.read_text(encoding="utf-8"))


def test_class_member_extra_space_is_indent_error() -> None:
    source = """class Rekenmachine {
    private fix int getalA
     private fix int getalB

    public constructor(int a, int b) {
        this.getalA = a
        this.getalB = b
    }
}
"""
    with pytest.raises(TranspileError, match=r"Indentation error: expected 4 spaces, found 5") as ei:
        _analyze(source)
    err = ei.value
    assert getattr(err, "code", None) == "pys.indent"
    assert err.suggested_fix == "    private fix int getalB"


def test_method_body_extra_space_is_indent_error() -> None:
    source = """class Rekenmachine {
    private fix int getalA
    private fix int getalB

    public constructor(int a, int b) {
         this.getalA = a
        this.getalB = b
    }
}
"""
    with pytest.raises(TranspileError, match=r"Indentation error: expected 8 spaces, found 9") as ei:
        _analyze(source)
    err = ei.value
    assert getattr(err, "code", None) == "pys.indent"
    assert err.suggested_fix.startswith("        this.getalA")


def test_nested_block_requires_plus_four() -> None:
    source = """function void demo() {
    if (true) {
      print(1)
    }
}
"""
    with pytest.raises(TranspileError, match=r"Indentation error: expected 8 spaces, found 6"):
        _analyze(source)


def test_else_if_chain_same_nest_as_if() -> None:
    source = """int x = 1
if (x < 0) {
    print("neg")
}
else if (x == 0) {
    print("zero")
}
else {
    print("pos")
}
"""
    _analyze(source)


def test_global_function_body_indents_from_line_start() -> None:
    source = """global function void add(int a, int b) {
    print(a + b)
}
"""
    _analyze(source)

    source = """class Counter {
    private int value

    public constructor() {
        this.value = 0
    }

    public bump() {
        this.value = this.value + 1
    }
}

Counter c = Counter()
c.bump()
"""
    _analyze(source)


def test_top_level_indent_rejected() -> None:
    source = """class C {
    public constructor() {
        pass
    }
}
    print(1)
"""
    with pytest.raises(TranspileError, match=r"Indentation error: expected 0 spaces, found 4"):
        _analyze(source)
