from pathlib import Path

from transpiler.transpiler import transpile


def test_transpile_repeat_syntax() -> None:
    source = """repeat 3 times:
    print hello
"""
    expected = """for _ in range(3):
    print(hello)
"""
    assert transpile(source) == expected
