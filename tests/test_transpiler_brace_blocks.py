import sys
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile, transpile_with_modules


def test_transpile_loop_with_braces() -> None:
    source = """loop(int i=0; i<3; i++) {\nprint i\n}\n"""
    py = transpile(source)
    assert "for i in range(0, 3):" not in py
    assert "for _pys_b" in py and " in range(0, 3):" in py
    assert "print(_pys_format(_pys_b" in py


def test_transpile_while_style_loop() -> None:
    source = """int y = 20
loop (y < 30) {
    print(y)
    y++
}
"""
    expected = """def _pys_format(value):
    return "null" if value is None else str(value)
y = 20
while y < 30:
    print(_pys_format(y))
    y += 1
"""
    assert transpile(source) == expected


def test_polymorphic_assignment_and_dispatch() -> None:
    source = """interface Startable {
    start()
}

class Car implements Startable {
    public constructor() {
        pass
    }
    public start() {
        print("car-start")
    }
    public open drive() {
        print("car-drive")
    }
}

class Truck inherits Car {
    public constructor() {
        pass
    }
    public override drive() {
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
    public constructor() {
        pass
    }
}
class Other {
    public constructor() {
        pass
    }
}
Car c = Other()
"""
    with pytest.raises(TranspileError, match=r"cannot assign Other to 'c' of type Car"):
        transpile(source)


def test_declared_type_hides_subtype_only_members() -> None:
    source = """class Car {
    public constructor() {
        pass
    }
    public drive() {
        print("car")
    }
}
class Truck inherits Car {
    private int loadCapacity
    public constructor() {
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
    public constructor() {
        pass
    }
}
class Truck inherits Car {
    public constructor() {
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
    start()
}

class Car implements Startable {
    public constructor() {
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
    start()
}

class Car implements Startable {
    public constructor() {
        pass
    }
}
"""
    with pytest.raises(TranspileError, match=r"must implement abstract method 'start'"):
        transpile(source)


def test_interface_method_body_is_rejected() -> None:
    source = """interface Startable {
    start() {
        print("nope")
    }
}
"""
    with pytest.raises(TranspileError, match=r"abstract and cannot have a body"):
        transpile(source)


def test_interface_arity_mismatch_is_rejected() -> None:
    source = """interface Startable {
    start(string name)
}

class Car implements Startable {
    public start() {
        print("starting")
    }
}
"""
    with pytest.raises(TranspileError, match=r"does not match interface"):
        transpile(source)


def test_interface_access_modifier_is_rejected() -> None:
    source = """interface Startable {
    private start()
}
"""
    with pytest.raises(TranspileError, match=r"always public|omit `private`"):
        transpile(source)


def test_transpile_nested_brace_blocks() -> None:
    source = """if (x < 0) {\nprint "negative"\n} else {\nprint "non-negative"\n}\n"""
    expected = (
        'def _pys_format(value):\n'
        '    return "null" if value is None else str(value)\n'
        'if x < 0:\n'
        '    print(_pys_format("negative"))\n'
        'else:\n'
        '    print(_pys_format("non-negative"))\n'
    )
    assert transpile(source) == expected


def test_transpile_import_from() -> None:
    source = """import Car from example.pys\nprint Car\n"""
    expected = (
        'def _pys_format(value):\n'
        '    return "null" if value is None else str(value)\n'
        'from example import Car\n'
        'print(_pys_format(Car))\n'
    )
    assert transpile(source) == expected


def test_transpile_multi_name_import_from(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    site = tmp_path / "site"
    pkg = site / "PyQt6"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "QtWidgets.pyd").write_bytes(b"")
    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [site],
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import QApplication, QWidget from PyQt6.QtWidgets\nprint(QApplication)\n",
        encoding="utf-8",
    )
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "from PyQt6.QtWidgets import QApplication, QWidget" in python


def test_subclass_can_call_library_parent_methods(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "site"
    pkg = site / "PyQt6"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "QtWidgets.py").write_text(
        "class QMainWindow:\n"
        "    def setWindowTitle(self, title):\n"
        "        pass\n"
        "    def setCentralWidget(self, widget):\n"
        "        pass\n"
        "    def show(self):\n"
        "        pass\n"
        "class QPushButton:\n"
        "    def __init__(self, text=''):\n"
        "        self.text = text\n",
        encoding="utf-8",
    )
    # Drop any real/partial PyQt6 cached by earlier tests (acceptance on CI).
    for key in list(sys.modules):
        if key == "PyQt6" or key.startswith("PyQt6."):
            del sys.modules[key]
    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [site],
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import QMainWindow, QPushButton from PyQt6.QtWidgets\n"
        "package class MainWindow inherits QMainWindow {\n"
        "    public constructor() {\n"
        "        this.setWindowTitle(\"My App\")\n"
        "        QPushButton button = QPushButton(\"Press Me!\")\n"
        "        this.setCentralWidget(button)\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "class MainWindow(QMainWindow):" in python
    assert "self.setWindowTitle(\"My App\")" in python
    assert "self.setCentralWidget(button)" in python
    assert "super().__init__()" in python


def test_subclass_rejects_unknown_library_parent_method(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = tmp_path / "site"
    pkg = site / "PyQt6"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "QtWidgets.py").write_text(
        "class QMainWindow:\n"
        "    def setWindowTitle(self, title):\n"
        "        pass\n",
        encoding="utf-8",
    )
    for key in list(sys.modules):
        if key == "PyQt6" or key.startswith("PyQt6."):
            del sys.modules[key]
    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [site],
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import QMainWindow from PyQt6.QtWidgets\n"
        "package class MainWindow inherits QMainWindow {\n"
        "    public constructor() {\n"
        "        this.notARealQtMethod()\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError, match=r"not a member of declared type MainWindow"):
        transpile(
            main.read_text(encoding="utf-8"),
            source_path=main,
            allow_runtime_introspection=True,
        )


def test_subclass_allows_library_parent_when_module_unloadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CI often has PyQt wheel files present but QtWidgets fails to import."""
    site = tmp_path / "site"
    pkg = site / "PyQt6"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "QtWidgets.py").write_text("raise ImportError('qt libs missing')\n", encoding="utf-8")
    for key in list(sys.modules):
        if key == "PyQt6" or key.startswith("PyQt6."):
            del sys.modules[key]
    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [site],
    )
    main = tmp_path / "main.pys"
    main.write_text(
        "import QMainWindow from PyQt6.QtWidgets\n"
        "package class MainWindow inherits QMainWindow {\n"
        "    public constructor() {\n"
        "        this.setWindowTitle(\"My App\")\n"
        "        this.show()\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "self.setWindowTitle" in python
    assert "self.show()" in python


def test_library_type_member_via_package_import(tmp_path: Path) -> None:
    """``Frame`` via ``import tkinter.ttk as ttk`` must allow ``.pack`` (hasattr)."""
    main = tmp_path / "main.pys"
    main.write_text(
        "import tkinter.ttk as ttk\n"
        "function build(){\n"
        "    Frame panel = ttk.Frame()\n"
        "    panel.pack()\n"
        "}\n",
        encoding="utf-8",
    )
    python = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "panel.pack()" in python


def test_library_type_rejects_absent_member_via_package_import(tmp_path: Path) -> None:
    main = tmp_path / "main.pys"
    main.write_text(
        "import tkinter.ttk as ttk\n"
        "function build(){\n"
        "    Frame panel = ttk.Frame()\n"
        "    panel.notARealTkMethod()\n"
        "}\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError, match=r"'notARealTkMethod' is not a member of declared type Frame"):
        transpile(main.read_text(encoding="utf-8"), source_path=main)


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


def test_const_rejects_reassignment() -> None:
    source = """const int MAX = 10
MAX = 20
"""
    with pytest.raises(TranspileError, match="Cannot assign to const 'MAX'"):
        transpile(source)


def test_fix_allows_runtime_initializer() -> None:
    source = """int a = 4
int b = 5
fix int x = a + b
print(x)
"""
    assert "x = a + b" in transpile(source)


def test_fix_rejects_reassignment() -> None:
    source = """fix int x = 9
x = 10
"""
    with pytest.raises(TranspileError, match="Cannot assign to fix 'x'"):
        transpile(source)


def test_fix_rejects_increment() -> None:
    source = """fix int x = 9
x++
"""
    with pytest.raises(TranspileError, match="Cannot modify fix 'x'"):
        transpile(source)


def test_const_requires_compile_time_initializer() -> None:
    source = """int x = 10
const int Y = x
"""
    with pytest.raises(TranspileError, match="compile-time constant"):
        transpile(source)


def test_global_const_is_importable(tmp_path: Path) -> None:
    (tmp_path / "mathy.pys").write_text(
        "global const float PI = 3.14159265358979323846\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import mathy\nprint(PI)\n", encoding="utf-8")
    py = transpile(main.read_text(encoding="utf-8"), source_path=main)
    assert "from mathy import PI" in py
    with pytest.raises(TranspileError, match="Cannot assign to const 'PI'"):
        transpile("import mathy\nPI = 1\n", source_path=main)


def test_typed_arrays_use_stdlib_array() -> None:
    source = """int[] numbers = [1, 2, 3, 4, 5]
float[] floats = [1.1, 2.2, 3.3]
bool[] bools = [true, false, true]
string[] names = ["John", "Jane"]
"""
    py = transpile(source)
    assert "from array import array" in py
    assert "numbers = array('i', [1, 2, 3, 4, 5])" in py
    assert "floats = array('d', [1.1, 2.2, 3.3])" in py
    assert "bools = array('b', [1, 0, 1])" in py
    assert 'names = ["John", "Jane"]' in py


def test_sized_array_decl_rejected() -> None:
    source = "int[4] nums = [2, 3, 5, 8]\n"
    with pytest.raises(TranspileError, match="Sized array type|not valid on a declaration"):
        transpile(source)


def test_unsized_array_length_from_initializer() -> None:
    assert transpile("int[] nums = [2, 3, 5, 8]\n") == (
        "from array import array\nnums = array('i', [2, 3, 5, 8])\n"
    )


def test_array_rejects_mixed_types() -> None:
    with pytest.raises(TranspileError, match="Int array elements must be integers"):
        transpile("int[] nums = [1, 2.5, 3]\n")


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
    expected = """def _pys_format(value):
    return "null" if value is None else str(value)
class Car:
    def drive(self):
        print(_pys_format("driving"))

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
    assert 'print(_pys_format("driving"))' in transpiled


def test_private_field_access_denied_outside_class() -> None:
    source = """class Car {
    private string make

    public constructor(string make) {
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

    public constructor(string make) {
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


def test_subclass_constructor_injects_implicit_super() -> None:
    source = """class Car {
    public constructor() {
        pass
    }
}
class Truck inherits Car {
    public constructor() {
        pass
    }
}
"""
    transpiled = transpile(source)
    truck_init = transpiled.split("class Truck")[1]
    assert "super().__init__()" in truck_init
    # Base class with no parent must not get a synthetic super call.
    car_init = transpiled.split("class Car")[1].split("class Truck")[0]
    assert "super().__init__()" not in car_init


def test_subclass_constructor_keeps_explicit_super() -> None:
    source = """class Car {
    public constructor(string make) {
        pass
    }
}
class Truck inherits Car {
    public constructor(string make) {
        super(make)
    }
}
"""
    transpiled = transpile(source)
    truck_init = transpiled.split("class Truck")[1]
    assert truck_init.count("super().__init__") == 1
    assert "super().__init__(make)" in truck_init


def test_private_field_denied_in_subclass() -> None:
    source = """class Car {
    private string make

    public constructor(string make) {
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

    public constructor(string make) {
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

    public constructor(string make) {
        this.make = make
    }
}

Car car = Car("Toyota")
car.make = "Honda"
print(car.make)
"""
    transpiled = transpile(source)
    assert 'car.make = "Honda"' in transpiled
