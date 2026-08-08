from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


BOOK = Path(__file__).resolve().parents[1] / "book"


def _load_builder():
    sys.path.insert(0, str(BOOK))
    try:
        spec = importlib.util.spec_from_file_location(
            "pys_book_build_html", BOOK / "build_html.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(BOOK))


def _rewrite(href: str) -> str:
    builder = _load_builder()
    match = re.search(r'href="([^"]+)"', f'<a href="{href}">link</a>')
    assert match
    return builder.md_href_to_html(match)


def test_summary_link_rewrites_to_generated_index() -> None:
    assert _rewrite("SUMMARY.md") == 'href="index.html"'


def test_repo_file_link_rewrites_to_github_blob() -> None:
    assert _rewrite("../docs/LANGUAGE.md") == (
        'href="https://github.com/remideboer/pys/blob/main/docs/LANGUAGE.md"'
    )


def test_repo_directory_link_rewrites_to_github_tree() -> None:
    assert _rewrite("../examples/source_roots/") == (
        "href="
        '"https://github.com/remideboer/pys/tree/main/examples/source_roots"'
    )


def test_result_teaching_snippets_stay_compilable() -> None:
    from transpiler.transpiler import transpile

    for name in ("basics_outcomes.md", "chapter_8_4_no_direct_twin.md"):
        text = (BOOK / name).read_text(encoding="utf-8")
        blocks = re.findall(r"```pys\n(.*?)```", text, flags=re.DOTALL)
        assert blocks, f"No PYS teaching blocks found in {name}"
        for source in blocks:
            transpile(
                source,
                source_path=BOOK / name,
                is_entrypoint="int count = readCount() propagate" in source,
            )


def test_book_highlighter_recognizes_result_language_surface() -> None:
    sys.path.insert(0, str(BOOK))
    try:
        from pys_highlight import highlight_pys

        highlighted = highlight_pys(
            "result<int, string> outcome = ok(1)\n"
            "int value = outcome propagate\n"
        )
    finally:
        sys.path.remove(str(BOOK))

    assert '<span class="tok-type">result</span>' in highlighted
    assert '<span class="tok-builtin">ok</span>' in highlighted
    assert '<span class="tok-kw">propagate</span>' in highlighted


def test_optional_computer_model_chapters_follow_the_core_course(capsys) -> None:
    from transpiler.transpiler import transpile

    summary = (BOOK / "SUMMARY.md").read_text(encoding="utf-8")
    # Session 10 = patterns; 11 = C#/Java transfer; 12 = under the hood (optional).
    patterns = summary.index("# 10. Session — Patterns")
    session7 = summary.index("# 11. Session 7")
    under_the_hood = summary.index("# 12. Under the hood")
    assert patterns < session7 < under_the_hood
    assert under_the_hood < summary.index("# 13. Exercises")

    for name in ("under_the_hood_entrypoint.md", "under_the_hood_memory.md"):
        text = (BOOK / name).read_text(encoding="utf-8")
        blocks = re.findall(r"```pys\n(.*?)```", text, flags=re.DOTALL)
        assert blocks, f"No PYS teaching blocks found in {name}"
        for source in blocks:
            exec(transpile(source, source_path=BOOK / name), {})

    assert capsys.readouterr().out.splitlines() == [
        "program started",
        "12",
        "2",
        "1",
        "9",
        "2",  # IdCounter.getTotal() after two constructions (static field)
    ]

    index = (BOOK / "html" / "index.html").read_text(encoding="utf-8")
    assert 'href="under_the_hood_entrypoint.html"' in index
    assert 'href="under_the_hood_memory.html"' in index
    entrypoint_html = (
        BOOK / "html" / "under_the_hood_entrypoint.html"
    ).read_text(encoding="utf-8")
    memory_html = (BOOK / "html" / "under_the_hood_memory.html").read_text(
        encoding="utf-8"
    )
    assert entrypoint_html.count('class="concept-diagram"') >= 2
    assert "Operating system" in entrypoint_html
    assert "Browser host" in entrypoint_html
    assert memory_html.count('class="concept-diagram"') >= 3
    assert "Virtual address space" in memory_html
    assert "Thread 1" in memory_html
    assert "Shared runtime data" in memory_html


def test_session_10_pattern_chapters_include_concept_diagrams() -> None:
    summary = (BOOK / "SUMMARY.md").read_text(encoding="utf-8")
    assert "chapter_9_0_visual_style.md" in summary
    assert "chapter_9_1a_multitier.md" in summary
    assert "bibliography_visual_explanations.md" in summary

    pages = [
        "chapter_9_session_patterns.html",
        "chapter_9_0_visual_style.html",
        "chapter_9_1_app_shape.html",
        "chapter_9_1a_multitier.html",
        "chapter_9_2_authorization.html",
        "chapter_9_3_resilience.html",
        "chapter_9_4_integration.html",
        "chapter_9_5_test_doubles.html",
        "chapter_9_6_composable_rules.html",
        "chapter_9_7_data_paths.html",
        "chapter_9_8_prompting_ai.html",
    ]
    for name in pages:
        html = (BOOK / "html" / name).read_text(encoding="utf-8")
        assert 'class="concept-diagram"' in html, f"{name} missing concept-diagram"
        assert "<figcaption>" in html, f"{name} missing figcaption"

    bib = (BOOK / "html" / "bibliography_visual_explanations.html").read_text(
        encoding="utf-8"
    )
    assert "Paivio" in bib
    assert "Mayer" in bib
    assert "concept-diagram" in (
        BOOK / "chapter_9_0_visual_style.md"
    ).read_text(encoding="utf-8")


def test_core_sessions_include_concept_diagrams() -> None:
    """Sessions 3–7 mental-model chapters (diagram rollout) keep dual coding."""
    pages = [
        "chapter_3_session_control_flow.html",
        "chapter_3_1_control_flow.html",
        "chapter_3_2_loops.html",
        "chapter_3_3_arrays_and_lists.html",
        "chapter_4_5_structs_data_entity.html",
        "chapter_4_6_choosing_construct.html",
        "chapter_5_session_functions_lambdas.html",
        "chapter_5_1_functions_return.html",
        "chapter_5_2_lambdas.html",
        "chapter_5_3_passing_functions.html",
        "chapter_6_session_concurrency.html",
        "chapter_6_1_tasks_await.html",
        "chapter_6_2_shared_state.html",
        "chapter_6_3_atomic_updates.html",
        "chapter_6_4_lambdas_capture.html",
        "chapter_7_session_tests.html",
        "chapter_7_1_first_test.html",
        "chapter_7_2_tdd.html",
        "chapter_7_3_packages_source_roots.html",
    ]
    for name in pages:
        html = (BOOK / "html" / name).read_text(encoding="utf-8")
        assert 'class="concept-diagram"' in html, f"{name} missing concept-diagram"
        assert "<figcaption>" in html, f"{name} missing figcaption"


def test_gui_intro_mermaid_is_rendered_as_div_not_code_fence() -> None:
    gui = (BOOK / "html" / "gui_intro.html").read_text(encoding="utf-8")
    assert 'class="language-mermaid"' not in gui
    assert 'class="mermaid"' in gui
    assert "flowchart TD" in gui
    assert "mermaid.esm.min.mjs" in gui
    assert "Create window and widgets" in gui
