"""ADR-026: library decorator application in PYS source."""

from __future__ import annotations

import ast

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_decorate_function_emits_at() -> None:
    py = transpile(
        """
function object mark(f) {
    return f
}

@mark
function void hello() {
    print("hi")
}
"""
    )
    ast.parse(py)
    assert "@mark" in py
    assert "def hello" in py


def test_stacked_decorators() -> None:
    py = transpile(
        """
function object a(f) {
    return f
}
function object b(f) {
    return f
}

@a
@b
function int answer() {
    return 42
}
"""
    )
    ast.parse(py)
    assert py.index("@a") < py.index("@b") < py.index("def answer")


def test_decorate_method() -> None:
    py = transpile(
        """
function object route(f) {
    return f
}

package class Api {
    @route
    public string ping() {
        return "pong"
    }
}
"""
    )
    ast.parse(py)
    assert "@route" in py
    assert "def ping" in py


def test_decorate_call_expr() -> None:
    py = transpile(
        """
function object route(string path) {
    return mark
}

function object mark(f) {
    return f
}

@route("/health")
function void health() {
    print("ok")
}
"""
    )
    ast.parse(py)
    assert '@route("/health")' in py or "@route('/health')" in py


def test_decorator_on_field_rejected() -> None:
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
package class C {
    @route
    private int x
}
"""
        )
    assert ei.value.code == "pys.decorator-target"


def test_emit_keeps_nominal_param_annotation() -> None:
    """FastAPI Request injection needs a Python annotation (ADR-026 field research)."""
    py = transpile(
        """
import Request from fastapi

function void handle(Request request) {
    print("ok")
}
"""
    )
    ast.parse(py)
    assert "def handle(request: Request):" in py
    with pytest.raises(TranspileError) as ei:
        transpile(
            """
@oops
int x = 1
"""
        )
    assert ei.value.code == "pys.decorator-target"
