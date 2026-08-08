"""data / entity: parse/sem/emit happy paths and SA rejections."""
from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
DATA_EXAMPLE = ROOT / "examples" / "data.pys"
ENTITIES_EXAMPLE = ROOT / "examples" / "entities.pys"
SHOP_APP = ROOT / "examples" / "database" / "shop_app.pys"


def test_example_data_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert DATA_EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(DATA_EXAMPLE.parent))
    assert run_source(DATA_EXAMPLE) == 0


def test_example_entities_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert ENTITIES_EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ENTITIES_EXAMPLE.parent))
    assert run_source(ENTITIES_EXAMPLE) == 0


def test_example_database_shop_transpiles() -> None:
    """MySQL shop console must compile (run needs a live `shop` database)."""
    from transpiler.transpiler import transpile_with_modules

    assert SHOP_APP.is_file()
    modules = transpile_with_modules(SHOP_APP)
    assert set(modules) >= {
        "shop_app",
        "models",
        "db",
        "mappers",
        "repositories",
        "console",
        "menus",
        "gui",
    }
    assert "class Product" in modules["models"]
    assert "class OrderLine" in modules["models"]
    assert "__eq__" in modules["models"]
    assert "_pys_fix_fields" in modules["models"]
    assert "ProductMapper" in modules["mappers"]
    assert "MysqlProductMapper" in modules["mappers"]
    assert "ProductRepository" in modules["repositories"]
    assert "DefaultProductRepository" in modules["repositories"]
    assert "ShopDatabase" not in modules["repositories"]
    assert "SELECT " not in modules["repositories"]
    assert "MainMenu" in modules["menus"]
    assert "ShopGuiApp" in modules["gui"]
    assert "ColumnTable" in modules["gui"]
    assert "SELECT " not in modules["gui"]
    assert "mysql.connector" in modules["db"]
    for text in modules.values():
        ast.parse(text)


def test_example_data_emit_is_frozen_dataclass() -> None:
    py = transpile(DATA_EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "@dataclass(frozen=True)" in py
    assert "_pys_struct_copy" in py


def test_example_entities_emit_identity_eq() -> None:
    py = transpile(ENTITIES_EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "def __eq__(self, other):" in py
    assert "def __hash__(self):" in py
    assert "_pys_fix_fields" in py


def test_data_equality_and_immutability(capsys: pytest.CaptureFixture[str]) -> None:
    source = """
data Money {
    int amountCents
    string currency
}
Money m1 = Money(100, "USD")
Money m2 = Money(100, "USD")
print(m1 == m2)
print(m1 != Money(100, "EUR"))
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["True", "True"]


def test_entity_identity_equality_ignores_other_fields() -> None:
    source = """
entity Customer identity(customerId) {
    private fix int customerId
    public string name

    public constructor(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}
Customer a = Customer(1, "A")
Customer b = Customer(1, "B")
Customer c = Customer(2, "A")
print(a == b)
print(a == c)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["True", "False"]


def test_entity_composite_key_parent_then_local() -> None:
    source = """
entity Order identity(orderId) {
    private fix int orderId
    public string placedAt

    public constructor(int orderId, string placedAt) {
        this.orderId = orderId
        this.placedAt = placedAt
    }
}
entity OrderLine inherits Order identity(lineNumber) {
    private fix int lineNumber
    public int quantity

    public constructor(int orderId, string placedAt, int lineNumber, int quantity) {
        super(orderId, placedAt)
        this.lineNumber = lineNumber
        this.quantity = quantity
    }
}
OrderLine a = OrderLine(10, "t", 1, 2)
OrderLine b = OrderLine(10, "u", 1, 9)
OrderLine c = OrderLine(10, "t", 2, 2)
print(a == b)
print(a == c)
"""
    py = transpile(source)
    ns: dict = {}
    exec(py, ns)
    assert ns["a"] == ns["b"]
    assert ns["a"] != ns["c"]
    assert hash(ns["a"]) == hash(ns["b"])


@pytest.mark.parametrize(
    "source, match",
    [
        (
            "entity E {\n  private fix int id\n  public constructor(int id) { this.id = id }\n}\n",
            r"identity",
        ),
        (
            "entity E identity(id) {\n  private int id\n  public constructor(int id) { this.id = id }\n}\n",
            r"fix",
        ),
        (
            "entity E identity(missing) {\n  private fix int id\n  public constructor(int id) { this.id = id }\n}\n",
            r"identity field",
        ),
        (
            "entity E identity(id) {\n  private fix int id\n}\n",
            r"constructor",
        ),
        (
            "class C { public constructor() {} }\n"
            "entity E inherits C identity(id) {\n"
            "  private fix int id\n"
            "  public constructor(int id) { this.id = id }\n"
            "}\n",
            r"only inherit another entity",
        ),
        (
            "entity E identity(id) {\n"
            "  private fix int id\n"
            "  public constructor(int id) { this.id = id }\n"
            "  public bool equals(E other) { return true }\n"
            "}\n",
            r"equals",
        ),
        (
            "data D { int x }\nD d = D(1)\nd.x = 2\n",
            r"data",
        ),
        (
            "data D inherits Foo { int x }\n",
            r"data|inherits|cannot",
        ),
    ],
)
def test_data_entity_sa_rejects(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_entity_rejects_fix_assign_outside_ctor() -> None:
    source = """
entity E identity(id) {
    private fix int id
    public string name

    public constructor(int id, string name) {
        this.id = id
        this.name = name
    }

    public void bump() {
        this.id = this.id + 1
    }
}
"""
    with pytest.raises(TranspileError, match=r"fix field"):
        transpile(source)
