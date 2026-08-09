"""examples/by-target/javascript/rest-api/express/jwt — transpile + crypto suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.transpiler import transpile_with_modules, run_source
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
JWT = ROOT / "examples" / "by-target" / "javascript" / "rest-api" / "express" / "jwt"
MAIN = JWT / "src" / "main.pys"
CRYPTO = JWT / "tests" / "test_jwt_crypto.pys"


def test_express_jwt_main_transpiles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(JWT))
    modules = transpile_with_modules(MAIN, target="javascript")
    assert "main" in modules
    joined = "\n".join(modules.values())
    assert "/api/login" in joined or "login" in joined
    assert "JwtService" in joined or "jwt_service" in modules


def test_express_jwt_crypto_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(JWT))
    assert run_source(CRYPTO, target="javascript") == 0
