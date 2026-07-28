import pytest

from transpiler.language_spec import LANGUAGE
from transpiler.transpiler import TranspileError, transpile


def test_translate_loop_general() -> None:
    line = "loop(int i=0, i<3, i++)"
    assert LANGUAGE.translate_line(line) == "for i in range(0, 3):"


def test_translate_loop_condition_is_while() -> None:
    assert LANGUAGE.translate_line("loop(y < 30)") == "while y < 30:"
    assert LANGUAGE.translate_line("loop (y < 30)") == "while y < 30:"


def test_translate_loop_general_with_trailing_space() -> None:
    line = "loop (int i = 0, i < 5, i++) "
    assert LANGUAGE.translate_line(line) == "for i in range(0, 5):"


def test_translate_import_from() -> None:
    line = "import Car from example.pys"
    assert LANGUAGE.translate_line(line) == "from example import Car"


def test_translate_import_all_and_module() -> None:
    assert LANGUAGE.translate_line("import all from funcs.pys") == "from funcs import *"
    assert LANGUAGE.translate_line("import funcs.pys") == "from funcs import *"
    assert LANGUAGE.translate_line("import funcs") == "from funcs import *"


def test_translate_visible_function() -> None:
    assert LANGUAGE.translate_line("global function hello()") == "def hello():"
    assert LANGUAGE.translate_line("package function greet(name)") == "def greet(name):"
    assert LANGUAGE.translate_line("module function secret()") == "def secret():"


def test_translate_const_decl() -> None:
    assert (
        LANGUAGE.translate_line("global const float PI = 3.14159265358979323846")
        == "PI = 3.14159265358979323846"
    )
    assert LANGUAGE.translate_line("const int MAX = 100") == "MAX = 100"
    assert transpile("const int MAX = 10 + 5\nprint(MAX)\n") == "MAX = 10 + 5\nprint(MAX)\n"


def test_translate_loop_with_trailing_spaces() -> None:
    line = "loop (int i = 0, i < 5, i++) "
    assert LANGUAGE.translate_line(line) == "for i in range(0, 5):"


def test_translate_string_interpolation() -> None:
    line = 'print "{name} is {age} years old"'
    assert LANGUAGE.translate_line(line) == 'print(f"{name} is {age} years old")'


def test_print_plus_switches_to_string_concat() -> None:
    assert (
        LANGUAGE.translate_line('print(3.14 + 10 + "addada")')
        == 'print(str(3.14 + 10) + "addada")'
    )
    assert (
        LANGUAGE.translate_line('print(3.14 + 10 + "addada" + 5)')
        == 'print(str(3.14 + 10) + "addada" + str(5))'
    )
    assert (
        LANGUAGE.translate_line('print("addada" + 3.14 + 10)')
        == 'print("addada" + str(3.14) + str(10))'
    )


def test_typed_decl_translates_cast() -> None:
    assert LANGUAGE.translate_line("int a = (int) f") == "a = int(f)"
    assert LANGUAGE.translate_line("int a = (int)f") == "a = int(f)"
    assert transpile("float f = 3.14\nint a = (int) f\nprint(a)\n") == "f = 3.14\na = int(f)\nprint(a)\n"


def test_print_plus_concat_runtime() -> None:
    source = """print(3.14 + 10 + "addada")
print(3.14 + 10 + "addada" + 5)
print("addada" + 3.14 + 10)
"""
    from transpiler.transpiler import transpile

    py = transpile(source)
    assert 'str(3.14 + 10) + "addada"' in py
    namespace: dict = {}
    exec(py, namespace)


def test_translate_string_interpolation_in_print_parens() -> None:
    line = 'print("Hello {name}")'
    assert LANGUAGE.translate_line(line) == 'print(f"Hello {name}")'


def test_rejects_assignment_to_undeclared_variable() -> None:
    source = "int x = 10\ny = 20"
    with pytest.raises(TranspileError, match="Undeclared variable"):
        transpile(source)


def test_translate_class_member_access_modifier() -> None:
    line = "public string make"
    assert LANGUAGE.translate_line(line) == "make = ''"

    line2 = "private string model"
    assert LANGUAGE.translate_line(line2) == "model = ''"


def test_translate_class_inherits() -> None:
    assert LANGUAGE.translate_line("class Truck inherits Car") == "class Truck(Car):"
    assert LANGUAGE.translate_line("class Truck super Car") == "class Truck(Car):"


def test_translate_interface_and_implements() -> None:
    assert LANGUAGE.translate_line("interface Startable") == "class Startable(ABC):"
    assert LANGUAGE.translate_line("class Car implements Startable") == "class Car(Startable):"
    assert (
        LANGUAGE.translate_line("class Truck inherits Car implements Startable")
        == "class Truck(Car, Startable):"
    )


def test_translate_super_call() -> None:
    assert LANGUAGE.translate_line("super(make, model, year)") == "super().__init__(make, model, year)"
    assert LANGUAGE.translate_line("super.drive()") == "super().drive()"
