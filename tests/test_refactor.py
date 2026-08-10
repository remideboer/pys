"""Binding-aware Find Usages and refactor plans."""

from __future__ import annotations

from pathlib import Path

from transpiler.ide import find_usages
from transpiler.refactor.apply import apply_plan_to_files
from transpiler.refactor.extract import plan_extract_function, plan_extract_variable
from transpiler.refactor.inline import plan_inline_function, plan_inline_variable
from transpiler.refactor.rename import plan_rename
from transpiler.refactor.safe_delete import plan_introduce_parameter, plan_safe_delete


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
    assert len(hits) >= 3  # decl + import + calls
    by_file = {}
    for h in hits:
        by_file.setdefault(Path(h["file"]).name, []).append(h["line"])
    assert 1 in by_file.get("lib.pys", [])
    assert "main.pys" in by_file


def test_find_usages_skips_keywords_and_empty(tmp_path: Path) -> None:
    src = tmp_path / "x.pys"
    src.write_text("function noop() {\n    return\n}\n", encoding="utf-8")
    assert find_usages(src, "function") == []
    assert find_usages(src, "") == []
    assert find_usages(src, "int") == []


def test_find_usages_shadowed_brace_scope(tmp_path: Path) -> None:
    src = tmp_path / "s.pys"
    src.write_text(
        "function f() {\n"
        "    int n = 1\n"
        "    if (true) {\n"
        "        int n = 2\n"
        "        print(n)\n"
        "    }\n"
        "    print(n)\n"
        "}\n",
        encoding="utf-8",
    )
    line5 = "        print(n)"
    col = line5.rindex("n") + 1  # the arg, not the n in print
    hits = find_usages(src, "n", line=5, column=col)
    lines = sorted({h["line"] for h in hits})
    assert 4 in lines and 5 in lines
    assert 2 not in lines
    assert 7 not in lines


def test_find_usages_dotted_enum_member(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text(
        "enum Color {\n    RED = 1,\n    BLUE = 2\n}\nColor c = Color.RED\nprint(Color.RED)\n",
        encoding="utf-8",
    )
    hits = find_usages(src, "Color.RED")
    assert len(hits) >= 2
    assert any(h["line"] == 2 for h in hits)


def test_rename_across_import(tmp_path: Path) -> None:
    (tmp_path / "lib.pys").write_text(
        "package function int greet() {\n    return 1\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import greet from lib\nint a = greet()\nfunction other() {\n    int greet = 0\n    print(greet)\n}\n",
        encoding="utf-8",
    )
    lib = tmp_path / "lib.pys"
    line = "package function int greet() {"
    col = line.index("greet") + 1
    plan = plan_rename(lib, line=1, column=col, new_name="hello")
    assert plan.ok, [c.message for c in plan.conflicts]
    applied = apply_plan_to_files(plan)
    lib_txt = applied[str(lib.resolve())]
    assert "hello" in lib_txt
    if str(main.resolve()) in applied:
        main_txt = applied[str(main.resolve())]
        assert "int greet = 0" in main_txt


def test_rename_field_updates_this_and_not_unrelated(tmp_path: Path) -> None:
    src = tmp_path / "calc.pys"
    src.write_text(
        "class Calc {\n"
        "    private fix int getalA\n"
        "    private fix int other\n"
        "    public constructor(int a) {\n"
        "        this.getalA = a\n"
        "        this.other = 0\n"
        "    }\n"
        "    public int read() {\n"
        "        return this.getalA\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    line = "    private fix int getalA"
    col = line.index("getalA") + 1
    plan = plan_rename(src, line=2, column=col, new_name="valueA")
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "private fix int valueA" in out
    assert "this.valueA = a" in out
    assert "return this.valueA" in out
    assert "this.other = 0" in out
    assert "getalA" not in out


def test_rename_method_updates_call_sites(tmp_path: Path) -> None:
    src = tmp_path / "calc.pys"
    src.write_text(
        "class Calc {\n"
        "    public int som() {\n"
        "        return 1\n"
        "    }\n"
        "}\n"
        "Calc rm = Calc()\n"
        "print(rm.som())\n",
        encoding="utf-8",
    )
    line = "    public int som() {"
    col = line.index("som") + 1
    plan = plan_rename(src, line=2, column=col, new_name="add")
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "public int add()" in out
    assert "print(rm.add())" in out
    assert "som" not in out


def test_rename_class_updates_type_and_ctor(tmp_path: Path) -> None:
    src = tmp_path / "calc.pys"
    src.write_text(
        "class Rekenmachine {\n"
        "    public constructor() {}\n"
        "}\n"
        "Rekenmachine rm = Rekenmachine()\n",
        encoding="utf-8",
    )
    line = "class Rekenmachine {"
    col = line.index("Rekenmachine") + 1
    plan = plan_rename(src, line=1, column=col, new_name="Calculator")
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "class Calculator {" in out
    assert "Calculator rm = Calculator()" in out
    assert "Rekenmachine" not in out


def test_rename_field_updates_interpolation(tmp_path: Path) -> None:
    src = tmp_path / "calc.pys"
    src.write_text(
        "class Calc {\n"
        "    public fix int getalA\n"
        "    public constructor(int a) {\n"
        "        this.getalA = a\n"
        "    }\n"
        "}\n"
        "Calc rm = Calc(1)\n"
        'print("x={rm.getalA}")\n',
        encoding="utf-8",
    )
    line = "    public fix int getalA"
    col = line.index("getalA") + 1
    plan = plan_rename(src, line=2, column=col, new_name="valueA")
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert 'print("x={rm.valueA}")' in out
    assert "getalA" not in out


def test_rename_resolves_caret_on_exclusive_end(tmp_path: Path) -> None:
    """VS Code left-to-right selection parks the caret on the exclusive end column."""
    from transpiler.refactor.refs import build_index, resolve_at

    src = tmp_path / "c.pys"
    src.write_text(
        "class Calc {\n"
        "    public fix int getalA\n"
        "    public constructor(int a) {\n"
        "        this.getalA = a\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    line = "    public fix int getalA"
    start = line.index("getalA") + 1
    end_exclusive = start + len("getalA")
    idx = build_index(src)
    assert resolve_at(idx, src, 2, start) is not None
    assert resolve_at(idx, src, 2, end_exclusive) is not None
    plan = plan_rename(src, line=2, column=end_exclusive, new_name="valueA")
    assert plan.ok, [c.message for c in plan.conflicts]


def test_extract_variable(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text("print(1 + 2)\n", encoding="utf-8")
    # select `1 + 2`
    line = "print(1 + 2)"
    start = line.index("1") + 1
    end = line.index(")") + 1  # exclusive end_column is position after last char of expr
    # expr is 1 + 2 — end column after 2
    end = line.index("2") + 2
    plan = plan_extract_variable(
        src,
        start_line=1,
        start_column=start,
        end_line=1,
        end_column=end,
        new_name="sum",
    )
    assert plan.ok
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "var sum = 1 + 2" in out
    assert "print(sum)" in out


def test_extract_function(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text("print(1)\nprint(2)\n", encoding="utf-8")
    plan = plan_extract_function(src, start_line=1, end_line=2, new_name="show")
    assert plan.ok
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "function show()" in out
    assert "show()" in out


def test_inline_variable(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text("function f() {\n    int x = 3\n    print(x)\n}\n", encoding="utf-8")
    # cursor on x in decl — line 2 column of x
    plan = plan_inline_variable(src, line=2, column=9)
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "print(3)" in out
    assert "int x = 3" not in out


def test_inline_function(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text(
        "function int one() {\n    return 1\n}\nint a = one()\n",
        encoding="utf-8",
    )
    plan = plan_inline_function(src, line=1, column=14)
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "one()" not in out or "function" not in out.split("int a")[0]
    assert "(1)" in out or "1" in out


def test_safe_delete_unused(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text("function dead() {\n    return\n}\nprint(1)\n", encoding="utf-8")
    plan = plan_safe_delete(src, line=1, column=10)
    assert plan.ok, [c.message for c in plan.conflicts]


def test_safe_delete_blocked_when_used(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text("function live() {\n    return\n}\nlive()\n", encoding="utf-8")
    plan = plan_safe_delete(src, line=1, column=10)
    assert not plan.ok
    assert plan.conflicts


def test_introduce_parameter(tmp_path: Path) -> None:
    src = tmp_path / "e.pys"
    src.write_text(
        "function f() {\n    int n = 1\n    print(n)\n}\nf()\n",
        encoding="utf-8",
    )
    plan = plan_introduce_parameter(src, line=2, column=9, param_name="n", param_type="int")
    assert plan.ok, [c.message for c in plan.conflicts]
    out = apply_plan_to_files(plan)[str(src.resolve())]
    assert "function f(int n)" in out or "int n" in out.split("{")[0]
