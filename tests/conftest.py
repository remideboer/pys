"""Shared test setup."""
from __future__ import annotations

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
