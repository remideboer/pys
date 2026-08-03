"""Find Usages / references for PYS identifiers (IDE)."""

from __future__ import annotations

from pathlib import Path

from transpiler.ide import find_usages


def test_find_usages_same_package(tmp_path: Path) -> None:
    (tmp_path / "lib.pys").write_text(
        "package function int bump(int n) {\n    return n + 1\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text(
        'import bump from lib\nint a = bump(1)\nint b = bump(2)\nprint("bump")\n',
        encoding="utf-8",
    )
    hits = find_usages(main, "bump")
    # lib: function name; main: import name + two calls. String literal ignored.
    assert len(hits) == 4
    by_file = {}
    for h in hits:
        by_file.setdefault(Path(h["file"]).name, []).append(h["line"])
    assert by_file["lib.pys"] == [1]
    assert sorted(by_file["main.pys"]) == [1, 2, 3]


def test_find_usages_skips_keywords_and_empty(tmp_path: Path) -> None:
    src = tmp_path / "x.pys"
    src.write_text("function noop() {\n    return\n}\n", encoding="utf-8")
    assert find_usages(src, "function") == []
    assert find_usages(src, "") == []
    assert find_usages(src, "int") == []


def test_find_usages_dotted_uses_last_segment(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text(
        "enum Color {\n    RED = 1\n    BLUE = 2\n}\nColor c = Color.RED\nprint(Color.RED)\n",
        encoding="utf-8",
    )
    hits = find_usages(src, "Color.RED")
    # member decl + Color.RED + Color.RED
    assert len(hits) == 3
    assert sorted(h["line"] for h in hits) == [2, 5, 6]
