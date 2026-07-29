"""Tests for tasks / task / await / shared (Policy B)."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_tasks_task_transpiles_and_joins() -> None:
    source = """
tasks {
    task {
        print("a")
    }
    task {
        print("b")
    }
}
"""
    out = transpile(source)
    assert "_pys_run_tasks(" in out
    assert "def __pys_task_" in out
    assert "_PysShared" in out or "ThreadPoolExecutor" in out


def test_shared_mutation_allowed() -> None:
    source = """
shared int counter = 0
tasks {
    task {
        counter = counter + 1
    }
}
print(counter)
"""
    out = transpile(source)
    assert "counter = _PysShared(0)" in out
    assert "counter.set(" in out
    assert "counter.value" in out


def test_capture_mutation_rejected() -> None:
    source = """
int local = 1
tasks {
    task {
        local = 2
    }
}
"""
    with pytest.raises(TranspileError, match="shared"):
        transpile(source)


def test_await_named_task() -> None:
    source = """
tasks {
    task ready {
        return 41
    }
    task {
        int n = await ready
        print(n)
    }
}
"""
    out = transpile(source)
    assert "_pys_await(_pys_futures_" in out
    assert "['ready']" in out or '["ready"]' in out


def test_await_outside_task_rejected() -> None:
    source = """
int n = await ready
"""
    with pytest.raises(TranspileError, match="await"):
        transpile(source)


def test_shared_name_not_rewritten_inside_strings() -> None:
    source = """
shared int counter = 0
print("counter stays literal")
print(counter)
"""
    out = transpile(source)
    assert '"counter stays literal"' in out
    assert "print(counter.value)" in out


def test_task_outside_tasks_rejected() -> None:
    source = """
task {
    print("x")
}
"""
    with pytest.raises(TranspileError, match="tasks"):
        transpile(source)
