# CER-024: Published book link rewriting

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Commits | (book navigation/link repair increment) |
| Scope | `book/build_html.py`; generated `book/html`; book Previous/Next links |
| ADRs | — |

## Context

The Markdown book links to repository docs/examples with `../…` paths. The
GitHub Pages workflow publishes only `book/html`, so those relative links left
the `/pys/` site and returned 404. `SUMMARY.md` was also rewritten as
`SUMMARY.html` because generic `.md` handling ran before its special case.

### Pre-behavior

- Published repository links such as `../docs/LANGUAGE.md` were broken.
- “Back to Summary” targeted missing `SUMMARY.html`.
- Sequential chapter links routed through session overview pages.

### Post-behavior

- Repository files/directories become GitHub `blob/main` / `tree/main` URLs.
- `SUMMARY.md` becomes generated `index.html`.
- Sequential Previous/Next links skip session overview pages and proceed
  directly between lesson chapters.
- The rebuilt HTML has zero broken local links/anchors.
- `import markdown` is **lazy** (only when converting pages). Loading
  `build_html` for `md_href_to_html` tests does not require the package, so
  the extension CI `pytest` job stays free of a book-build-only dependency.

### Evidence

- `tests/test_book_links.py`
- Generated-HTML link/anchor audit: `BROKEN_HTML=0`
