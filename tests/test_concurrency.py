"""Tests for tasks / task / await / shared (Policy B)."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile, run_source
from pathlib import Path
import tempfile


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
    assert "_PysTaskGroup()" in out
    assert ".run()" in out
    assert "def __pys_task_" in out
    assert "add_auto" in out


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
    assert ".futures['ready']" in out or '.futures["ready"]' in out


def test_parameterized_task_await_call() -> None:
    source = """
tasks {
    task double(int n) {
        return n * 2
    }
    task {
        int x = await double(21)
        print(x)
    }
}
"""
    out = transpile(source)
    assert "def __pys_task_double(n):" in out
    assert "add_template" in out
    assert ".call('double', 21)" in out or '.call("double", 21)' in out


def test_parameterized_task_runs() -> None:
    source = """
tasks {
    task add(int a, int b) {
        return a + b
    }
    task {
        int s = await add(10, 32)
        print(s)
    }
}
"""
    # Smoke: transpile valid + execute
    py = transpile(source)
    assert "add_template" in py
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.pys"
        path.write_text(source, encoding="utf-8")
        # run via generated module execution
        from transpiler.transpiler import Parser
        code = Parser(source).parse()
        ns: dict = {}
        exec(code, ns)


def test_await_outside_task_rejected() -> None:
    source = """
int n = await ready
"""
    with pytest.raises(TranspileError, match="await"):
        transpile(source)


def test_task_outside_tasks_rejected() -> None:
    source = """
task {
    print("x")
}
"""
    with pytest.raises(TranspileError, match="tasks"):
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
