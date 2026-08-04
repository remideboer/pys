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
