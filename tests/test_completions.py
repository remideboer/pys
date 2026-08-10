"""Completions: in-scope names and accessible members."""
from __future__ import annotations

from transpiler.completions import completions_at


_SRC = """
class Rekenmachine {
    private fix int getalA
    private fix int getalB

    public constructor(int a, int b) {
        this.getalA = a
        this.getalB = b
    }

    public int som() {
        return this.getalA + this.getalB
    }

    public int vermenigvuldigd() {
        return this.getalA * this.getalB
    }
}

Rekenmachine rm = Rekenmachine(4, 5)
print(rm.som())
"""


def test_member_completions_after_dot_exclude_private() -> None:
    src = _SRC + "rm.\n"
    lines = src.splitlines()
    line = len(lines)
    column = len(lines[-1]) + 1
    result = completions_at(src, line=line, column=column)
    assert result["ok"] is True
    assert result.get("mode") == "members"
    labels = {i["label"] for i in result["items"]}
    assert "som" in labels
    assert "vermenigvuldigd" in labels
    assert "getalA" not in labels
    assert "getalB" not in labels


def test_member_completions_this_inside_class_includes_private() -> None:
    src = """
class C {
    private int x
    public int y

    public int get() {
        return this.
    }
}
"""
    lines = src.splitlines()
    line = next(i + 1 for i, L in enumerate(lines) if "this." in L)
    column = lines[line - 1].index("this.") + len("this.") + 1
    result = completions_at(src, line=line, column=column)
    assert result["ok"] is True
    labels = {i["label"] for i in result["items"]}
    assert "x" in labels
    assert "y" in labels


def test_scope_completions_include_binding() -> None:
    src = """
class C {
    public int m() {
        int local = 1
        return local
    }
}
"""
    lines = src.splitlines()
    line = next(i + 1 for i, L in enumerate(lines) if "return local" in L)
    column = lines[line - 1].index("local") + 1
    result = completions_at(src, line=line, column=column)
    assert result["ok"] is True
    labels = {i["label"] for i in result["items"]}
    assert "local" in labels
    assert "C" in labels
