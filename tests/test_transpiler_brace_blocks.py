import pytest

from transpiler.transpiler import TranspileError, transpile


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


def test_transpile_nested_brace_blocks() -> None:
    source = """if (x < 0) {\nprint "negative"\n} else {\nprint "non-negative"\n}\n"""
    expected = """if x < 0:\n    print("negative")\nelse:\n    print("non-negative")\n"""
    assert transpile(source) == expected


def test_transpile_import_from() -> None:
    source = """import Car from example.pys\nprint Car\n"""
    expected = """from example import Car\nprint(Car)\n"""
    assert transpile(source) == expected


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
