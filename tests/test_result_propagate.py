"""BDD coverage for result<T, E>, ok/err, propagate, and panic."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.ast_nodes import (
    AssignStmt,
    FunctionDef,
    PropagateExpr,
    ResultCtor,
    ResultPattern,
    ReturnStmt,
    SwitchStmt,
)
from transpiler.lex import TokenKind, tokenize
from transpiler.ide import analyze_file, find_usages
from transpiler.parse import parse_program, parse_program_from_tokens
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError, transpile


def test_result_syntax_parses_type_constructors_and_propagate() -> None:
    """Given result syntax, when parsed, then dedicated AST nodes preserve intent."""
    module = parse_program(
        """
function result<int, string> readNumber() {
    return ok(10)
}
function result<int, string> useNumber() {
    int value = readNumber() propagate
    return err("stop")
}
"""
    )

    read_number, use_number = module.body
    assert isinstance(read_number, FunctionDef)
    assert read_number.return_type == "result<int, string>"
    read_return = read_number.body.statements[0]
    assert isinstance(read_return, ReturnStmt)
    assert isinstance(read_return.value, ResultCtor)
    assert read_return.value.kind == "ok"

    value_decl = use_number.body.statements[0]
    assert isinstance(value_decl, AssignStmt)
    assert isinstance(value_decl.value, PropagateExpr)
    error_return = use_number.body.statements[1]
    assert isinstance(error_return.value, ResultCtor)
    assert error_return.value.kind == "err"


def test_result_syntax_has_rd_and_peg_ast_parity() -> None:
    source = (
        "function result<int, string> readNumber() {\n"
        "    return ok(10)\n"
        "}\n"
        "result<int, string> outcome = readNumber()\n"
        "switch (outcome) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n"
    )
    tokens = tokenize(source)

    assert parse_program_from_tokens(tokens, engine="rd") == parse_program_from_tokens(
        tokens,
        engine="peg",
    )


def test_result_keywords_are_reserved_by_the_lexer() -> None:
    tokens = tokenize("result<int, string> r = ok(1) propagate\nerr(\"x\")\n")
    reserved = {
        token.text
        for token in tokens
        if token.kind == TokenKind.KEYWORD
    }
    assert {"result", "ok", "err", "propagate"} <= reserved


@pytest.mark.parametrize(
    "source",
    [
        "result<int> value = ok(1)\n",
        "result<int, string, bool> value = ok(1)\n",
    ],
)
def test_result_type_requires_success_and_error_type(source: str) -> None:
    with pytest.raises(TranspileError, match="exactly two type arguments"):
        parse_program(source)


def test_result_error_type_cannot_be_void() -> None:
    with pytest.raises(TranspileError, match="E cannot be `void`"):
        parse_program("result<int, void> value = err(1)\n")


def test_result_diagnostic_json_has_stable_code_and_actionable_tip(
    tmp_path: Path,
) -> None:
    source = tmp_path / "main.pys"
    source.write_text(
        "function int wrong() {\n"
        "    int value = 1 propagate\n"
        "    return value\n"
        "}\n",
        encoding="utf-8",
    )

    result = analyze_file(source)

    assert result["ok"] is False
    assert result["error"]["code"] == "pys.propagate-type"
    assert "make the expression return `result<T, E>`" in result["error"]["tips"][0]


def test_ok_without_payload_has_dedicated_constructor_node() -> None:
    module = parse_program(
        "function result<void, string> finish() {\n"
        "    return ok()\n"
        "}\n"
    )
    stmt = module.body[0].body.statements[0]
    assert isinstance(stmt.value, ResultCtor)
    assert stmt.value.value is None


def test_err_requires_a_payload() -> None:
    with pytest.raises(TranspileError, match="requires an error value"):
        parse_program(
            "function result<int, string> fail() {\n"
            "    return err()\n"
            "}\n"
        )


def test_result_constructors_are_checked_against_declared_type() -> None:
    analyze(
        parse_program(
            'result<int, string> success = ok(10)\n'
            'result<int, string> failure = err("bad input")\n'
        )
    )

    with pytest.raises(TranspileError, match="error payload"):
        analyze(parse_program("result<int, string> bad = err(404)\n"))
    with pytest.raises(TranspileError, match="success payload"):
        analyze(parse_program('result<int, string> bad = ok("ten")\n'))


def test_result_constructor_requires_context() -> None:
    with pytest.raises(TranspileError, match="expected `result"):
        analyze(parse_program("var ambiguous = ok(10)\n"))


def test_result_function_must_return_result_value() -> None:
    with pytest.raises(TranspileError, match="Result type mismatch"):
        analyze(
            parse_program(
                "function result<int, string> wrong() {\n"
                "    return 10\n"
                "}\n"
            )
        )


def test_result_constructor_uses_function_parameter_context() -> None:
    analyze(
        parse_program(
            "function void consume(result<int, string> value) {\n"
            "    print(1)\n"
            "}\n"
            "consume(ok(10))\n"
        )
    )


def test_result_argument_cannot_flow_to_plain_parameter() -> None:
    with pytest.raises(TranspileError, match="Argument 1 has type result"):
        analyze(
            parse_program(
                "function result<int, string> readNumber() {\n"
                "    return ok(10)\n"
                "}\n"
                "function void consume(int value) {\n"
                "    print(value)\n"
                "}\n"
                "consume(readNumber())\n"
            )
        )


def test_result_does_not_implicitly_convert_to_success_type() -> None:
    with pytest.raises(TranspileError, match="must be handled"):
        analyze(
            parse_program(
                "function result<int, string> readNumber() {\n"
                "    return ok(10)\n"
                "}\n"
                "int value = readNumber()\n"
            )
        )


def test_propagate_unwraps_matching_result_inside_result_function() -> None:
    analyze(
        parse_program(
            "function result<int, string> readNumber() {\n"
            "    return ok(10)\n"
            "}\n"
            "function result<int, string> useNumber() {\n"
            "    int value = readNumber() propagate\n"
            "    return ok(value)\n"
            "}\n"
        )
    )


def test_result_method_signature_supports_propagation() -> None:
    analyze(
        parse_program(
            "class Reader {\n"
            "    public Reader() {\n"
            "        print(1)\n"
            "    }\n"
            "    public result<int, string> read() {\n"
            "        return ok(10)\n"
            "    }\n"
            "}\n"
            "function result<int, string> useReader(Reader reader) {\n"
            "    int value = reader.read() propagate\n"
            "    return ok(value)\n"
            "}\n"
        )
    )


def test_result_method_boundary_returns_propagated_error(capsys) -> None:
    source = (
        "class Reader {\n"
        "    public result<int, string> read() {\n"
        '        return err("method failed")\n'
        "    }\n"
        "    public result<int, string> use() {\n"
        "        int value = this.read() propagate\n"
        '        print("not reached")\n'
        "        return ok(value)\n"
        "    }\n"
        "}\n"
        "Reader reader = Reader()\n"
        "result<int, string> outcome = reader.use()\n"
        "switch (outcome) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n"
    )

    exec(transpile(source), {})

    assert capsys.readouterr().out == "method failed\n"


def test_propagate_requires_result_operand() -> None:
    with pytest.raises(TranspileError, match="only applies to result"):
        analyze(
            parse_program(
                "function result<int, string> bad() {\n"
                "    int value = 10 propagate\n"
                "    return ok(value)\n"
                "}\n"
            )
        )


def test_propagate_requires_matching_enclosing_error_type() -> None:
    with pytest.raises(TranspileError, match="error type string.*bool"):
        analyze(
            parse_program(
                "function result<int, string> readNumber() {\n"
                '    return err("bad")\n'
                "}\n"
                "function result<int, bool> bad() {\n"
                "    int value = readNumber() propagate\n"
                "    return ok(value)\n"
                "}\n"
            )
        )


def test_propagate_requires_result_returning_function() -> None:
    with pytest.raises(TranspileError, match="returns `result"):
        analyze(
            parse_program(
                "function result<int, string> readNumber() {\n"
                "    return ok(10)\n"
                "}\n"
                "function int bad() {\n"
                "    return readNumber() propagate\n"
                "}\n"
            )
        )


def test_propagate_cannot_cross_task_boundary() -> None:
    with pytest.raises(TranspileError, match="cannot cross a task boundary"):
        analyze(
            parse_program(
                "function result<int, string> readNumber() {\n"
                "    return ok(10)\n"
                "}\n"
                "tasks {\n"
                "    task {\n"
                "        int value = readNumber() propagate\n"
                "        print(value)\n"
                "    }\n"
                "}\n"
            )
        )


def test_entrypoint_propagations_require_one_exact_error_type() -> None:
    with pytest.raises(TranspileError, match="mixes error type bool with string"):
        analyze(
            parse_program(
                "function result<int, string> textError() {\n"
                '    return err("bad")\n'
                "}\n"
                "function result<int, bool> flagError() {\n"
                "    return err(false)\n"
                "}\n"
                "int first = textError() propagate\n"
                "int second = flagError() propagate\n"
            ),
            is_entrypoint=True,
        )


@pytest.mark.parametrize("name", ["ok", "err"])
def test_result_constructor_names_cannot_be_redeclared(name: str) -> None:
    with pytest.raises(TranspileError, match="reserved result constructor"):
        analyze(parse_program(f"int {name} = 1\n"))


def test_imported_result_function_signature_supports_propagate(tmp_path) -> None:
    helper = tmp_path / "helper.pys"
    main = tmp_path / "main.pys"
    helper.write_text(
        "global function result<int, string> readNumber() {\n"
        "    return ok(10)\n"
        "}\n",
        encoding="utf-8",
    )
    main.write_text(
        "import readNumber from helper.pys\n"
        "function result<int, string> useNumber() {\n"
        "    int value = readNumber() propagate\n"
        "    return ok(value)\n"
        "}\n",
        encoding="utf-8",
    )

    analyze(parse_program(main.read_text(encoding="utf-8")), source_path=main)


def test_result_switch_patterns_parse_and_bind_payloads() -> None:
    module = parse_program(
        'result<int, string> outcome = err("bad")\n'
        "switch (outcome) {\n"
        "    case ok(value):\n"
        '        print("#i{value}")\n'
        "    case err(message):\n"
        '        print("#s{message}")\n'
        "}\n"
    )
    switch = module.body[1]
    assert isinstance(switch, SwitchStmt)
    assert [case.labels[0].kind for case in switch.cases] == ["ok", "err"]
    assert all(isinstance(case.labels[0], ResultPattern) for case in switch.cases)
    analyze(module)


def test_result_switch_expression_unwraps_payload() -> None:
    analyze(
        parse_program(
            "result<int, string> outcome = ok(10)\n"
            "int value = switch (outcome) {\n"
            "    case ok(number) => number\n"
            "    case err(message) => 0\n"
            "}\n"
        )
    )


def test_switch_expression_arms_use_expected_result_context(capsys) -> None:
    source = (
        "bool valid = true\n"
        "result<int, string> outcome = switch (valid) {\n"
        "    case true => ok(10)\n"
        '    default => err("invalid")\n'
        "}\n"
        "switch (outcome) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n"
    )

    exec(transpile(source), {})

    assert capsys.readouterr().out == "10\n"


def test_result_switch_expression_must_be_exhaustive() -> None:
    with pytest.raises(TranspileError, match="not exhaustive.*err"):
        analyze(
            parse_program(
                "result<int, string> outcome = ok(10)\n"
                "int value = switch (outcome) {\n"
                "    case ok(number) => number\n"
                "}\n"
            )
        )


def test_result_switch_default_can_complete_exhaustiveness(capsys) -> None:
    source = (
        'result<int, string> outcome = err("bad")\n'
        "switch (outcome) {\n"
        "    case ok(number):\n"
        "        print(number)\n"
        "    default:\n"
        '        print("failed")\n'
        "}\n"
    )

    exec(transpile(source), {})

    assert capsys.readouterr().out == "failed\n"


def test_result_switch_rejects_duplicate_constructor_pattern() -> None:
    with pytest.raises(TranspileError, match="Duplicate result pattern 'ok'"):
        analyze(
            parse_program(
                "result<int, string> outcome = ok(10)\n"
                "switch (outcome) {\n"
                "    case ok(first):\n"
                "        print(first)\n"
                "    case ok(second):\n"
                "        print(second)\n"
                "    case err(message):\n"
                "        print(message)\n"
                "}\n"
            )
        )


def test_result_switch_pattern_cannot_fall_through() -> None:
    with pytest.raises(TranspileError, match="cannot fall through"):
        analyze(
            parse_program(
                "result<int, string> outcome = ok(10)\n"
                "switch (outcome) {\n"
                "    case ok(number):\n"
                "        continue\n"
                "    case err(error):\n"
                "        print(error)\n"
                "}\n"
            )
        )


def test_result_switch_rejects_literal_case() -> None:
    with pytest.raises(TranspileError, match="requires `ok"):
        analyze(
            parse_program(
                "result<int, string> outcome = ok(10)\n"
                "switch (outcome) {\n"
                "    case 10:\n"
                "        print(10)\n"
                "    default:\n"
                "        print(0)\n"
                "}\n"
            )
        )


def test_propagate_runtime_returns_same_error_and_skips_remaining_body(capsys) -> None:
    source = (
        "function result<int, string> mayFail(bool fail) {\n"
        "    if (fail) {\n"
        '        return err("boom")\n'
        "    }\n"
        "    return ok(7)\n"
        "}\n"
        "function result<int, string> addOne(bool fail) {\n"
        "    int value = mayFail(fail) propagate\n"
        '    print("after propagate")\n'
        "    return ok(value + 1)\n"
        "}\n"
        "result<int, string> success = addOne(false)\n"
        "switch (success) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n"
        "result<int, string> failure = addOne(true)\n"
        "switch (failure) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n"
    )

    exec(transpile(source), {})
    assert capsys.readouterr().out.splitlines() == [
        "after propagate",
        "8",
        "boom",
    ]


def test_result_switch_expression_emits_payload_binding(capsys) -> None:
    py = transpile(
        "result<int, string> outcome = ok(42)\n"
        "int answer = switch (outcome) {\n"
        "    case ok(value) => value\n"
        "    case err(error) => 0\n"
        "}\n"
        "print(answer)\n"
    )

    exec(py, {})
    assert capsys.readouterr().out == "42\n"


def test_result_pattern_binding_is_visible_to_find_usages(tmp_path) -> None:
    source = tmp_path / "main.pys"
    source.write_text(
        "result<int, string> outcome = ok(42)\n"
        "switch (outcome) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n",
        encoding="utf-8",
    )
    line = "    case ok(value):"
    hits = find_usages(source, "value", line=3, column=line.index("value") + 1)
    assert {hit["line"] for hit in hits} == {3, 4}


def test_result_typed_lambda_catches_its_own_propagation(capsys) -> None:
    source = (
        "function result<int, string> mayFail(bool fail) {\n"
        "    if (fail) {\n"
        '        return err("lambda failed")\n'
        "    }\n"
        "    return ok(4)\n"
        "}\n"
        "lambda<bool -> result<int, string>> run = fail => {\n"
        "    int value = mayFail(fail) propagate\n"
        "    return ok(value + 1)\n"
        "}\n"
        "result<int, string> outcome = run(true)\n"
        "switch (outcome) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        "        print(error)\n"
        "}\n"
    )

    exec(transpile(source), {})
    assert capsys.readouterr().out == "lambda failed\n"


def test_results_teaching_example_covers_success_handled_error_and_void(
    capsys,
) -> None:
    example = Path(__file__).parents[1] / "examples" / "results.pys"

    exec(transpile(example.read_text(encoding="utf-8")), {})

    assert capsys.readouterr().out.splitlines() == [
        "after propagate",
        "8",
        "invalid count",
        "0",
        "saved",
        "save accepted",
    ]


def test_nested_propagation_records_deterministic_source_sites() -> None:
    source = (
        "function result<int, string> leaf() {\n"
        '    return err("broken")\n'
        "}\n"
        "function result<int, string> middle() {\n"
        "    int value = leaf() propagate\n"
        "    return ok(value)\n"
        "}\n"
        "function result<int, string> outer() {\n"
        "    int value = middle() propagate\n"
        "    return ok(value)\n"
        "}\n"
        "result<int, string> outcome = outer()\n"
    )
    namespace: dict[str, object] = {}

    exec(transpile(source), namespace)

    outcome = namespace["outcome"]
    assert outcome.sites == [
        ("<memory>", 5, "middle"),
        ("<memory>", 9, "outer"),
    ]
