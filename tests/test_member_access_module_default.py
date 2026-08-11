"""Omitted class/entity member access defaults to module (CER-058)."""
from __future__ import annotations

from transpiler.parse import parse_program
from transpiler.transpiler import transpile


def test_bare_entity_field_and_method_default_to_module() -> None:
    src = """
entity Item identity(id) {
    fix int id
    string label

    constructor(int id, string label) {
        this.id = id
        this.label = label
    }

    string tag() {
        return this.label
    }
}
"""
    tree = parse_program(src)
    ent = next(s for s in tree.body if getattr(s, "name", None) == "Item")
    assert next(f for f in ent.fields if f.name == "label").access == "module"
    assert next(m for m in ent.methods if m.name == "tag").access == "module"
    assert next(m for m in ent.methods if m.is_constructor).access == "module"
    transpile(src)


def test_explicit_public_still_public() -> None:
    src = """
class Car {
    public int year

    public drive() {
        print(this.year)
    }
}
"""
    tree = parse_program(src)
    cls = next(s for s in tree.body if getattr(s, "name", None) == "Car")
    assert next(f for f in cls.fields if f.name == "year").access == "public"
    assert next(m for m in cls.methods if m.name == "drive").access == "public"
    transpile(src)
