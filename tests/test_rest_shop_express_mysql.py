"""examples/by-target/javascript/rest-api/express/mysql — transpile gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
MYSQL = ROOT / "examples" / "by-target" / "javascript" / "rest-api" / "express" / "mysql"
MAIN = MYSQL / "src" / "main.pys"


def test_express_mysql_main_transpiles(monkeypatch: pytest.MonkeyPatch) -> None:
    assert MAIN.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(MYSQL))
    modules = transpile_with_modules(MAIN, target="javascript")
    assert "main" in modules
    joined = "\n".join(modules.values())
    assert "mysql2" in joined or "createConnection" in joined
    assert "express" in joined
    assert "ShopDatabase" in joined or "ShopStore" in joined
