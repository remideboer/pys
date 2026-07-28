import pytest

from transpiler.transpiler import TranspileError, transpile


def test_transpile_error_message_includes_line_number() -> None:
    source = """let x 1
print hello
"""
    with pytest.raises(TranspileError, match=r"line 1"):
        transpile(source)
