"""prepare_debug: temp .py + pysmap sidecars for DAP."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from transpiler.ide import main as ide_main
from transpiler.ide import prepare_debug
from transpiler.workspace import WORKSPACE_ROOT_ENV


def test_prepare_debug_writes_py_and_maps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    src = ws / "demo.pys"
    src.write_text("int x = 1\nprint(x)\n", encoding="utf-8")
    out = tmp_path / "dbg"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ws))
    result = prepare_debug(src, out)
    assert result["ok"] is True
    main = Path(result["main"])
    assert main.is_file()
    assert "x = 1" in main.read_text(encoding="utf-8")
    assert result["pythonpath_prepend"] == str(out.resolve())
    assert result["python"]
    map_path = Path(result["maps"]["demo"])
    assert map_path.is_file()
    sidecar = json.loads(map_path.read_text(encoding="utf-8"))
    assert sidecar["version"] == 1
    assert Path(sidecar["pys"]).resolve() == src.resolve()
    assert sidecar["lines"]
    assert any(e["pys"] == 1 for e in sidecar["lines"])
    assert "names" in sidecar
    assert sidecar["hidePrefixes"] == ["_pys_", "__pys_", "_Pys"]


def test_prepare_debug_prepends_deps_site_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Debug launch PYTHONPATH must include pys.deps sites (parity with Run)."""
    import os
    import sys

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "pys.deps").write_text(
        "[interpreter]\n\tversion: any\n"
        "[dependencies]\n\tdemo\n\t\tversion: 1.0.0\n",
        encoding="utf-8",
    )
    src = ws / "app.pys"
    src.write_text("print(1)\n", encoding="utf-8")
    out = tmp_path / "dbg"
    site = tmp_path / "fake-site"
    site.mkdir()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ws))
    monkeypatch.setattr(
        "transpiler.deps.resolve_python_executable",
        lambda _config: sys.executable,
    )
    monkeypatch.setattr(
        "transpiler.deps.resolve_site_paths",
        lambda *_a, **_k: [site],
    )
    result = prepare_debug(src, out)
    assert result["ok"] is True
    parts = result["pythonpath_prepend"].split(os.pathsep)
    assert parts[0] == str(out.resolve())
    assert str(site) in parts
    assert result["python"] == sys.executable


def test_prepare_debug_includes_lambda_capture_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    src = ws / "lam.pys"
    src.write_text(
        "shared int hits = 0\n"
        "list<int> xs = [1]\n"
        "xs.loop(n => {\n"
        "  hits += 1\n"
        "  return n\n"
        "})\n",
        encoding="utf-8",
    )
    out = tmp_path / "dbg"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ws))
    result = prepare_debug(src, out)
    assert result["ok"] is True
    sidecar = json.loads(Path(result["maps"]["lam"]).read_text(encoding="utf-8"))
    assert sidecar["names"].get("_c_hits") == "hits"


def test_prepare_debug_cli_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    src = ws / "a.pys"
    src.write_text("print(1)\n", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ws))
    code = ide_main(["--prepare-debug", str(out), str(src)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert Path(payload["main"]).is_file()


def test_prepare_debug_rejects_outside_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    outside = tmp_path / "outside.pys"
    outside.write_text("print(1)\n", encoding="utf-8")
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(ws))
    result = prepare_debug(outside, tmp_path / "dbg")
    assert result["ok"] is False
    assert "workspace" in result["error"]["message"].lower()
