"""JavaScript emit target — MVP compile tests."""
from __future__ import annotations

import pytest

from transpiler.emit.javascript import JsEmitError
from transpiler.pipeline import compile_pys


def test_js_emit_print_and_literal() -> None:
    js = compile_pys('print("hi")\n', target="javascript")
    assert "console.log(_pys_format(" in js
    assert '"hi"' in js
    assert "function _pys_format" in js


def test_js_emit_if_and_vars() -> None:
    src = """
int x = 3
if (x > 2) {
    print(x)
} else {
    print(0)
}
"""
    js = compile_pys(src, target="javascript")
    assert "let x = 3;" in js
    assert "if ((x > 2))" in js or "if (x > 2)" in js
    assert "console.log" in js


def test_js_emit_class_method_call() -> None:
    src = """
class Counter {
    private int value

    public constructor() {
        this.value = 0
    }

    public bump() {
        this.value = this.value + 1
    }

    public int getValue() {
        return this.value
    }
}

Counter c = Counter()
c.bump()
print(c.getValue())
"""
    js = compile_pys(src, target="javascript")
    assert "class Counter" in js
    assert "constructor()" in js
    assert "new Counter()" in js
    assert "c.bump()" in js


def test_js_emit_explicit_cast() -> None:
    """Given (int) f, When emit JS, Then Number/Math.trunc wraps the inner expr."""
    src = """
float f = 3.7
int a = (int) f
print(a)
"""
    js = compile_pys(src, target="javascript")
    assert "Math.trunc(Number(f))" in js
    assert "let a =" in js


def test_js_emit_lambda_expression() -> None:
    src = """
lambda<int -> int> double = n => n * 2
print(double(5))
"""
    js = compile_pys(src, target="javascript")
    assert "=>" in js
    assert "double(5)" in js


def test_js_emit_slice_tuple_set() -> None:
    src = """
list<int> arr = [1, 2, 3, 4, 5, 6]
print(arr[1:5])
print(arr[1:6:2])
tuple t = (1, "a")
print(t[0])
set<int> s = {1, 2, 3}
print(s)
"""
    js = compile_pys(src, target="javascript")
    assert "_pys_slice(arr, 1, 5, null)" in js
    assert "_pys_slice(arr, 1, 6, 2)" in js
    assert '[1, "a"]' in js or '[1, \\"a\\"]' in js
    assert "new Set([1, 2, 3])" in js


def test_js_emit_switch_and_enum() -> None:
    src = """
enum Color {
    Red,
    Green
}
Color c = Color.Red
switch (c) {
    case Color.Red:
        print("r")
    default:
        print("other")
}
string label = switch (c) {
    case Color.Red => "red"
    default => "x"
}
print(label)
"""
    js = compile_pys(src, target="javascript")
    assert "Object.freeze" in js
    assert "_pys_enum_member" in js
    assert "Color.Red" in js


def test_js_emit_entity_and_result() -> None:
    src = """
entity Product identity(id) {
    public fix int id
    public string name

    public constructor(int id, string name) {
        this.id = id
        this.name = name
    }
}

result<int, string> r = ok(42)
switch (r) {
    case ok(v):
        print(v)
    case error(e):
        print(e)
}
"""
    js = compile_pys(src, target="javascript")
    assert "class Product" in js
    assert "equals(other)" in js
    assert "_pys_ok(" in js


def test_js_emit_rejects_python_package_import() -> None:
    with pytest.raises(JsEmitError, match="Python package"):
        compile_pys("import tkinter as tk\n", target="javascript")


def test_js_emit_npm_mapped_import() -> None:
    js = compile_pys('import nodegui as ng\nprint("x")\n', target="javascript")
    assert 'from "@nodegui/nodegui"' in js


def test_js_emit_namespace_constructor_uses_new() -> None:
    js = compile_pys(
        'import nodegui as ng\nobject win = ng.QMainWindow()\n',
        target="javascript",
    )
    assert "new ng.QMainWindow()" in js


def test_js_emit_append_and_loop() -> None:
    src = """
list<int> xs = [1, 2]
xs.append(3)
xs.loop(print)
"""
    js = compile_pys(src, target="javascript")
    assert ".push(3)" in js
    assert ".map(print)" in js


def test_js_emit_tasks_shared_and_await() -> None:
    src = """
shared int n = 0
tasks {
    task {
        n = n + 1
    }
}
print(n)
"""
    js = compile_pys(src, target="javascript")
    assert "_PysTaskGroup" in js
    assert "_PysShared" in js
    assert "n.set(" in js or ".set(" in js


def test_js_emit_data_equals_and_to_bin() -> None:
    src = """
data Point {
    int x
    int y
}
Point a = Point(1, 2)
Point b = Point(1, 2)
print(a == b)
print(toBin(10, 8))
"""
    js = compile_pys(src, target="javascript")
    assert "equals(other)" in js
    assert "_pys_value_eq(" in js
    assert "_pys_to_bin(" in js


def test_js_emit_rejects_decorators() -> None:
    src = """
@app.get("/")
function void hi() {
    print(1)
}
"""
    with pytest.raises(JsEmitError, match="decorator"):
        compile_pys(src, target="javascript")


def test_python_target_unchanged() -> None:
    py = compile_pys('print("hi")\n', target="python")
    assert "print(" in py
    assert "console.log" not in py
