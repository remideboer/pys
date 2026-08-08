"""examples/rest-api/shop/mysql — transpile gate (no live MySQL in CI)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
MYSQL = ROOT / "examples" / "rest-api" / "shop" / "mysql"
MAIN = MYSQL / "src" / "main.pys"


def test_shop_mysql_main_transpiles(
    mysql_connector_site: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert MAIN.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(MYSQL))
    modules = transpile_with_modules(MAIN)
    assert "main" in modules
    assert "store" in modules or "Store" in "\n".join(modules.values()) or "ShopStore" in modules.get(
        "store", ""
    )
    for stem, python_text in modules.items():
        try:
            ast.parse(python_text)
        except SyntaxError as exc:
            raise AssertionError(f"shop mysql module {stem!r}: {exc}") from exc
    joined = "\n".join(modules.values())
    assert "mysql.connector" in joined or "ShopDatabase" in joined
