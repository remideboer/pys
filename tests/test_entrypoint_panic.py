"""Manifest entrypoint resolution and top-level panic behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from transpiler import project_manifest
from transpiler.ide import analyze_file, prepare_debug
from transpiler.project_manifest import load_project_main, resolve_entrypoint
from transpiler.transpiler import TranspileError, run_source


def test_manifest_main_is_contained_and_resolved(tmp_path: Path) -> None:
    main = tmp_path / "src" / "app.pys"
    main.parent.mkdir()
    main.write_text('print("ready")\n', encoding="utf-8")
    manifest = tmp_path / "pys.toml"
    manifest.write_text('[project]\nmain = "src/app.pys"\n', encoding="utf-8")

    assert load_project_main(manifest) == main.resolve()
    assert resolve_entrypoint(tmp_path) == main.resolve()


def test_manifest_main_cannot_escape_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    manifest = project / "pys.toml"
    manifest.write_text('[project]\nmain = "../outside.pys"\n', encoding="utf-8")

    with pytest.raises(TranspileError, match="outside the project"):
        load_project_main(manifest)


def test_python_310_manifest_fallback_rejects_non_string_main(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = tmp_path / "pys.toml"
    manifest.write_text("[project]\nmain = 123\n", encoding="utf-8")
    monkeypatch.setattr(project_manifest.sys, "version_info", (3, 10))

    with pytest.raises(TranspileError, match="non-empty path string"):
        load_project_main(manifest)


def test_configured_main_rejects_conflicting_selected_file(tmp_path: Path) -> None:
    main = tmp_path / "main.pys"
    other = tmp_path / "other.pys"
    main.write_text('print("main")\n', encoding="utf-8")
    other.write_text('print("other")\n', encoding="utf-8")
    (tmp_path / "pys.toml").write_text(
        '[project]\nmain = "main.pys"\n', encoding="utf-8"
    )

    with pytest.raises(TranspileError, match="configured entrypoint"):
        resolve_entrypoint(other)


def test_directory_without_manifest_main_is_configuration_error(
    tmp_path: Path,
) -> None:
    (tmp_path / "pys.toml").write_text("[project]\n", encoding="utf-8")

    with pytest.raises(TranspileError, match=r"\[project\]\.main"):
        resolve_entrypoint(tmp_path)


def test_direct_file_top_level_propagate_panics(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    main = tmp_path / "main.pys"
    main.write_text(
        "function result<int, string> fail() {\n"
        '    return err("broken input")\n'
        "}\n"
        "int value = fail() propagate\n"
        'print("unreachable")\n',
        encoding="utf-8",
    )

    assert run_source(main) != 0
    captured = capfd.readouterr()
    assert "unreachable" not in captured.out
    assert "PYS panic: broken input" in captured.err
    assert "main.pys:4" in captured.err


def test_manifest_directory_run_uses_main_and_preserves_import_chain(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    helper = tmp_path / "helper.pys"
    helper.write_text(
        "global function result<int, string> load() {\n"
        '    return err("missing config")\n'
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "app.pys"
    main.write_text(
        "import load from helper.pys\n"
        "function result<int, string> start() {\n"
        "    int value = load() propagate\n"
        "    return ok(value)\n"
        "}\n"
        "int value = start() propagate\n",
        encoding="utf-8",
    )
    (tmp_path / "pys.toml").write_text(
        '[project]\nmain = "app.pys"\n', encoding="utf-8"
    )

    assert run_source(tmp_path) != 0
    captured = capfd.readouterr()
    assert "PYS panic: missing config" in captured.err
    assert "app.pys:3" in captured.err
    assert "app.pys:6" in captured.err


def test_imported_top_level_propagate_never_gets_entrypoint_semantics(
    tmp_path: Path,
) -> None:
    helper = tmp_path / "helper.pys"
    helper.write_text(
        "global function result<int, string> fail() {\n"
        '    return err("bad")\n'
        "}\n"
        "int value = fail() propagate\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pys"
    main.write_text("import all from helper.pys\n", encoding="utf-8")

    with pytest.raises(TranspileError, match="enclosing function"):
        run_source(main)


def test_debug_directory_uses_same_manifest_entrypoint(
    tmp_path: Path,
) -> None:
    main = tmp_path / "src" / "app.pys"
    main.parent.mkdir()
    main.write_text('print("debug")\n', encoding="utf-8")
    (tmp_path / "pys.toml").write_text(
        '[project]\nmain = "src/app.pys"\n', encoding="utf-8"
    )

    result = prepare_debug(tmp_path, tmp_path / "debug-out")

    assert result["ok"] is True
    assert Path(result["main"]).name == "app.py"
    assert Path(result["cwd"]) == main.parent


def test_ide_analysis_applies_top_level_propagate_only_to_manifest_main(
    tmp_path: Path,
) -> None:
    main = tmp_path / "main.pys"
    helper = tmp_path / "helper.pys"
    source = (
        "function result<int, string> fail() {\n"
        '    return err("bad")\n'
        "}\n"
        "int value = fail() propagate\n"
    )
    main.write_text(source, encoding="utf-8")
    helper.write_text(source, encoding="utf-8")
    (tmp_path / "pys.toml").write_text(
        '[project]\nmain = "main.pys"\n', encoding="utf-8"
    )

    assert analyze_file(main)["ok"] is True
    helper_result = analyze_file(helper)
    assert helper_result["ok"] is False
    assert helper_result["error"]["code"] == "pys.propagate-return"


def test_result_panic_teaching_project_has_documented_terminal_outcome(
    monkeypatch,
    capfd,
) -> None:
    project = Path(__file__).parents[1] / "examples" / "result_panic"
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(project))

    assert run_source(project) == 1

    captured = capfd.readouterr()
    assert captured.out == ""
    assert "PYS panic: missing count" in captured.err
    assert "app.pys:14 in start" in captured.err
    assert "app.pys:18 in <entrypoint>" in captured.err


def test_handled_propagation_does_not_pollute_a_later_panic_chain(
    tmp_path: Path,
    monkeypatch,
    capfd,
) -> None:
    source = tmp_path / "main.pys"
    source.write_text(
        "function result<int, string> forward(result<int, string> input) {\n"
        "    int value = input propagate\n"
        "    return ok(value)\n"
        "}\n"
        'result<int, string> failure = err("reused")\n'
        "result<int, string> handled = forward(failure)\n"
        "switch (handled) {\n"
        "    case ok(value):\n"
        "        print(value)\n"
        "    case err(error):\n"
        '        print("handled")\n'
        "}\n"
        "int value = forward(failure) propagate\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYS_WORKSPACE_ROOT", str(tmp_path))

    assert run_source(source) == 1

    captured = capfd.readouterr()
    assert captured.out.splitlines() == ["handled"]
    assert captured.err.count("main.pys:2 in forward") == 1
    assert "main.pys:13 in <entrypoint>" in captured.err
