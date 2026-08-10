"""IDE analyze_file buffer override (--stdin / source=)."""
from __future__ import annotations

from pathlib import Path

from transpiler.ide import analyze_file


def test_analyze_file_source_override_ignores_disk(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(tmp_path))
    path = tmp_path / "buf.pys"
    path.write_text("print(1)\n", encoding="utf-8")
    bad = """
trait Presenter {
    require int a
}
"""
    result = analyze_file(path, source=bad)
    assert result["ok"] is False
    err = result["error"]
    assert err["code"] == "pys.trait-require-typo"
    assert err["suggested_fix"] == "requires"
    # Disk is still valid — override must be what was analyzed.
    disk_ok = analyze_file(path)
    assert disk_ok["ok"] is True
