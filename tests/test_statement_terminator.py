"""Optional `;` statement terminator — same-line mandatory rule (BDD)."""
from __future__ import annotations

import ast

import pytest

from transpiler.parse import parse_program
from transpiler.transpiler import TranspileError, transpile


def test_same_line_statements_with_semi_parse_and_emit() -> None:
    """Given two decls on one line separated by `;`, When transpile, Then OK."""
    source = "int x = 10; int y = 20\nprint(x + y)\n"
    mod = parse_program(source)
    assert len([s for s in mod.body if not hasattr(s, "text")]) >= 2
    py = transpile(source)
    ast.parse(py)
    assert "x = 10" in py and "y = 20" in py


def test_same_line_without_semi_is_fatal() -> None:
    """Given two stmts on one line with no `;`, When parse, Then FatalParseError tip."""
    with pytest.raises(TranspileError) as ei:
        parse_program("int x = 10 int y = 20\n")
    err = ei.value
    assert "same line" in str(err).lower() or "separated by ';'" in str(err)
    assert getattr(err, "code", None) == "pys.same-line-statements"
    tips = getattr(err, "tips", None) or []
    assert tips
    assert any(";" in t or "own line" in t for t in tips)


def test_alone_on_line_with_and_without_trailing_semi() -> None:
    """Given one stmt per line, When with/without trailing `;`, Then both OK."""
    parse_program("int x = 10\nint y = 20\n")
    parse_program("int x = 10;\nint y = 20;\n")
    py = transpile("int x = 1;\nprint(x)\n")
    ast.parse(py)


def test_trailing_semi_in_block() -> None:
    source = """
function f() {
    int x = 1;
    print(x)
}
f()
"""
    py = transpile(source)
    ast.parse(py)


def test_c_for_uses_semi_separators() -> None:
    source = """
loop (int i = 0; i < 3; i++) {
    print(i)
}
"""
    py = transpile(source)
    ast.parse(py)
    assert "range(" in py or "for " in py


def test_old_c_for_comma_form_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        parse_program("loop (int i = 0, i < 3, i++) { print(i) }\n")
    msg = str(ei.value)
    assert ";" in msg
    tips = getattr(ei.value, "tips", None) or []
    assert tips


def test_enum_comma_delimited_forms() -> None:
    one_line = "enum Day { MONDAY, TUESDAY, WEDNESDAY }\n"
    wrapped = """
enum Day {
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY,
    FRIDAY, SATURDAY, SUNDAY
}
"""
    trailing = """
enum Day {
    MONDAY,
    TUESDAY,
    WEDNESDAY,
}
"""
    for src in (one_line, wrapped, trailing):
        mod = parse_program(src)
        enum = mod.body[0]
        assert len(enum.members) >= 3


def test_enum_without_commas_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        parse_program("enum Day {\n    MONDAY\n    TUESDAY\n}\n")
    assert "comma" in str(ei.value).lower() or "," in str(ei.value)


def test_switch_stmt_multi_label_and_block_body() -> None:
    source = """
enum Day { MONDAY, SUNDAY, FRIDAY, WEDNESDAY }
Day day = Day.WEDNESDAY
switch (day) {
    case MONDAY, SUNDAY, FRIDAY: print(6)
    case WEDNESDAY: { print(9); print("x") }
    default: {
        print(0)
    }
}
"""
    py = transpile(source)
    ast.parse(py)


def test_switch_block_arm_locals_are_brace_scoped() -> None:
    """Block-form case body mangles locals (CER-015); bare arm does not."""
    block_src = """
enum E { A, B }
E e = E.A
switch (e) {
    case A: {
        int only_here = 1
        print(only_here)
    }
    case B: print(0)
}
"""
    py_block = transpile(block_src)
    assert any(line.strip().startswith("_pys_b") and "only_here" in line for line in py_block.splitlines()) or "_pys_b" in py_block

    bare_src = """
enum E { A, B }
E e = E.A
switch (e) {
    case A:
        int only_here = 1
        print(only_here)
    case B: print(0)
}
print(only_here)
"""
    py_bare = transpile(bare_src)
    # Bare arm shares enclosing scope — no brace mangling for only_here.
    assert "only_here = 1" in py_bare
    assert "_pys_b" not in py_bare or "only_here" in py_bare.split("_pys_b")[0]
