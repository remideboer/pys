"""Structs: parse/sem/emit happy path and SA rejections."""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile, run_source

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "structs.pys"


def test_example_structs_runs() -> None:
    assert EXAMPLE.is_file()
    assert run_source(EXAMPLE) == 0


def test_example_structs_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "@dataclass" in py
    assert "_pys_struct_copy" in py
    assert "def _pys_copy(self):" in py


def test_struct_equality_and_copy_on_call(capsys: pytest.CaptureFixture[str]) -> None:
    source = """
struct Damage {
    int amount
    string type
}

function Damage bump(Damage d) {
    d.amount = d.amount + 1
    return d
}

Damage d1 = Damage(20, "physical")
Damage d2 = Damage(amount=20, type="physical")
print(d1 == d2)
Damage before = Damage(10, "fire")
Damage after = bump(before)
print(before.amount)
print(after.amount)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip().splitlines() == ["True", "10", "11"]


def test_fix_struct_is_hashable_mutable_is_not() -> None:
    source = """
struct Mut {
    int x
}
fix struct Imm {
    int x
}
struct AllFix {
    fix int x
}
"""
    py = transpile(source)
    ns: dict = {}
    exec(py, ns)
    assert ns["Imm"](1).__hash__() is not None
    assert hash(ns["Imm"](1)) == hash(ns["Imm"](1))
    assert ns["AllFix"](1).__hash__() is not None
    with pytest.raises(TypeError):
        hash(ns["Mut"](1))


@pytest.mark.parametrize(
    "source, match",
    [
        (
            "struct S { int x }\nshared S s = S(1)\n",
            r"shared.*struct",
        ),
        (
            "struct S { int x }\nS s = null\n",
            r"cannot be null",
        ),
        (
            "struct S inherits Foo { int x }\n",
            r"Structs cannot use",
        ),
        (
            "struct S { int x }\nfix S s = S(1)\ns.x = 2\n",
            r"fix-bound struct",
        ),
        (
            "fix struct S { int x }\nS s = S(1)\ns.x = 2\n",
            r"fix struct type",
        ),
        (
            "struct S { fix int x }\nS s = S(1)\ns.x = 2\n",
            r"fix field",
        ),
        (
            "struct S { int x }\nS s = S(1, 2)\n",
            r"expects at most 1",
        ),
        (
            "struct S { int x }\nS s = S(y=1)\n",
            r"Unknown field",
        ),
        (
            "struct S { int x }\nS s = new S(1)\n",
            r"Unexpected `new`",
        ),
        (
            "struct S { public int x }\n",
            r"Struct fields are always public",
        ),
        (
            "struct S { private int x }\n",
            r"Struct fields are always public",
        ),
    ],
)
def test_struct_sa_rejections(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_named_kwargs_on_method() -> None:
    source = """
class Box {
    private int n
    public Box(int n) {
        this.n = n
    }
    public set(int n) {
        this.n = n
    }
    public int get() {
        return this.n
    }
}
Box b = Box(1)
b.set(n=7)
print(b.get())
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == "7"


def test_struct_keyword_lexed() -> None:
    from transpiler.lex import tokenize, TokenKind

    toks = tokenize("struct Damage { }")
    kinds = [(t.kind, t.text) for t in toks if t.kind != TokenKind.BLANK]
    assert (TokenKind.KEYWORD, "struct") in kinds


def test_struct_unknown_field_member_denied() -> None:
    source = """
struct S {
    int x
}
S s = S(1)
print(s.y)
"""
    with pytest.raises(TranspileError, match=r"'y' is not a member of declared type S"):
        transpile(source)


def test_emit_copies_only_struct_values() -> None:
    source = """
struct Damage {
    int amount
    string type
}
class Unit {
    private int health
    public Unit(int health) {
        this.health = health
    }
}
Damage d = Damage(1, "a")
Unit u = Unit(10)
print(d.amount)
print(u)
"""
    py = transpile(source)
    assert "d = _pys_struct_copy(Damage(" in py or "d = _pys_struct_copy(Damage" in py
    assert "u = _pys_struct_copy(Unit" not in py
    assert 'Unit(_pys_struct_copy(10))' not in py
    assert "Unit(10)" in py or "Unit(health=10)" in py or "Unit(10" in py


def test_partial_fix_field_runtime_guard() -> None:
    source = """
struct Mixed {
    int amount
    fix string type
}
"""
    py = transpile(source)
    assert "_pys_fix_fields" in py
    assert "__setattr__" in py
    ns: dict = {}
    exec(py, ns)
    m = ns["Mixed"](1, "fire")
    m.amount = 2
    with pytest.raises(AttributeError, match="fix field"):
        m.type = "ice"


def test_struct_field_defaults_and_trailing_omit() -> None:
    source = """
struct Hit {
    int amount
    string type = "physical"
}
Hit a = Hit(10)
Hit b = Hit(10, "fire")
print(a.type)
print(b.type)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip().splitlines() == ["physical", "fire"]


def test_nested_struct_copy_on_call() -> None:
    source = """
struct Inner {
    int x
}
struct Outer {
    Inner inner
}
function Outer touch(Outer o) {
    o.inner.x = 99
    return o
}
Outer before = Outer(Inner(1))
Outer after = touch(before)
print(before.inner.x)
print(after.inner.x)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip().splitlines() == ["1", "99"]


@pytest.mark.parametrize(
    "source, match",
    [
        (
            "struct S { int x\n int x }\n",
            r"Duplicate field",
        ),
        (
            "struct S { int x = 1\n int y }\n",
            r"without a default cannot follow",
        ),
        (
            "struct S {\n  function int f() { return 1 }\n}\n",
            r"Structs cannot contain `function`",
        ),
        (
            """
struct Inner { int x }
struct Outer { Inner inner }
fix Outer o = Outer(Inner(1))
o.inner.x = 2
""",
            r"fix-bound struct",
        ),
        (
            """
struct Inner { int x }
struct Outer { fix Inner inner }
Outer o = Outer(Inner(1))
o.inner.x = 2
""",
            r"through fix field",
        ),
    ],
)
def test_struct_maturity_rejections(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_package_struct_import_and_ide_types(tmp_path: Path) -> None:
    from transpiler.ide import analyze_file

    lib = tmp_path / "damage_lib.pys"
    lib.write_text(
        "package struct Damage {\n    int amount\n    string type\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text(
        'import Damage from damage_lib.pys\nDamage d = Damage(3, "a")\nprint(d.amount)\n',
        encoding="utf-8",
    )
    assert run_source(main) == 0
    analysis = analyze_file(main)
    assert analysis["ok"]
    assert "Damage" in analysis["validated_types"]
    assert "Damage" in analysis["symbols"]
