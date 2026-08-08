"""examples/classes.pys — general class teaching sample."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import run_source, transpile
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "classes.pys"

os.environ.setdefault("PYS_SUPPRESS_WARNINGS", "1")


def test_example_classes_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_classes_emit_and_output() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "class Person:" in py
    assert "class Dog(Animal):" in py
    assert "class Unit:" in py
    assert "class Vehicle:" in py
    assert "class Car(Vehicle):" in py
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == [
        "Person:Ada",
        "Ada",
        "(0,0)",
        "(3,4)",
        "Rex the dog says woof",
        "Rex the dog says woof",
        "unit#42",
        "Car plate=UNKNOWN model=Unnamed",
        "Car plate=ABC-1 model=Roadster",
    ]
