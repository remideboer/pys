from transpiler.transpiler import transpile


def test_transpile_loop_with_braces() -> None:
    source = """loop(int i=0, i<3, i++) {\nprint i\n}\n"""
    expected = """for i in range(0, 3):\n    print(i)\n"""
    assert transpile(source) == expected


def test_transpile_nested_brace_blocks() -> None:
    source = """if (x < 0) {\nprint "negative"\n} else {\nprint "non-negative"\n}\n"""
    expected = """if x < 0:\n    print("negative")\nelse:\n    print("non-negative")\n"""
    assert transpile(source) == expected


def test_transpile_import_from() -> None:
    source = """import Car from example.pys\nprint Car\n"""
    expected = """from example import Car\nprint(Car)\n"""
    assert transpile(source) == expected
