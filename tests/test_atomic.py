"""Tests for atomic qualifier (implies shared; indivisible RMW / CAS)."""
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
EXAMPLE = ROOT / "examples" / "atomic.pys"


def test_example_atomic_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_atomic_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "_PysAtomic(" in py
    assert ".iadd(" in py
    assert ".compareAndSet(" in py
    assert ".get()" in py


def test_atomic_counter_deterministic_2000(capsys: pytest.CaptureFixture[str]) -> None:
    source = """
atomic int counter = 0
tasks {
    task {
        loop (int i = 0; i < 1000; i++) {
            counter += 1
        }
    }
    task {
        loop (int i = 0; i < 1000; i++) {
            counter += 1
        }
    }
}
print(counter)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip() == "2000"


def test_atomic_compare_and_set() -> None:
    source = """
atomic int highScore = 0
function void reportScore(int candidate) {
    bool done = false
    loop (!done) {
        int current = highScore.get()
        if (candidate <= current) {
            done = true
        } else {
            done = highScore.compareAndSet(current, candidate)
        }
    }
}
reportScore(10)
reportScore(5)
reportScore(20)
print(highScore)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip() == "20"


def test_atomic_lambda_capture_mutation() -> None:
    source = """
atomic int hits = 0
list<int> xs = [1, 2, 3]
xs.loop(n => {
    hits += 1
    return n
})
print(hits)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip() == "3"


@pytest.mark.parametrize(
    "source, match",
    [
        (
            "atomic int x = 0\nx *= 2\n",
            r"not allowed on atomic|compareAndSet",
        ),
        (
            "atomic int x = 0\nx /= 2\n",
            r"not allowed on atomic|compareAndSet",
        ),
        (
            "atomic int x = 0\nx %= 2\n",
            r"not allowed on atomic|compareAndSet",
        ),
        (
            "atomic shared int x = 0\n",
            r"redundant|implies shared",
        ),
        (
            "shared atomic int x = 0\n",
            r"redundant|implies shared",
        ),
        (
            "atomic float x = 0.0\n",
            r"atomic",
        ),
        (
            "atomic int x = 0\nx.foo()\n",
            r"no member|atomic",
        ),
    ],
)
def test_atomic_sa_rejects(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_run_source_workspace_isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "a.pys"
    src.write_text("atomic int x = 1\nprint(x)\n", encoding="utf-8")
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
    assert run_source(src) == 0
