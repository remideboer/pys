import pytest

from transpiler.language_spec import LANGUAGE
from transpiler.transpiler import Parser, TranspileError, transpile


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


def test_translate_fix_decl() -> None:
    assert LANGUAGE.translate_line("fix int x = sum(4, 5)") == "x = sum(4, 5)"
    assert LANGUAGE.translate_line("global fix int n = 1 + 2") == "n = 1 + 2"
    assert transpile("fix int x = 4 + 5\nprint(x)\n") == "x = 4 + 5\nprint(x)\n"


def test_translate_array_loop() -> None:
    assert LANGUAGE.translate_line("numbers.loop(print)") == "list(map(print, numbers))"


def test_multiline_comment_stripped() -> None:
    source = "int x = 10\n## this is\na multiline\ncomment /#\nprint(x)\n"
    result = transpile(source)
    assert "x = 10" in result
    assert "print(x)" in result
    assert "multiline" not in result


def test_generic_class_transpiles() -> None:
    source = (
        "class Box<T> {\n"
        "    private T value\n"
        "    public Box(T value) {\n"
        "        this.value = value\n"
        "    }\n"
        "    public T get() {\n"
        "        return this.value\n"
        "    }\n"
        "}\n"
    )
    result = transpile(source)
    assert "class Box:" in result
    assert "def get(self):" in result


def test_loop_counter_immutability_rejects_assignment() -> None:
    source = "loop(int i=0, i<5, i++) {\n    i = 3\n}\n"
    with pytest.raises(TranspileError, match="Loop counter 'i' is immutable"):
        transpile(source)


def test_loop_counter_immutability_rejects_increment() -> None:
    source = "loop(int i=0, i<5, i++) {\n    i++\n}\n"
    with pytest.raises(TranspileError, match="Loop counter 'i' is immutable"):
        transpile(source)


def test_loop_counter_allowed_outside_loop() -> None:
    source = "int i = 0\nloop(int i=0, i<5, i++) {\n    print(i)\n}\ni = 10\n"
    transpile(source)


def test_unterminated_multiline_comment() -> None:
    source = "## this never closes\nint x = 10\n"
    with pytest.raises(TranspileError, match="Unterminated multiline comment"):
        transpile(source)


def test_translate_loop_with_trailing_spaces() -> None:
    line = "loop (int i = 0, i < 5, i++) "
    assert LANGUAGE.translate_line(line) == "for i in range(0, 5):"


def test_translate_string_interpolation() -> None:
    line = 'print "{name} is {age} years old"'
    assert LANGUAGE.translate_line(line) == 'print(f"{name} is {age} years old")'


def test_translate_typed_string_interpolation() -> None:
    assert LANGUAGE.translate_line('print "#s{x} is a string"') == 'print(f"{x} is a string")'
    assert LANGUAGE.translate_line('print "#i{y} is an int"') == 'print(f"{y} is an int")'
    assert LANGUAGE.translate_line('print "#f{z} is a float"') == 'print(f"{z} is a float")'
    assert LANGUAGE.translate_line('print "#c{ch} is a char"') == 'print(f"{ch} is a char")'
    assert LANGUAGE.translate_line('print "#b{x} is a bool"') == 'print(f"{x} is a bool")'
    assert LANGUAGE.translate_line('print "#o{car} is an object"') == 'print(f"{car} is an object")'


def test_translate_escape_hash() -> None:
    assert LANGUAGE.translate_line(r'print "\# is a hash"') == 'print(f"# is a hash")'


def test_typed_interpolation_mixed_with_plain() -> None:
    line = 'print "#i{x} plus {y} equals #s{result}"'
    result = LANGUAGE.translate_line(line)
    assert result == 'print(f"{x} plus {y} equals {result}")'


def test_typed_interpolation_rejects_wrong_type() -> None:
    source = 'float f = 3.14\nprint("#i{f} wrong")\n'
    with pytest.raises(TranspileError, match="requires int.*is float"):
        transpile(source)


def test_typed_interpolation_accepts_correct_type() -> None:
    source = 'int x = 10\nprint("#i{x} ok")\n'
    transpile(source)


def test_typed_interpolation_string_rejects_char() -> None:
    source = "char c = 'A'\nprint(\"#s{c} wrong\")\n"
    with pytest.raises(TranspileError, match="requires string.*is char"):
        transpile(source)


def test_true_false_null_translation() -> None:
    assert "True" in transpile("bool b = true\n")
    assert "False" in transpile("bool b = false\n")


def test_typed_interpolation_object_rejects_primitive() -> None:
    source = 'int x = 10\nprint("#o{x} wrong")\n'
    with pytest.raises(TranspileError, match="requires an object.*is int"):
        transpile(source)


def test_typed_interpolation_tuple_index_rejects_wrong_spec() -> None:
    source = (
        "list<tuple<int, string, string>> rows = null\n"
        "loop (tuple<int, string, string> x in rows) {\n"
        '    print("#s{x[0]} wrong")\n'
        "}\n"
    )
    with pytest.raises(TranspileError, match=r"requires string.*'x\[0\]' is int"):
        transpile(source)


def test_typed_interpolation_tuple_index_accepts_correct_spec() -> None:
    source = (
        "list<tuple<int, string, string>> rows = null\n"
        "loop (tuple<int, string, string> x in rows) {\n"
        '    print("#i{x[0]} #s{x[1]} #s{x[2]}")\n'
        "}\n"
    )
    transpile(source)


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


def test_sealed_class_transpiles() -> None:
    assert LANGUAGE.translate_line("sealed class Ship") == "class Ship:"
    assert LANGUAGE.translate_line("package sealed class Ship") == "class Ship:"
    assert (
        LANGUAGE.translate_line("package sealed class Ship inherits Vehicle implements Loadable")
        == "class Ship(Vehicle, Loadable):"
    )


def test_sealed_class_rejects_inheritance() -> None:
    source = "sealed class Foo {\n}\nclass Bar inherits Foo {\n}\n"
    with pytest.raises(TranspileError, match="cannot inherit from sealed class Foo"):
        Parser(source).parse()


def test_inclusive_slice_rewrite() -> None:
    from transpiler.language_spec import _rewrite_inclusive_slices

    assert _rewrite_inclusive_slices("arr[1:5]") == "arr[1:(5) + 1]"
    assert _rewrite_inclusive_slices("arr[3:]") == "arr[3:]"
    assert _rewrite_inclusive_slices("arr[:3]") == "arr[:(3) + 1]"
    assert _rewrite_inclusive_slices("arr[1:6:2]") == "arr[1:(6) + 1:2]"
    assert _rewrite_inclusive_slices("arr[i]") == "arr[i]"
    assert _rewrite_inclusive_slices("print(arr[1:5])") == "print(arr[1:(5) + 1])"


def test_array_slicing_transpiles_and_runs() -> None:
    source = (
        "int[] arr = [1, 2, 3, 4, 5, 6, 7]\n"
        "print(arr[1:5])\n"
        "print(arr[3:])\n"
        "print(arr[:3])\n"
        "print(arr[1:6:2])\n"
    )
    python = transpile(source)
    assert "arr[1:(5) + 1]" in python
    assert "arr[3:]" in python
    assert "arr[:(3) + 1]" in python
    assert "arr[1:(6) + 1:2]" in python
    ns: dict = {}
    exec(python, ns)  # noqa: S102 — test harness
