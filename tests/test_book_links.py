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

    for name in ("basics_outcomes.md", "chapter_8_4.md"):
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
    under_the_hood = summary.index("# 10. Under the hood")
    assert summary.index("# 9. Session 7") < under_the_hood
    assert under_the_hood < summary.index("# 11. Exercises")

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
