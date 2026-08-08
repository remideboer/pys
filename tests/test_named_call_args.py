"""Named call arguments for functions, methods, and class constructors.

BDD:
- Given all-positional or all-named args, When calling a known callable,
  Then types bind by position or by parameter name.
- Given any mix of positional and named in one call (including struct ctors),
  Then analysis rejects the call.
"""

from __future__ import annotations

import pytest

from transpiler.transpiler import TranspileError, transpile


def test_function_all_named_args_bind_by_name() -> None:
    """Scenario: function call with only named arguments."""
    py = transpile(
        "function void greet(string name, int times) {\n"
        "    print(name)\n"
        "}\n"
        'greet(times=2, name="Ada")\n'
    )
    assert 'greet(times=2, name="Ada")' in py or 'greet(name="Ada", times=2)' in py


def test_function_rejects_mixed_positional_and_named() -> None:
    """Scenario: mix is illegal in any call."""
    with pytest.raises(TranspileError, match=r"mix|positional.*named|named.*positional"):
        transpile(
            "function void greet(string name, int times) {\n"
            "    print(name)\n"
            "}\n"
            'greet("Ada", times=2)\n'
        )


def test_function_rejects_unknown_named_argument() -> None:
    with pytest.raises(TranspileError, match=r"Unknown named argument|unknown argument"):
        transpile(
            "function void greet(string name) {\n"
            "    print(name)\n"
            "}\n"
            'greet(who="Ada")\n'
        )


def test_function_rejects_duplicate_named_argument() -> None:
    with pytest.raises(TranspileError, match=r"[Dd]uplicate"):
        transpile(
            "function void greet(string name) {\n"
            "    print(name)\n"
            "}\n"
            'greet(name="Ada", name="Bob")\n'
        )


def test_function_named_argument_type_mismatch() -> None:
    with pytest.raises(TranspileError, match=r"type|expected"):
        transpile(
            "function void greet(string name) {\n"
            "    print(name)\n"
            "}\n"
            "greet(name=1)\n"
        )


def test_method_all_named_args() -> None:
    py = transpile(
        "class Greeter {\n"
        "    public void greet(string name) {\n"
        "        print(name)\n"
        "    }\n"
        "}\n"
        "Greeter g = Greeter()\n"
        'g.greet(name="Ada")\n'
    )
    assert 'greet(name="Ada")' in py


def test_method_rejects_mixed_args() -> None:
    with pytest.raises(TranspileError, match=r"mix|positional.*named|named.*positional"):
        transpile(
            "class Greeter {\n"
            "    public void greet(string name, int n) {\n"
            "        print(name)\n"
            "    }\n"
            "}\n"
            "Greeter g = Greeter()\n"
            'g.greet("Ada", n=1)\n'
        )


def test_class_constructor_named_args() -> None:
    py = transpile(
        "class Person {\n"
        "    private string name\n"
        "    public constructor(string name) {\n"
        "        this.name = name\n"
        "    }\n"
        "    public string getName() { return this.name }\n"
        "}\n"
        'Person p = Person(name="Ada")\n'
        "print(p.getName())\n"
    )
    assert 'Person(name="Ada")' in py


def test_class_constructor_rejects_mixed_args() -> None:
    with pytest.raises(TranspileError, match=r"mix|positional.*named|named.*positional"):
        transpile(
            "class Person {\n"
            "    private string name\n"
            "    private int age\n"
            "    public constructor(string name, int age) {\n"
            "        this.name = name\n"
            "        this.age = age\n"
            "    }\n"
            "}\n"
            'Person p = Person("Ada", age=1)\n'
        )


def test_generic_class_constructor_accepts_concrete_args() -> None:
    """Call-site type args are erased; unbound T must not reject Car."""
    py = transpile(
        "class Car {\n"
        "    public constructor() {}\n"
        "}\n"
        "class Pair<T, U> {\n"
        "    private T first\n"
        "    private U second\n"
        "    public constructor(T first, U second) {\n"
        "        this.first = first\n"
        "        this.second = second\n"
        "    }\n"
        "}\n"
        "Car a = Car()\n"
        "Car b = Car()\n"
        "Pair<Car, Car> pair = Pair<Car, Car>(a, b)\n"
    )
    assert "Pair" in py


def test_generic_class_constructor_named_args() -> None:
    py = transpile(
        "class Car {\n"
        "    public constructor() {}\n"
        "}\n"
        "class Pair<T, U> {\n"
        "    private T first\n"
        "    private U second\n"
        "    public constructor(T first, U second) {\n"
        "        this.first = first\n"
        "        this.second = second\n"
        "    }\n"
        "}\n"
        "Car a = Car()\n"
        "Car b = Car()\n"
        "Pair<Car, Car> pair = Pair<Car, Car>(second=b, first=a)\n"
    )
    assert "Pair" in py


def test_struct_rejects_mixed_positional_and_named() -> None:
    """Structs used to allow positional-then-named; mix is now illegal everywhere."""
    with pytest.raises(TranspileError, match=r"mix|positional.*named|named.*positional"):
        transpile(
            "struct Point {\n"
            "    int x\n"
            "    int y = 0\n"
            "}\n"
            "Point p = Point(1, y=2)\n"
        )


def test_struct_all_named_still_ok() -> None:
    py = transpile(
        "struct Point {\n"
        "    int x\n"
        "    int y\n"
        "}\n"
        "Point p = Point(y=2, x=1)\n"
    )
    assert "Point(" in py
