"""Abstract classes: ABC emit, subclass impl, no instantiate, void returns."""
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
EXAMPLE = ROOT / "examples" / "abstract_list.pys"

os.environ.setdefault("PYS_SUPPRESS_WARNINGS", "1")


def test_example_abstract_list_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_abstract_list_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "from abc import ABC, abstractmethod" in py
    assert "class AbstractList(ABC):" in py
    assert "class AbstractCountedList(AbstractList, ABC):" in py
    assert "@abstractmethod" in py
    assert "def get(self, index):" in py
    assert "def add(self, item):" in py
    # Decorators stay on abstract methods (not hoisted onto __init__).
    init_at = py.index("def __init__(self):")
    get_at = py.index("@abstractmethod\n    def get(self, index):")
    assert "@abstractmethod" not in py[:init_at]
    assert get_at > init_at
    assert "class ArrayListPys(AbstractCountedList):" in py
    assert "class LinkedListPys(AbstractCountedList):" in py
    assert "def hasItem(list, item):" in py


def test_abstract_list_runtime_behavior() -> None:
    source = EXAMPLE.read_text(encoding="utf-8")
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == [
        "True",
        "False",
        "a",
        "True",
        "False",
        "2",
        "True",
        "True",
        "b",
        "a",
        "True",
        "2",
        "True",
        "True",
    ]


@pytest.mark.parametrize(
    "source, match",
    [
        (
            """
class C {
    public C() {}
    public abstract int f()
}
""",
            r"abstract method|abstract class",
        ),
        (
            """
abstract class A {
    public A() {}
    public abstract int f()
}
class C inherits A {
    public C() { super() }
}
""",
            r"must implement|abstract",
        ),
        (
            """
abstract class A {
    public A() {}
    public abstract int f()
}
A a = A()
""",
            r"cannot be instantiated|abstract",
        ),
        (
            """
sealed abstract class A {
    public A() {}
}
""",
            r"mutually exclusive",
        ),
        (
            """
abstract class A {
    public A() {}
    public abstract void f()
}
class C inherits A {
    public C() { super() }
    public void f() {
        return 1
    }
}
""",
            r"void|cannot return a value|return",
        ),
    ],
)
def test_abstract_sa_errors(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_abstract_happy_path_template_method() -> None:
    src = """
abstract class Base {
    public Base() {}
    public int template() {
        return this.hook() + 1
    }
    public abstract int hook()
}
class Concrete inherits Base {
    public Concrete() { super() }
    public int hook() { return 41 }
}
Concrete c = Concrete()
print(c.template())
"""
    py = transpile(src)
    assert "class Base(ABC):" in py
    assert "@abstractmethod" in py
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip() == "42"


def test_ide_goto_abstract_class(tmp_path: Path) -> None:
    path = tmp_path / "a.pys"
    path.write_text(
        """
abstract class Shape {
    public Shape() {}
    public abstract float area()
}
class Box inherits Shape {
    public Box() { super() }
    public float area() { return 1.0 }
}
""",
        encoding="utf-8",
    )
    analysis = analyze_file(path)
    assert "Shape" in (analysis.get("symbols") or {})
    hit = lookup_symbol(analysis, "Shape")
    assert hit is not None
