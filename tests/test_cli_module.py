"""CLI entry: python -m transpiler must invoke main()."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_pythonpath() -> dict[str, str]:
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_module_run_executes_and_prints(tmp_path: Path) -> None:
    source = tmp_path / "hello.pys"
    source.write_text('print("cli-ok")\n', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "transpiler", "run", str(source)],
        check=False,
        capture_output=True,
        text=True,
        env=_repo_pythonpath(),
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert "cli-ok" in proc.stdout


def test_module_run_shows_deps_resolve(tmp_path: Path) -> None:
    (tmp_path / "pys.deps").write_text(
        "[dependencies]\n\tmysql-connector-python\n\t\tversion: 8.0.33\n",
        encoding="utf-8",
    )
    source = tmp_path / "hello.pys"
    source.write_text('print("deps-ok")\n', encoding="utf-8")
    env = _repo_pythonpath()
    env["PYS_REPO"] = str(tmp_path / "repo")
    proc = subprocess.run(
        [sys.executable, "-m", "transpiler", "run", str(source)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Resolving 1 dependency" in proc.stdout
    assert "mysql-connector-python" in proc.stdout
    assert "Dependencies ready." in proc.stdout
    assert "deps-ok" in proc.stdout
