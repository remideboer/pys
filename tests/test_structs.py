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
    public int amount
    public string type
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
    public int x
}
fix struct Imm {
    public int x
}
struct AllFix {
    public fix int x
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
            "struct S { public int x }\nshared S s = S(1)\n",
            r"shared.*struct",
        ),
        (
            "struct S { public int x }\nS s = null\n",
            r"cannot be null",
        ),
        (
            "struct S inherits Foo { public int x }\n",
            r"Structs cannot use",
        ),
        (
            "struct S { public int x }\nfix S s = S(1)\ns.x = 2\n",
            r"fix-bound struct",
        ),
        (
            "fix struct S { public int x }\nS s = S(1)\ns.x = 2\n",
            r"fix struct type",
        ),
        (
            "struct S { public fix int x }\nS s = S(1)\ns.x = 2\n",
            r"fix field",
        ),
        (
            "struct S { public int x }\nS s = S(1, 2)\n",
            r"expects at most 1",
        ),
        (
            "struct S { public int x }\nS s = S(y=1)\n",
            r"Unknown field",
        ),
        (
            "struct S { public int x }\nS s = new S(1)\n",
            r"Unexpected `new`",
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
