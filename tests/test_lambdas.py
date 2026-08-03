"""Lambdas: parse/sem/emit, capture rules, foreach freeze."""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "lambdas.pys"


def test_example_lambdas_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_lambdas_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "def _pys_lam_" in py
    assert "_c_i=" in py


def test_lambda_call_and_apply(capsys: pytest.CaptureFixture[str]) -> None:
    source = """
lambda<int, bool> isEven = n => n % 2 == 0
print(isEven(4))
print(isEven(3))
function int apply(int x, lambda<int, int> fn) {
    return fn(x)
}
print(apply(5, n => n * 2))
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["True", "False", "10"]


def test_foreach_capture_is_by_value() -> None:
    source = """
list<lambda<int>> callbacks = []
loop (int i in [0, 1, 2]) {
    callbacks = callbacks + [() => print(i)]
}
loop (lambda<int> cb in callbacks) {
    cb()
}
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["0", "1", "2"]


def test_shared_capture_mutation_allowed() -> None:
    source = """
shared int counter = 0
list<int> xs = [1, 2, 3]
xs.loop(n => {
    counter += n
    return n
})
print(counter)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip() == "6"


@pytest.mark.parametrize(
    "source, match",
    [
        (
            "int counter = 0\n"
            "lambda<int, int> add = n => {\n"
            "  counter += n\n"
            "  return counter\n"
            "}\n",
            r"mutate captured variable",
        ),
        (
            "loop (int i in [1]) {\n  i = 2\n}\n",
            r"immutable",
        ),
        (
            "lambda<int, bool> f = (int a, int b) => a > b\n",
            r"parameter",
        ),
    ],
)
def test_lambda_sa_rejects(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)
