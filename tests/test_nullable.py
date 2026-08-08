"""BDD coverage for explicit nullable<T> and non-null-by-default semantics."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.ide import analyze_file
from transpiler.lex import TokenKind, tokenize
from transpiler.parse import parse_program, parse_program_from_tokens
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError, transpile


def test_nullable_type_parses_with_rd_and_peg_parity() -> None:
    """Given nested nullable types, both parser engines preserve their position."""
    source = (
        "nullable<list<string>> names = null\n"
        "list<nullable<string>> aliases = [\"Ada\", null]\n"
        "function result<nullable<string>, string> lookup() {\n"
        "    return ok(null)\n"
        "}\n"
    )
    tokens = tokenize(source)

    rd = parse_program_from_tokens(tokens, engine="rd")
    peg = parse_program_from_tokens(tokens, engine="peg")

    assert rd == peg
    assert rd.body[0].declare_type == "nullable<list<string>>"
    assert rd.body[1].declare_type == "list<nullable<string>>"
    assert rd.body[2].return_type == "result<nullable<string>, string>"


def test_nullable_is_a_reserved_keyword() -> None:
    tokens = tokenize("nullable<string> name = null\n")
    assert any(
        token.kind == TokenKind.KEYWORD and token.text == "nullable"
        for token in tokens
    )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("nullable<void> value = null\n", "void is not a runtime value"),
        ("nullable<nullable<string>> value = null\n", "already nullable"),
    ],
)
def test_nullable_rejects_invalid_underlying_types(source: str, message: str) -> None:
    with pytest.raises(TranspileError, match=message):
        parse_program(source)


def test_plain_type_rejects_null_with_actionable_diagnostic(tmp_path: Path) -> None:
    """Scenario A: ordinary T is non-null by default."""
    source = tmp_path / "main.pys"
    source.write_text("string name = null\n", encoding="utf-8")

    result = analyze_file(source)

    assert result["ok"] is False
    assert result["error"]["code"] == "pys.null-non-nullable"
    assert result["error"]["suggested_fix"] == "nullable<string> name = null"
    assert "does not allow null" in result["error"]["message"]


def test_nullable_accepts_null_and_present_value() -> None:
    """Scenario B: nullable<T> accepts exactly absence or a compatible T."""
    analyze(
        parse_program(
            'nullable<string> name = null\n'
            'name = "Fatima"\n'
            'name = null\n'
        )
    )
    py = transpile("nullable<string> name = null\n")
    assert "name = None" in py


def test_pys_output_formats_absence_as_null_not_python_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    py = transpile(
        "nullable<int> unknown = null\n"
        "print(unknown)\n"
        "print(str(unknown))\n"
        'print("value={unknown}")\n'
    )

    exec(py, {})

    assert capsys.readouterr().out.splitlines() == ["null", "null", "value=null"]


def test_var_cannot_infer_an_underlying_type_from_null() -> None:
    with pytest.raises(TranspileError, match="Cannot infer an underlying type from null") as exc:
        analyze(parse_program("var name = null\n"))
    assert exc.value.code == "pys.null-infer"


def test_nullable_member_use_requires_proof() -> None:
    """Scenario C: nullable member access is rejected without a dominating check."""
    source = (
        "nullable<string> name = null\n"
        "print(name.upper())\n"
    )
    with pytest.raises(TranspileError, match="may be null") as exc:
        analyze(parse_program(source))
    assert exc.value.code == "pys.nullable-use-before-check"


def test_null_check_narrows_inside_branch_and_guard_survivor() -> None:
    """Scenario D: branch and exiting-guard facts expose the underlying type."""
    analyze(
        parse_program(
            "function string display(nullable<string> name) {\n"
            "    if (name != null) {\n"
            "        return name.upper()\n"
            "    }\n"
            "    return \"(geen naam)\"\n"
            "}\n"
            "function string guarded(nullable<string> name) {\n"
            "    if (name == null) {\n"
            "        return \"(geen naam)\"\n"
            "    }\n"
            "    return name.upper()\n"
            "}\n"
        )
    )


def test_else_and_short_circuit_paths_narrow_nullable_value() -> None:
    analyze(
        parse_program(
            "function void show(nullable<string> name) {\n"
            "    if (name == null) {\n"
            "        print(\"missing\")\n"
            "    } else {\n"
            "        print(name.upper())\n"
            "    }\n"
            "    if (name != null and name.upper() == \"ADA\") {\n"
            "        print(\"match\")\n"
            "    }\n"
            "}\n"
        )
    )


def test_nullable_switch_null_case_narrows_other_arms() -> None:
    analyze(
        parse_program(
            "function void show(nullable<string> name) {\n"
            "    switch (name) {\n"
            "        case null:\n"
            "            print(\"missing\")\n"
            "        default:\n"
            "            print(name.upper())\n"
            "    }\n"
            "}\n"
        )
    )


def test_shared_nullable_requires_a_local_snapshot_before_narrowing() -> None:
    source = (
        "shared nullable<string> name = null\n"
        "if (name != null) {\n"
        "    print(name.upper())\n"
        "}\n"
    )
    with pytest.raises(TranspileError, match="may be null"):
        analyze(parse_program(source))


def test_atomic_nullable_is_rejected() -> None:
    with pytest.raises(TranspileError, match="atomic nullable") as exc:
        parse_program("atomic nullable<int> counter = null\n")
    assert exc.value.code == "pys.nullable-atomic"


def test_reassignment_invalidates_nullable_narrowing() -> None:
    """Scenario E: a previous proof cannot survive assignment of null."""
    source = (
        "nullable<string> name = \"Ada\"\n"
        "if (name != null) {\n"
        "    name = null\n"
        "    print(name.upper())\n"
        "}\n"
    )
    with pytest.raises(TranspileError, match="may be null"):
        analyze(parse_program(source))


def test_nullable_entity_identity_is_rejected() -> None:
    """Scenario H: entity identity remains present and stable."""
    source = (
        "entity Customer identity(customerId) {\n"
        "    private fix nullable<int> customerId\n"
        "    public Customer(nullable<int> customerId) {\n"
        "        this.customerId = customerId\n"
        "    }\n"
        "}\n"
    )
    with pytest.raises(TranspileError, match="identity.*non-null") as exc:
        analyze(parse_program(source))
    assert exc.value.code == "pys.nullable-identity"


def test_nested_nullable_position_and_result_absence_remain_distinct() -> None:
    """Scenarios I/J: wrapper position is retained and ok(null) is not error."""
    analyze(
        parse_program(
            "nullable<list<string>> missingList = null\n"
            "list<nullable<string>> presentList = [\"Ada\", null]\n"
            "result<nullable<string>, string> missing = ok(null)\n"
            "result<nullable<string>, string> failure = error(\"offline\")\n"
        )
    )


def test_nullable_struct_wrapper_and_field_preserve_complete_value_semantics() -> None:
    source = (
        "struct Profile {\n"
        "    nullable<string> nickname = null\n"
        "}\n"
        "nullable<Profile> profile = null\n"
        "Profile present = Profile(null)\n"
    )
    analyze(parse_program(source))


def test_non_null_check_warns_as_redundant() -> None:
    module = analyze(
        parse_program(
            'string name = "Ada"\n'
            "if (name == null) {\n"
            "    print(\"never\")\n"
            "}\n"
        )
    )

    assert any(
        warning.code == "pys.null-redundant-check"
        for warning in module.analysis_warnings
    )


def test_sql_null_and_empty_string_remain_distinct(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scenarios F/G: SQL NULL ↔ PYS null; empty string stays present."""
    py = transpile(
        "function nullable<string> cellNullableStr(value) {\n"
        "    if (value == null) {\n"
        "        return null\n"
        "    }\n"
        "    return str(value)\n"
        "}\n"
        "function string cellStr(value) {\n"
        "    if (value == null) {\n"
        '        return \"__contract_violation__\"\n'
        "    }\n"
        "    return str(value)\n"
        "}\n"
        "nullable<string> absent = cellNullableStr(null)\n"
        'nullable<string> empty = cellNullableStr("")\n'
        "print(absent == null)\n"
        "print(empty == null)\n"
        'print(empty == "")\n'
        'print(cellStr("paid"))\n'
        "print(cellStr(null))\n"
    )
    exec(py, {})
    assert capsys.readouterr().out.splitlines() == [
        "True",
        "False",
        "True",
        "paid",
        "__contract_violation__",
    ]


def test_shop_database_example_transpiles_with_nullable_contracts() -> None:
    from transpiler.transpiler import transpile_with_modules

    modules = transpile_with_modules(Path("examples/database/shop_app.pys"))
    assert "ShopGuiApp" in modules["gui"]
    assert "cellNullableStr" in modules["db"]
    assert 'return ""' not in modules["db"]
    assert "NULLIF" not in modules["mappers"]


def test_find_usages_skips_nullable_keyword() -> None:
    from transpiler.ide import find_usages

    assert find_usages("nullable<string> name = null\n", "nullable") == []


def test_analyze_file_exports_narrowed_types(tmp_path: Path) -> None:
    source = tmp_path / "main.pys"
    source.write_text(
        "nullable<string> name = \"Ada\"\n"
        "if (name != null) {\n"
        "    print(name.upper())\n"
        "}\n",
        encoding="utf-8",
    )
    result = analyze_file(source)
    assert result["ok"] is True
    assert result["variable_types"].get("name") == "nullable<string>"
    assert any(type_name == "string" for type_name in result["narrowed_types"].values())
