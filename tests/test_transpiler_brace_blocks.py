import pytest

from transpiler.transpiler import TranspileError, transpile


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


def test_transpile_class_method_keyword() -> None:
    source = """class Car {
    public method drive() {
        print("driving")
    }
}
"""
    expected = """class Car:
    def drive(self):
        print("driving")
"""
    assert transpile(source) == expected


def test_class_level_function_is_illegal() -> None:
    source = """class Car {
    public function drive() {
        print("driving")
    }
}
"""
    with pytest.raises(TranspileError, match="Class methods must use `method` instead of `function`"):
        transpile(source)


def test_transpile_overloaded_methods() -> None:
    source = """class Car {
    method drive() {
        print("no args")
    }

    method drive(string name) {
        print(name)
    }
}
"""
    transpiled = transpile(source)
    assert "def drive(self, *args):" in transpiled
    assert "def _drive_0(self):" in transpiled
    assert "def _drive_1(self, name):" in transpiled
    assert "self._drive_0()" in transpiled
    assert "self._drive_1(args[0])" in transpiled


def test_comments_do_not_break_brace_indentation() -> None:
    source = """class Car {
    # comment inside class
    public method drive() {
        print("driving")
    }
}
"""
    transpiled = transpile(source)
    assert 'print("driving")' in transpiled
