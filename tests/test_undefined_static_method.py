"""Undefined static method diagnostics + Create Static Method planner."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.pipeline import compile_pys
from transpiler.refactor.apply import apply_plan_to_files
from transpiler.refactor.create_static_method import plan_create_static_method
from transpiler.transpiler import TranspileError


def test_undefined_static_method_on_type_name_call() -> None:
    src = """
class Character {
    public string greeting(string name) {
        return "Hello, {name}"
    }
}

Character.greet()
"""
    with pytest.raises(TranspileError) as ei:
        compile_pys(src)
    err = ei.value
    assert err.code == "pys.undefined-static-method"
    assert "greet" in str(err)
    assert "Character" in str(err)
    assert err.suggested_fix == "create-static-method"


def test_instance_method_via_type_name_is_rejected() -> None:
    src = """
class Character {
    public string greeting(string name) {
        return "Hello, {name}"
    }
}

Character.greeting("Ada")
"""
    with pytest.raises(TranspileError) as ei:
        compile_pys(src)
    err = ei.value
    assert err.code == "pys.instance-member-via-type"
    assert "greeting" in str(err)


def test_static_method_call_ok() -> None:
    src = """
class MathUtil {
    public static int twice(int n) {
        return n * 2
    }
}

int x = MathUtil.twice(3)
print(x)
"""
    compile_pys(src)


def test_create_static_method_void_no_args(tmp_path: Path) -> None:
    src = (
        "class Character{\n"
        "    private string name\n"
        "\n"
        "    public string greeting(string name){\n"
        '        return "Hello, {name}"\n'
        "    }\n"
        "}\n"
        "\n"
        "Character.greet()\n"
    )
    path = tmp_path / "t.pys"
    path.write_text(src, encoding="utf-8")
    plan = plan_create_static_method(path, line=9, column=11, class_name="Character", method_name="greet")
    assert plan.ok is True
    after = apply_plan_to_files(plan, {str(path.resolve()): src})
    text = after[str(path.resolve())]
    assert "public static void greet()" in text
    compile_pys(text)


def test_create_static_method_infers_args_and_return(tmp_path: Path) -> None:
    src = (
        "class Util {\n"
        "}\n"
        "\n"
        'string s = Util.fmt("hi", 2)\n'
    )
    path = tmp_path / "u.pys"
    path.write_text(src, encoding="utf-8")
    plan = plan_create_static_method(path, line=4, column=12)
    assert plan.ok is True
    after = apply_plan_to_files(plan, {str(path.resolve()): src})
    text = after[str(path.resolve())]
    assert "public static string fmt(string text, int n)" in text
    assert 'return ""' in text
    compile_pys(text)
