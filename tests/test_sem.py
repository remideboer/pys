"""Semantic analyzer checks that own errors without relying on legacy emit."""
from __future__ import annotations

import pytest

from transpiler.parse import parse_program
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError, transpile


def _analyze(source: str):
    return analyze(parse_program(source))


def test_sem_typed_interpolation_rejects_wrong_int_spec() -> None:
    with pytest.raises(TranspileError, match="requires int.*is float"):
        _analyze('float f = 3.14\nprint("#i{f} wrong")\n')


def test_sem_typed_interpolation_accepts_correct_spec() -> None:
    _analyze('int x = 10\nprint("#i{x} ok")\n')


def test_sem_typed_interpolation_string_rejects_char() -> None:
    with pytest.raises(TranspileError, match="requires string.*is char"):
        _analyze("char c = 'A'\nprint(\"#s{c} wrong\")\n")


def test_sem_typed_interpolation_object_rejects_primitive() -> None:
    with pytest.raises(TranspileError, match="requires an object.*is int"):
        _analyze('int x = 10\nprint("#o{x} wrong")\n')


def test_sem_typed_interpolation_bool_and_float_specs() -> None:
    _analyze('bool b = true\nprint("#b{b} ok")\n')
    _analyze('float f = 1.5\nprint("#f{f} ok")\n')
    with pytest.raises(TranspileError, match="requires bool.*is int"):
        _analyze('int x = 1\nprint("#b{x} wrong")\n')
    with pytest.raises(TranspileError, match="requires float.*is int"):
        _analyze('int x = 1\nprint("#f{x} wrong")\n')


def test_sem_typed_interpolation_indexed_array_element() -> None:
    _analyze('int[] xs = [1, 2]\nprint("#i{xs[0]} ok")\n')
    with pytest.raises(TranspileError, match="requires string.*is int"):
        _analyze('int[] xs = [1, 2]\nprint("#s{xs[0]} wrong")\n')


def test_pipeline_typed_interpolation_still_errors() -> None:
    with pytest.raises(TranspileError, match="requires int.*is float"):
        transpile('float f = 3.14\nprint("#i{f} wrong")\n')


def test_sem_private_field_access_denied_outside_class() -> None:
    source = """class Car {
    private string make

    public Car(string make) {
        this.make = make
    }
}

Car car = Car("Toyota")
car.make = "Honda"
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'make' is private"):
        _analyze(source)


def test_sem_private_field_allowed_inside_defining_class() -> None:
    source = """class Car {
    private string make

    public Car(string make) {
        this.make = make
    }

    public string getMake() {
        return this.make
    }
}
"""
    _analyze(source)


def test_sem_private_field_denied_in_subclass() -> None:
    source = """class Car {
    private string make

    public Car(string make) {
        this.make = make
    }
}

class Truck inherits Car {
    public string read() {
        return this.make
    }
}
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'make' is private"):
        _analyze(source)


def test_sem_protected_field_allowed_in_subclass() -> None:
    source = """class Car {
    protected string make

    public Car(string make) {
        this.make = make
    }
}

class Truck inherits Car {
    public string read() {
        return this.make
    }
}
"""
    _analyze(source)


def test_sem_sealed_class_rejects_inheritance() -> None:
    with pytest.raises(TranspileError, match="cannot inherit from sealed class Foo"):
        _analyze("sealed class Foo {\n}\nclass Bar inherits Foo {\n}\n")


def test_sem_missing_interface_method() -> None:
    source = """interface Startable {
    public start()
}

class Car implements Startable {
    public Car() {
        pass
    }
}
"""
    with pytest.raises(TranspileError, match=r"must implement abstract method 'start'"):
        _analyze(source)


def test_sem_interface_arity_mismatch() -> None:
    source = """interface Startable {
    public start(string name)
}

class Car implements Startable {
    public start() {
        print("starting")
    }
}
"""
    with pytest.raises(TranspileError, match=r"does not match interface"):
        _analyze(source)


def test_sem_interface_method_body_rejected() -> None:
    source = """interface Startable {
    public start() {
        print("nope")
    }
}
"""
    with pytest.raises(TranspileError, match=r"abstract and cannot have a body"):
        parse_program(source)


def test_sem_shared_capture_mutation_rejected() -> None:
    source = """
int local = 1
tasks {
    task {
        local = 2
    }
}
"""
    with pytest.raises(TranspileError, match="shared"):
        _analyze(source)


def test_sem_shared_mutation_allowed() -> None:
    source = """
shared int counter = 0
tasks {
    task {
        counter = counter + 1
    }
}
"""
    _analyze(source)


def test_sem_array_rejects_mixed_types() -> None:
    with pytest.raises(TranspileError, match="Int array elements must be integers"):
        _analyze("int[] nums = [1, 2.5, 3]\n")


def test_sem_array_rejects_overflow() -> None:
    with pytest.raises(TranspileError, match="Array index out of bounds"):
        _analyze("int[4] nums = [2, 3, 5, 8, 9]\n")


def test_sem_array_accepts_exact_size() -> None:
    _analyze("int[4] nums = [2, 3, 5, 8]\n")


def test_sem_class_requires_access_modifier() -> None:
    with pytest.raises(TranspileError, match="access modifier"):
        _analyze("class Car {\n    int year\n}\n")


def test_sem_class_rejects_function_keyword() -> None:
    source = """class Car {
    public function drive() {
        print("driving")
    }
}
"""
    with pytest.raises(TranspileError, match="Class methods must not use `function`"):
        parse_program(source)


def test_sem_class_rejects_method_keyword() -> None:
    source = """class Car {
    public method drive() {
        print("driving")
    }
}
"""
    with pytest.raises(TranspileError, match="Remove `method`"):
        parse_program(source)


def test_fixture_pys_files_parse_on_ast() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "tests"
    legacy = []
    for path in root.rglob("*.pys"):
        module = parse_program(path.read_text(encoding="utf-8"))
        if module.use_legacy:
            legacy.append(str(path.relative_to(root)))
    assert legacy == [], f"fixtures still on use_legacy: {legacy}"


def test_emit_python_parser_only_in_legacy_helper() -> None:
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "transpiler" / "emit" / "python.py").read_text(
        encoding="utf-8"
    )
    # Guard: production AST emit must not construct Parser outside _legacy_emit.
    assert "from ..transpiler import Parser" in text
    assert text.count("from ..transpiler import Parser") == 1
    legacy_idx = text.index("def _legacy_emit")
    import_idx = text.index("from ..transpiler import Parser")
    assert import_idx > legacy_idx


def test_examples_main_pys_compiles_on_ast() -> None:
    from pathlib import Path

    from transpiler.pipeline import compile_pys

    path = Path(__file__).resolve().parents[1] / "examples" / "main.pys"
    source = path.read_text(encoding="utf-8")
    assert parse_program(source).use_legacy is False
    out = compile_pys(source, source_path=path)
    assert "def " in out or "class " in out
