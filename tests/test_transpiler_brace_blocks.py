import pytest
from pathlib import Path

from transpiler.transpiler import TranspileError, transpile, transpile_with_modules


def test_transpile_loop_with_braces() -> None:
    source = """loop(int i=0, i<3, i++) {\nprint i\n}\n"""
    expected = """for i in range(0, 3):\n    print(i)\n"""
    assert transpile(source) == expected


def test_transpile_while_style_loop() -> None:
    source = """int y = 20
loop (y < 30) {
    print(y)
    y++
}
"""
    expected = """y = 20
while y < 30:
    print(y)
    y += 1
"""
    assert transpile(source) == expected


def test_polymorphic_assignment_and_dispatch() -> None:
    source = """interface Startable {
    public start()
}

class Car implements Startable {
    public Car() {
        pass
    }
    public start() {
        print("car-start")
    }
    public drive() {
        print("car-drive")
    }
}

class Truck inherits Car {
    public Truck() {
        pass
    }
    public drive() {
        print("truck-drive")
    }
}

Startable s = Car()
s.start()
Car c = Truck()
c.drive()
"""
    transpiled = transpile(source)
    assert "s = Car()" in transpiled
    assert "c = Truck()" in transpiled
    assert "s.start()" in transpiled
    assert "c.drive()" in transpiled


def test_incompatible_object_assignment_rejected() -> None:
    source = """class Car {
    public Car() {
        pass
    }
}
class Other {
    public Other() {
        pass
    }
}
Car c = Other()
"""
    with pytest.raises(TranspileError, match=r"cannot assign Other to 'c' of type Car"):
        transpile(source)


def test_declared_type_hides_subtype_only_members() -> None:
    source = """class Car {
    public Car() {
        pass
    }
    public drive() {
        print("car")
    }
}
class Truck inherits Car {
    private int loadCapacity
    public Truck() {
        pass
    }
    public haul() {
        print("haul")
    }
}
Car c = Truck()
c.haul()
"""
    with pytest.raises(TranspileError, match=r"'haul' is not a member of declared type Car"):
        transpile(source)


def test_reference_cast_enables_subtype_members() -> None:
    source = """class Car {
    public Car() {
        pass
    }
}
class Truck inherits Car {
    public Truck() {
        pass
    }
    public haul() {
        print("haul")
    }
}
Car c = Truck()
Truck t = (Truck) c
t.haul()
"""
    transpiled = transpile(source)
    assert "t = c" in transpiled
    assert "t.haul()" in transpiled


def test_transpile_interface_and_implements() -> None:
    source = """interface Startable {
    public start()
}

class Car implements Startable {
    public Car() {
        pass
    }

    public start() {
        print("starting")
    }
}
"""
    transpiled = transpile(source)
    assert "from abc import ABC, abstractmethod" in transpiled
    assert "class Startable(ABC):" in transpiled
    assert "@abstractmethod" in transpiled
    assert "def start(self):" in transpiled
    assert "class Car(Startable):" in transpiled


def test_missing_interface_method_is_rejected() -> None:
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
        transpile(source)


def test_interface_method_body_is_rejected() -> None:
    source = """interface Startable {
    public start() {
        print("nope")
    }
}
"""
    with pytest.raises(TranspileError, match=r"abstract and cannot have a body"):
        transpile(source)


def test_interface_arity_mismatch_is_rejected() -> None:
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
        transpile(source)


def test_transpile_nested_brace_blocks() -> None:
    source = """if (x < 0) {\nprint "negative"\n} else {\nprint "non-negative"\n}\n"""
    expected = """if x < 0:\n    print("negative")\nelse:\n    print("non-negative")\n"""
    assert transpile(source) == expected


def test_transpile_import_from() -> None:
    source = """import Car from example.pys\nprint Car\n"""
    expected = """from example import Car\nprint(Car)\n"""
    assert transpile(source) == expected


def test_import_all_resolves_visible_exports(tmp_path: Path) -> None:
    (tmp_path / "funcs.pys").write_text(
        "package function greet(name){\n"
        "    print(name)\n"
        "}\n"
        "\n"
        "global function hello(){\n"
        "    print(\"hi\")\n"
        "}\n"
        "\n"
        "function secret(){\n"
        "    print(\"no\")\n"
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import all from funcs.pys\ngreet(\"student\")\nhello()\n", encoding="utf-8")
    modules = transpile_with_modules(main)
    assert modules["main"].startswith("from funcs import greet, hello\n")
    assert "def greet(name):" in modules["funcs"]
    assert "def secret():" in modules["funcs"]
    assert "secret" not in modules["main"]


def test_import_module_same_as_import_all(tmp_path: Path) -> None:
    (tmp_path / "funcs.pys").write_text(
        "package function greet(name){\n    print(name)\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import funcs\ngreet(\"x\")\n", encoding="utf-8")
    assert transpile(main.read_text(encoding="utf-8"), source_path=main) == (
        "from funcs import greet\ngreet(\"x\")\n"
    )


def test_import_rejects_module_private(tmp_path: Path) -> None:
    (tmp_path / "funcs.pys").write_text(
        "function secret(){\n    print(\"no\")\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import secret from funcs.pys\n", encoding="utf-8")
    with pytest.raises(TranspileError, match="module-scoped"):
        transpile(main.read_text(encoding="utf-8"), source_path=main)


def test_package_export_not_visible_from_other_folder(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    other = tmp_path / "other"
    pkg.mkdir()
    other.mkdir()
    (pkg / "funcs.pys").write_text(
        "package function greet(name){\n    print(name)\n}\n"
        "global function hello(){\n    print(\"hi\")\n}\n",
        encoding="utf-8",
    )
    main = other / "main.pys"
    main.write_text("import all from ../pkg/funcs.pys\n", encoding="utf-8")
    py = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert py == "from funcs import hello\n"


def test_call_to_module_private_seen_name_is_access_error(tmp_path: Path) -> None:
    (tmp_path / "funcs.pys").write_text(
        "global function hello(){\n    print(\"hi\")\n}\n"
        "function doei(){\n    print(\"bye\")\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import funcs\nhello()\ndoei()\n", encoding="utf-8")
    with pytest.raises(TranspileError, match="Access denied: 'doei'.*not accessible"):
        transpile(main.read_text(encoding="utf-8"), source_path=main)


def test_call_to_visible_but_not_imported_name(tmp_path: Path) -> None:
    (tmp_path / "funcs.pys").write_text(
        "global function hello(){\n    print(\"hi\")\n}\n"
        "package function greet(name){\n    print(name)\n}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import hello from funcs.pys\ngreet(\"x\")\n", encoding="utf-8")
    with pytest.raises(TranspileError, match="was not imported"):
        transpile(main.read_text(encoding="utf-8"), source_path=main)


def test_transpile_class_method() -> None:
    source = """class Car {
    public drive() {
        print("driving")
    }

    public string name() {
        return "car"
    }
}
"""
    expected = """class Car:
    def drive(self):
        print("driving")

    def name(self):
        return "car"
"""
    assert transpile(source) == expected


def test_class_level_function_is_illegal() -> None:
    source = """class Car {
    public function drive() {
        print("driving")
    }
}
"""
    with pytest.raises(TranspileError, match="Class methods must not use `function`"):
        transpile(source)


def test_class_method_keyword_is_illegal() -> None:
    source = """class Car {
    public method drive() {
        print("driving")
    }
}
"""
    with pytest.raises(TranspileError, match="Remove `method`"):
        transpile(source)


def test_class_members_require_access_modifier() -> None:
    source = """class Car {
    int year
}
"""
    with pytest.raises(TranspileError, match="access modifier"):
        transpile(source)

    source_method = """class Car {
    drive() {
        print("driving")
    }
}
"""
    with pytest.raises(TranspileError, match="access modifier"):
        transpile(source_method)


def test_transpile_overloaded_methods() -> None:
    source = """class Car {
    public drive() {
        print("no args")
    }

    public drive(string name) {
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
    public drive() {
        print("driving")
    }
}
"""
    transpiled = transpile(source)
    assert 'print("driving")' in transpiled


def test_private_field_access_denied_outside_class() -> None:
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
        transpile(source)


def test_private_field_allowed_inside_defining_class() -> None:
    source = """class Car {
    private string make

    public Car(string make) {
        this.make = make
    }

    public string getMake() {
        return this.make
    }
}

Car car = Car("Toyota")
print(car.getMake())
"""
    transpiled = transpile(source)
    assert "self.make = make" in transpiled
    assert "return self.make" in transpiled


def test_private_field_denied_in_subclass() -> None:
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
        transpile(source)


def test_protected_field_allowed_in_subclass_not_outside() -> None:
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

Car car = Car("Toyota")
car.make = "Honda"
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'make' is protected"):
        transpile(source)


def test_module_field_allowed_in_same_file() -> None:
    source = """class Car {
    module string make

    public Car(string make) {
        this.make = make
    }
}

Car car = Car("Toyota")
car.make = "Honda"
print(car.make)
"""
    transpiled = transpile(source)
    assert 'car.make = "Honda"' in transpiled
