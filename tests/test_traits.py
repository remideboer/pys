"""Traits: composition via uses/requires, collision, SA diagnostics."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.ide import analyze_file, lookup_symbol
from transpiler.transpiler import TranspileError, run_source, transpile
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "traits.pys"

os.environ.setdefault("PYS_SUPPRESS_WARNINGS", "1")


def test_example_traits_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_traits_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "class Product" in py
    assert "def label(self)" in py
    assert "def isGreaterThan(self" in py
    assert "class Printable" not in py  # traits are not emitted as types
    assert "def _Loud_greet(self)" in py
    assert "def _Soft_greet(self)" in py


def test_traits_product_behavior() -> None:
    source = EXAMPLE.read_text(encoding="utf-8")
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == [
        "Item: apple",
        "False",
        "True",
        "True",
        "bolt#42",
        "Item: gauge",
        "within limit",
        "overflow",
        "HEY/hi",
    ]


@pytest.mark.parametrize(
    "source, match",
    [
        (
            """
trait T {
    requires string name
    string f() { return this.name }
}
class C uses T {
    public C() {}
}
""",
            r"does not provide 'name'",
        ),
        (
            """
trait A { string greet() { return "a" } }
trait B { string greet() { return "b" } }
class C uses A, B {
    public C() {}
}
""",
            r"both define 'greet'|disambiguate",
        ),
        (
            """
trait T {
    string f() { return this.missing }
}
class C uses T {
    public C() {}
}
""",
            r"this\.missing|not declared in `requires`",
        ),
        (
            """
trait T { string f() { return "x" } }
class C implements T {
    public C() {}
}
""",
            r"is a trait, not an interface",
        ),
        (
            """
trait T { string f() { return "x" } }
T t = T()
""",
            r"cannot be instantiated|not a type",
        ),
    ],
)
def test_trait_sa_errors(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_ide_goto_trait(tmp_path: Path) -> None:
    path = tmp_path / "t.pys"
    path.write_text(
        """
trait Printable {
    requires string name
    string label() { return this.name }
}
class Item uses Printable {
    private string name
    public Item(string name) { this.name = name }
}
""",
        encoding="utf-8",
    )
    analysis = analyze_file(path)
    assert "Printable" in (analysis.get("symbols") or {})
    hit = lookup_symbol(analysis, "Printable")
    assert hit is not None
