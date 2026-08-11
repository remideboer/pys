"""IDE --format / format_file helper."""
from __future__ import annotations

from pathlib import Path

from transpiler.ide import format_file


def test_format_file_ok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(tmp_path))
    path = tmp_path / "a.pys"
    path.write_text("class C{\npublic void go(){}\n}\n", encoding="utf-8")
    result = format_file(path)
    assert result["ok"] is True
    assert "class C {" in result["text"]
    assert format_file(path, source=result["text"])["text"] == result["text"]


def test_format_file_parse_fail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(tmp_path))
    path = tmp_path / "bad.pys"
    path.write_text("class {\n", encoding="utf-8")
    result = format_file(path)
    assert result["ok"] is False
    assert "text" not in result or not result.get("text")


def test_format_file_stdin_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(tmp_path))
    path = tmp_path / "buf.pys"
    path.write_text("print(1)\n", encoding="utf-8")
    result = format_file(path, source="class C{\npublic void go(){}\n}\n")
    assert result["ok"] is True
    assert "class C {" in result["text"]
