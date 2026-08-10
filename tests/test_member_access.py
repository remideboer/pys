"""Member visibility: negative + positive regressions across use sites.

Bug class: private/protected checks that only cover bare assigns miss other
use sites (interpolation, reads, call args, indented top-level after `}`).
DoD requires these rejection paths stay covered — see CER-052.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.parse import parse_program
from transpiler.pipeline import compile_pys
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError

_REPO = Path(__file__).resolve().parents[1]
_REKEN = _REPO / "requirements" / "rekenmachine.pys"

_REKENMACHINE_CLASS = """\
class Rekenmachine {
    private fix int getalA
    private fix int getalB

    public constructor(int a, int b) {
        this.getalA = a
        this.getalB = b
    }

    public int som() {
        return this.getalA + this.getalB
    }

    public int vermenigvuldigd() {
        return this.getalA * this.getalB
    }

    private int geheim() {
        return this.getalA
    }
}
"""


def _analyze(source: str):
    return analyze(parse_program(source))


def _deny(source: str, member: str, access: str = "private") -> None:
    with pytest.raises(
        TranspileError,
        match=rf"Access denied: '{member}' is {access} in class Rekenmachine",
    ):
        _analyze(source)


# --- Given/When/Then: Rekenmachine teaching sample (requirements/rekenmachine.pys) ---


def test_rekenmachine_fixture_compiles_without_external_private_use() -> None:
    """Given the requirements sample as written, When transpile, Then OK."""
    assert _REKEN.is_file(), "requirements/rekenmachine.pys missing"
    compile_pys(_REKEN.read_text(encoding="utf-8"))


def test_rekenmachine_fixture_external_print_is_access_denied() -> None:
    """Given print(rm.getalA) uncommented, When analyze, Then Access denied."""
    src = _REKEN.read_text(encoding="utf-8").replace("# print(rm.getalA)", "print(rm.getalA)")
    _deny(src, "getalA")


@pytest.mark.parametrize(
    ("commented", "member"),
    [
        ("# print(rm.getalA)", "getalA"),
        ("# int leaked = rm.getalB", "getalB"),
        ("# rm.getalA = 99", "getalA"),
        (
            '# print("De som van {rm.getalA} en {rm.getalB} is: {rm.som()}")',
            "getalA",
        ),
    ],
    ids=["print_read", "typed_decl", "assign", "interpolation"],
)
def test_rekenmachine_fixture_negative_lines_denied(commented: str, member: str) -> None:
    """Uncomment each documented NEGATIVE line from requirements/rekenmachine.pys."""
    raw = _REKEN.read_text(encoding="utf-8")
    assert commented in raw, f"fixture missing documented negative: {commented}"
    assert commented.startswith("# ")
    src = raw.replace(commented, commented[2:], 1)
    _deny(src, member)

def test_rekenmachine_indented_toplevel_private_read_still_denied() -> None:
    """Top-level after `}` must stay at column 1; access checks still apply there."""
    source = _REKENMACHINE_CLASS + """
Rekenmachine rm = Rekenmachine(4, 5)
print(rm.getalA)
"""
    _deny(source, "getalA")


# --- Negative matrix: private field outside defining class ---


@pytest.mark.parametrize(
    "snippet",
    [
        'print(rm.getalA)',
        'int x = rm.getalA',
        'rm.getalA = 99',
        'print("sum={rm.getalA}")',
        'print("#i{rm.getalA}")',
        'print(rm.getalA + rm.getalB)',
        'print(rm.geheim())',
    ],
    ids=[
        "print_read",
        "typed_decl_read",
        "assign_write",
        "string_interpolation",
        "typed_interpolation",
        "binary_expr_read",
        "private_method_call",
    ],
)
def test_private_member_denied_outside_class(snippet: str) -> None:
    """Given private members, When used outside the class, Then Access denied."""
    member = "geheim" if "geheim" in snippet else "getalA"
    _deny(_REKENMACHINE_CLASS + f"\nRekenmachine rm = Rekenmachine(4, 5)\n{snippet}\n", member)


def test_private_field_denied_as_call_argument() -> None:
    source = _REKENMACHINE_CLASS + """
function void show(int n) {
    print(n)
}

Rekenmachine rm = Rekenmachine(4, 5)
show(rm.getalA)
"""
    _deny(source, "getalA")


def test_private_field_denied_in_subclass() -> None:
    source = _REKENMACHINE_CLASS + """
class Turbo inherits Rekenmachine {
    public int peek() {
        return this.getalA
    }
}
"""
    _deny(source, "getalA")


def test_private_field_denied_on_unrelated_receiver_name() -> None:
    source = """
class Box {
    private int n
    public constructor(int n) { this.n = n }
}
Box a = Box(1)
Box b = Box(2)
print(a.n)
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'n' is private in class Box"):
        _analyze(source)


# --- Protected ---


def test_protected_field_denied_outside_hierarchy() -> None:
    source = """
class Car {
    protected string make
    public constructor(string make) { this.make = make }
}
Car car = Car("Toyota")
print(car.make)
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'make' is protected in class Car"):
        _analyze(source)


def test_protected_field_denied_in_string_interpolation_outside() -> None:
    source = """
class Car {
    protected string make
    public constructor(string make) { this.make = make }
}
Car car = Car("Toyota")
print("make={car.make}")
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'make' is protected"):
        _analyze(source)


def test_protected_field_allowed_in_subclass_methods() -> None:
    source = """
class Car {
    protected string make
    public constructor(string make) { this.make = make }
}
class Truck inherits Car {
    public string read() { return this.make }
    public string label() { return "truck={this.make}" }
}
"""
    _analyze(source)


# --- Positive: defining class + public API ---


def test_private_allowed_inside_defining_class_including_interpolation() -> None:
    source = """
class Car {
    private string make
    public constructor(string make) { this.make = make }
    public string describe() {
        return "make={this.make}"
    }
}
"""
    _analyze(source)


def test_public_api_readable_outside_including_interpolation() -> None:
    source = _REKENMACHINE_CLASS + """
Rekenmachine rm = Rekenmachine(4, 5)
print(rm.som())
print("product={rm.vermenigvuldigd()}")
int total = rm.som()
"""
    _analyze(source)


# --- Entity private (same access rules) ---


def test_entity_private_field_denied_outside() -> None:
    source = """
entity Order identity(id) {
    private fix int id
    private int qty
    public constructor(int id, int qty) {
        this.id = id
        this.qty = qty
    }
    public int getQty() { return this.qty }
}
Order o = Order(1, 3)
print(o.qty)
"""
    with pytest.raises(TranspileError, match=r"Access denied: 'qty' is private"):
        _analyze(source)


# --- Lexical scope is covered in test_block_scope.py; keep focus on members ---


def test_access_denied_message_names_member_and_class() -> None:
    """Compiler response must stay actionable for students / IDE."""
    source = _REKENMACHINE_CLASS + """
Rekenmachine rm = Rekenmachine(1, 2)
print(rm.getalB)
"""
    with pytest.raises(TranspileError) as ei:
        _analyze(source)
    msg = str(ei.value)
    assert "Access denied" in msg
    assert "getalB" in msg
    assert "private" in msg
    assert "Rekenmachine" in msg
