from transpiler.language_spec import LANGUAGE


def test_translate_loop_general() -> None:
    line = "loop(int i=0;i<3;i++)"
    assert LANGUAGE.translate_line(line) == "for i in range(0, 3):"


def test_translate_loop_general_with_trailing_space() -> None:
    line = "loop (int i = 0; i < 5; i++) "
    assert LANGUAGE.translate_line(line) == "for i in range(0, 5):"


def test_translate_import_from() -> None:
    line = "import Car from example.pys"
    assert LANGUAGE.translate_line(line) == "from example import Car"


def test_translate_loop_with_trailing_spaces() -> None:
    line = "loop (int i = 0; i < 5; i++) "
    assert LANGUAGE.translate_line(line) == "for i in range(0, 5):"


def test_translate_string_interpolation() -> None:
    line = 'print "{name} is {age} years old"'
    assert LANGUAGE.translate_line(line) == 'print(f"{name} is {age} years old")'


def test_translate_class_member_access_modifier() -> None:
    line = "public string make"
    assert LANGUAGE.translate_line(line) == "make = ''"

    line2 = "private string model"
    assert LANGUAGE.translate_line(line2) == "model = ''"
