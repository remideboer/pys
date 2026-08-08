"""Shared test setup."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler import parse as parse_mod
from transpiler import pytypes


@pytest.fixture(autouse=True)
def _reset_pytypes_caches() -> None:
    """Tests build site packages on the fly, so memoized lookups must not leak."""
    pytypes.clear_filesystem_caches()


@pytest.fixture(autouse=True)
def _reset_brace_engine() -> None:
    """Restore the process default brace engine after tests that flip it."""
    yield
    parse_mod.set_brace_engine("rd")


def stub_mysql_connector_site(tmp_path: Path) -> Path:
    """Minimal site layout so ``import mysql.connector`` resolves without install."""
    site = tmp_path / "mysql_site"
    pkg = site / "mysql" / "connector"
    pkg.mkdir(parents=True)
    (site / "mysql" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return site


@pytest.fixture
def mysql_connector_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ImportResolver deps paths at a stub mysql.connector package."""
    site = stub_mysql_connector_site(tmp_path)
    monkeypatch.setattr(
        "transpiler.imports.ImportResolver._deps_paths",
        lambda self: [site],
    )
    return site
