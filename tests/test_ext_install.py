"""Tests for contributor VSIX install helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler import ext_install


def test_parse_vsix_version() -> None:
    assert ext_install.parse_vsix_version(Path("pys-language-0.0.50.vsix")) == (0, 0, 50)
    assert ext_install.parse_vsix_version(Path("other.vsix")) is None


def test_latest_vsix_picks_highest_semver(tmp_path: Path) -> None:
    (tmp_path / "pys-language-0.0.9.vsix").write_bytes(b"x")
    (tmp_path / "pys-language-0.0.50.vsix").write_bytes(b"y")
    (tmp_path / "pys-language-0.0.48.vsix").write_bytes(b"z")
    (tmp_path / "notes.txt").write_text("nope", encoding="utf-8")
    assert ext_install.latest_vsix(tmp_path).name == "pys-language-0.0.50.vsix"


def test_latest_vsix_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No pys-language"):
        ext_install.latest_vsix(tmp_path)


def test_find_extension_dir_uses_repo(tmp_path: Path) -> None:
    ext = tmp_path / "pys-language"
    ext.mkdir()
    (ext / "package.json").write_text("{}", encoding="utf-8")
    assert ext_install.find_extension_dir(tmp_path) == ext.resolve()


def test_resolve_editor_cli_prefers_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ext_install.shutil,
        "which",
        lambda name: f"/bin/{name}" if name == "cursor" else None,
    )
    assert ext_install.resolve_editor_cli("auto") == "/bin/cursor"


def test_resolve_editor_cli_falls_back_to_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ext_install.shutil,
        "which",
        lambda name: f"/bin/{name}" if name == "code" else None,
    )
    assert ext_install.resolve_editor_cli("auto") == "/bin/code"


def test_command_argv_wraps_windows_cmd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ext_install.os, "name", "nt")
    monkeypatch.setattr(ext_install.shutil, "which", lambda name: name)
    assert ext_install.command_argv(r"C:\cursor.cmd", "--force") == [
        "cmd",
        "/c",
        r"C:\cursor.cmd",
        "--force",
    ]


def test_command_argv_unix_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ext_install.os, "name", "posix")
    monkeypatch.setattr(ext_install.shutil, "which", lambda name: name)
    assert ext_install.command_argv("/bin/cursor", "--force") == ["/bin/cursor", "--force"]


def test_install_vsix_runs_editor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    vsix = tmp_path / "pys-language-0.0.1.vsix"
    vsix.write_bytes(b"vsix")
    calls: list[list[str]] = []

    monkeypatch.setattr(ext_install.os, "name", "nt")
    monkeypatch.setattr(
        ext_install,
        "resolve_editor_cli",
        lambda _prefer: r"C:\Users\me\cursor.cmd",
    )
    monkeypatch.setattr(ext_install.shutil, "which", lambda name: name)
    monkeypatch.setattr(
        ext_install.subprocess,
        "run",
        lambda cmd, check: calls.append(list(cmd)),
    )
    cmd = ext_install.install_vsix(vsix, editor="cursor")
    assert cmd[:3] == ["cmd", "/c", r"C:\Users\me\cursor.cmd"]
    assert "--install-extension" in cmd
    assert str(vsix.resolve()) in cmd
    assert "--force" in cmd
    assert calls == [cmd]


def test_install_extension_reloads_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ext = tmp_path / "pys-language"
    ext.mkdir()
    (ext / "package.json").write_text("{}", encoding="utf-8")
    vsix = ext / "pys-language-0.0.1.vsix"
    vsix.write_bytes(b"x")
    reloads: list[bool] = []
    monkeypatch.setattr(ext_install, "build_vsix", lambda *_a, **_k: None)
    monkeypatch.setattr(ext_install, "install_vsix", lambda *_a, **_k: ["ok"])
    monkeypatch.setattr(
        ext_install,
        "reload_editor_window",
        lambda: reloads.append(True),
    )
    assert ext_install.install_extension(repo_root=tmp_path, build=False) == vsix
    assert reloads == [True]


def test_install_extension_can_skip_reload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ext = tmp_path / "pys-language"
    ext.mkdir()
    (ext / "package.json").write_text("{}", encoding="utf-8")
    vsix = ext / "pys-language-0.0.1.vsix"
    vsix.write_bytes(b"x")
    monkeypatch.setattr(ext_install, "install_vsix", lambda *_a, **_k: ["ok"])
    monkeypatch.setattr(
        ext_install,
        "reload_editor_window",
        lambda: (_ for _ in ()).throw(AssertionError("should skip")),
    )
    assert (
        ext_install.install_extension(repo_root=tmp_path, build=False, reload=False)
        == vsix
    )
