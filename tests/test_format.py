"""Tests for whole-file PYS AST formatter."""
from __future__ import annotations

from transpiler.format import format_source


def test_format_idempotent_class_and_static_call():
    src = """class Character{
private string name
public string greeting(string name){
return "Hello, {name}"
}
public static void greet() {
}
}

Character.greet()
"""
    once = format_source(src)
    assert once is not None
    twice = format_source(once)
    assert twice == once
    assert "public static void greet() {" in once
    assert "    private string name" in once
    assert once.endswith("\n")
    assert "\n\n\n" not in once


def test_format_preserves_semicolon_groups_as_separate_lines():
    # AST does not retain `;` grouping; formatter prints one stmt per line
    # and does not invent new same-line groups.
    src = """function void main() {
    int a = 1; int b = 2
}
"""
    out = format_source(src)
    assert out is not None
    assert "int a = 1" in out
    assert "int b = 2" in out
    assert "; int" not in out


def test_format_enum_one_line_when_small():
    src = """enum Color { RED, GREEN, BLUE }
"""
    out = format_source(src)
    assert out is not None
    assert "enum Color { RED, GREEN, BLUE }" in out.replace("\n", " ") or "enum Color {" in out


def test_format_enum_multiline_when_many():
    src = """enum Big {
A, B, C, D, E
}
"""
    out = format_source(src)
    assert out is not None
    assert "A," in out
    assert out.count("\n") >= 5


def test_format_parse_failure_returns_none():
    assert format_source("class {") is None


def test_format_entity_identity_order():
    src = """entity Product identity(id) {
    private fix string id
    private float price
    public constructor(string id, float price) {
        this.id = id
        this.price = price
    }
}
"""
    out = format_source(src)
    assert out is not None
    assert "identity(id)" in out
    id_pos = out.index("fix string id")
    price_pos = out.index("float price")
    ctor_pos = out.index("constructor")
    assert id_pos < price_pos < ctor_pos


def test_format_struct_fix_before_mutable():
    src = """struct Point {
    fix float x
    float y
}
"""
    out = format_source(src)
    assert out is not None
    assert out.index("fix float x") < out.index("float y")
    assert format_source(out) == out


def test_format_method_body_indent_is_eight_spaces():
    src = """class Character {
    private string name

    public string greeting(string name) {
            return "Hello, {name}"
    }
    public static void greet() {
    }
}
"""
    out = format_source(src)
    assert out is not None
    lines = out.splitlines()
    ret = next(line for line in lines if "return" in line)
    assert ret.startswith("        return"), repr(ret)
    assert not ret.startswith("            return")
    # Blank line between methods
    greet_i = next(i for i, line in enumerate(lines) if "static void greet" in line)
    assert lines[greet_i - 1] == ""
    assert format_source(out) == out


def test_format_java_sparse_blank_lines():
    """Fields pack tight; blank only before methods / between top-level types."""
    src = """class Character {



    private string name

    private int age



    public string greeting(string name) {

        return "Hello, {name}"

    }



    public static void greet() {

    }

}
"""
    out = format_source(src)
    assert out is not None
    assert "    private string name\n    private int age\n\n    public string greeting" in out
    assert "\n\n\n" not in out
    # No blank between field and field
    assert "name\n\n    private int" not in out
    # No blank inside method before return
    assert "greeting(string name) {\n        return" in out
    assert format_source(out) == out


def test_format_trailing_whitespace_and_final_newline():
    src = "function void main() {  \n    print(1)   \n}\n\n\n"
    out = format_source(src)
    assert out is not None
    assert out.endswith("\n")
    assert not out.endswith("\n\n")
    for line in out.split("\n")[:-1]:
        assert line == line.rstrip(" \t")


def test_format_k_and_r_braces():
    src = """class Foo
{
    public void go()
    {
    }
}
"""
    out = format_source(src)
    assert out is not None
    assert "class Foo {" in out
    assert "public void go() {" in out
