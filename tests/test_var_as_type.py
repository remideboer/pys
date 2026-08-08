"""ADR-025: var is declaration-only; object for opaque types."""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def _ok(src: str) -> None:
    transpile(src)


def _err(src: str, *, code: str = "pys.var-as-type") -> TranspileError:
    with pytest.raises(TranspileError) as ei:
        transpile(src)
    err = ei.value
    assert err.code == code
    return err


def test_var_local_declaration_ok() -> None:
    _ok("var x = 1\nprint(x)\n")


def test_var_inside_function_ok() -> None:
    _ok(
        """
function void f() {
    var x = 2
    print(x)
}
f()
"""
    )


def test_var_return_type_rejected() -> None:
    err = _err(
        """
package class C {
    public var m() {
        return 1
    }
}
"""
    )
    assert "cannot be used as a type" in str(err)


def test_var_param_rejected() -> None:
    err = _err(
        """
function int f(var x) {
    return 1
}
"""
    )
    assert err.suggested_fix == "x"


def test_var_field_rejected() -> None:
    _err(
        """
package class C {
    private var q

    public C() {
    }
}
"""
    )


def test_list_var_generic_rejected() -> None:
    _err("list<var> xs = []\n")


def test_lambda_var_param_rejected() -> None:
    _err(
        """
lambda<int -> int> f = (var x) => x + 1
"""
    )


def test_object_return_and_field_ok() -> None:
    _ok(
        """
package class C {
    private object q

    public C() {
        this.q = 1
    }

    public object get() {
        return this.q
    }
}
"""
    )


def test_omitted_param_type_ok() -> None:
    _ok(
        """
function void serve(conn) {
    print(conn)
}
serve(1)
"""
    )
