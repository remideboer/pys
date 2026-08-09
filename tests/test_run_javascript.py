"""Run JavaScript emit target via Node when available."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from transpiler.transpiler import run_source

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "examples" / "js_smoke.pys"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_js_smoke_runs_under_node() -> None:
    code = run_source(SMOKE, target="javascript")
    assert code == 0


def test_js_smoke_runs_under_python() -> None:
    code = run_source(SMOKE, target="python")
    assert code == 0


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_cli_run_target_javascript() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "transpiler",
            "run",
            str(SMOKE),
            "--target",
            "javascript",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0
    assert "hello-js" in proc.stdout
    assert "5" in proc.stdout
    assert "red" in proc.stdout
    assert "hi:Ada" in proc.stdout
