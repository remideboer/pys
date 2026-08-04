"""Source roots / same-package resolution (ADR-017, F-006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.project_manifest import (
    package_identity,
    package_mismatch_diagnostic,
    same_package,
)
from transpiler.transpiler import TranspileError, transpile


def _project(tmp_path: Path) -> Path:
    (tmp_path / "pys.toml").write_text(
        '[source_roots]\nmain = "src"\ntest = "tests"\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "billing").mkdir(parents=True)
    (tmp_path / "tests" / "billing").mkdir(parents=True)
    (tmp_path / "tests" / "test_utils").mkdir(parents=True)
    return tmp_path


def test_same_package_across_source_roots(tmp_path: Path) -> None:
    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    test = root / "tests" / "billing" / "InvoiceTest.pys"
    inv.write_text("package class Invoice {}\n", encoding="utf-8")
    test.write_text("# test\n", encoding="utf-8")
    assert same_package(inv, test)
    assert package_identity(inv).rel_dir == "billing"
    assert package_identity(test).rel_dir == "billing"


def test_different_relative_dirs_are_not_same_package(tmp_path: Path) -> None:
    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    wrong = root / "tests" / "test_utils" / "InvoiceTest.pys"
    inv.write_text("package class Invoice {}\n", encoding="utf-8")
    wrong.write_text("# test\n", encoding="utf-8")
    assert not same_package(inv, wrong)


def test_legacy_same_folder_without_manifest(tmp_path: Path) -> None:
    a = tmp_path / "a.pys"
    b = tmp_path / "b.pys"
    a.write_text("x\n", encoding="utf-8")
    b.write_text("y\n", encoding="utf-8")
    assert same_package(a, b)
    other = tmp_path / "sub"
    other.mkdir()
    c = other / "c.pys"
    c.write_text("z\n", encoding="utf-8")
    assert not same_package(a, c)


def test_bare_module_resolves_across_source_roots(tmp_path: Path) -> None:
    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    test = root / "tests" / "billing" / "InvoiceTest.pys"
    inv.write_text(
        "package function recalculateTotal(){\n    print(\"ok\")\n}\n",
        encoding="utf-8",
    )
    test.write_text(
        "import recalculateTotal from Invoice\nrecalculateTotal()\n",
        encoding="utf-8",
    )
    py = transpile(test.read_text(encoding="utf-8"), source_path=test)
    assert "from Invoice import recalculateTotal" in py


def test_import_package_export_across_mirrored_roots(tmp_path: Path) -> None:
    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    test = root / "tests" / "billing" / "InvoiceTest.pys"
    inv.write_text(
        "package function recalculateTotal(){\n    print(\"ok\")\n}\n",
        encoding="utf-8",
    )
    test.write_text(
        "import recalculateTotal from ../../src/billing/Invoice.pys\n"
        "recalculateTotal()\n",
        encoding="utf-8",
    )
    py = transpile(test.read_text(encoding="utf-8"), source_path=test)
    assert "from Invoice import recalculateTotal" in py


def test_wrong_test_folder_diagnostic(tmp_path: Path) -> None:
    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    wrong = root / "tests" / "test_utils" / "InvoiceTest.pys"
    inv.write_text(
        "package function recalculateTotal(){\n    print(\"ok\")\n}\n",
        encoding="utf-8",
    )
    wrong.write_text(
        "import recalculateTotal from ../../src/billing/Invoice.pys\n",
        encoding="utf-8",
    )
    with pytest.raises(TranspileError, match="Did you mean to place this file") as exc:
        transpile(wrong.read_text(encoding="utf-8"), source_path=wrong)
    err = exc.value
    msg = str(err)
    assert "package 'test_utils'" in msg
    assert "package 'billing'" in msg
    assert "tests/billing/InvoiceTest.pys" in msg.replace("\\", "/")
    assert err.code == "pys.package-mismatch"
    assert err.suggested_fix == "tests/billing/InvoiceTest.pys"
    assert err.tips


def test_package_peer_files_across_roots(tmp_path: Path) -> None:
    from transpiler.project_manifest import package_peer_files

    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    test = root / "tests" / "billing" / "InvoiceTest.pys"
    inv.write_text("package class Invoice {}\n", encoding="utf-8")
    test.write_text("# test\n", encoding="utf-8")
    peers = {p.name for p in package_peer_files(inv)}
    assert peers == {"Invoice.pys", "InvoiceTest.pys"}


def test_wrong_place_example_reproduces_diagnostic() -> None:
    """examples/source_roots wrong-folder stub: enable import → package-mismatch."""
    root = Path(__file__).resolve().parents[1] / "examples" / "source_roots"
    wrong = root / "tests" / "test_utils" / "WrongPlaceTest.pys"
    text = wrong.read_text(encoding="utf-8")
    text = text.replace(
        "# import formatInvoice from ../../src/billing/Invoice.pys\n",
        "import formatInvoice from ../../src/billing/Invoice.pys\n",
    )
    with pytest.raises(TranspileError) as exc:
        transpile(text, source_path=wrong)
    assert exc.value.code == "pys.package-mismatch"
    assert exc.value.suggested_fix == "tests/billing/WrongPlaceTest.pys"


def test_mismatch_diagnostic_helper(tmp_path: Path) -> None:
    root = _project(tmp_path)
    inv = root / "src" / "billing" / "Invoice.pys"
    wrong = root / "tests" / "test_utils" / "InvoiceTest.pys"
    inv.write_text("package class Invoice {}\n", encoding="utf-8")
    wrong.write_text("#\n", encoding="utf-8")
    hint = package_mismatch_diagnostic(
        importer=wrong, declaree=inv, symbol="Invoice.recalculateTotal"
    )
    assert hint is not None
    assert "test_utils" in hint
    assert "billing" in hint
    assert "Did you mean" in hint
