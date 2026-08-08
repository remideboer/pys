"""examples/rest-api/shop/jwt — transpile main + run JWT crypto suite."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
JWT = ROOT / "examples" / "rest-api" / "shop" / "jwt"
MAIN = JWT / "src" / "main.pys"
CRYPTO = JWT / "tests" / "test_jwt_crypto.pys"


def test_shop_jwt_main_transpiles(
    mysql_connector_site: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(JWT))
    modules = transpile_with_modules(MAIN)
    assert "main" in modules
    assert "jwt_service" in modules or "JwtService" in modules.get("jwt_service", "")
    for stem, python_text in modules.items():
        try:
            ast.parse(python_text)
        except SyntaxError as exc:
            raise AssertionError(f"shop jwt module {stem!r}: {exc}") from exc
    joined = "\n".join(modules.values())
    assert "/api/login" in joined or "login" in joined


def test_shop_jwt_crypto_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(JWT))
    assert run_source(CRYPTO) == 0
