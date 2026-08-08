"""library-tests/fastapi-shop — transpile gate + optional live MySQL smoke."""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from transpiler.transpiler import run_source, transpile_with_modules
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "library-tests" / "fastapi-shop"
MAIN = SHOP / "src" / "main.pys"
SMOKE = SHOP / "tests" / "smoke_live.pys"


def test_fastapi_shop_main_transpiles() -> None:
    assert MAIN.is_file()
    os.environ[WORKSPACE_ROOT_ENV] = str(SHOP.resolve())
    modules = transpile_with_modules(MAIN)
    assert "main" in modules
    assert "routes_meta" in modules
    assert "app_factory" in modules
    joined = "\n".join(modules.values())
    assert "@appRouter.get" in joined or "@appRouter.post" in joined
    assert "def handle" not in joined  # sanity: our routes exist
    assert "def health" in modules["routes_meta"]
    assert "request: Request" in modules["routes_meta"]
    for stem, python_text in modules.items():
        try:
            ast.parse(python_text)
        except SyntaxError as exc:
            raise AssertionError(f"fastapi-shop module {stem!r}: {exc}") from exc


def _mysql_reachable() -> bool:
    try:
        import mysql.connector
    except ImportError:
        return False
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="pys",
            password="123456789",
            database="shop",
            connection_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _mysql_reachable(), reason="MySQL shop DB not available (CI)")
def test_fastapi_shop_live_smoke() -> None:
    os.environ[WORKSPACE_ROOT_ENV] = str(SHOP.resolve())
    assert run_source(SMOKE) == 0
