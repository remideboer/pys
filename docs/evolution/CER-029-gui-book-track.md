# CER-029: Procedural Tkinter book track + temperature examples

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-06 |
| Scope | `book/gui_*.md`; `book/SUMMARY.md`; `book/html/`; `examples/gui/temperature_tk/`; `examples/gui/temperature_ttkbootstrap/` |
| Architecture | (teaching track — no new language ADR) |

## Context

Draft chapters taught procedural Tkinter and ttkbootstrap, but were not wired
into `SUMMARY.md`, used inventable APIs (`isNumeric` / `toFloat`), and had no
runnable example silos under `examples/gui/`.

## Entry 1 — book placement and compiling fences

### Pre-behavior

Seven `book/gui_*.md` files existed off-summary; fences used dotted types
(`tk.Tk window`), mutated non-`shared` captures, and non-existent parse helpers.

### Why it hurt

Students could not navigate the track; copy-paste examples failed to transpile.

### Post-behavior

§7 sits after Session 4 (lambdas). Fences use bare widget types, `shared`
for assigned captures, `parseFloat` inside `result`, and
`pys.deps` for ttkbootstrap. Heading numbers for later sessions shift by one.

### Evidence

Fence transpile via `.perfcheck/check_gui_fences.py` (tk fences always; ttkb
fences with `PYS_WORKSPACE_ROOT` = `examples/gui/temperature_ttkbootstrap`).
`python book/build_html.py` regenerates `book/html/`.

## Entry 2 — temperature converter example silos

### Pre-behavior

No Celsius→Fahrenheit twin under `examples/gui/` for the book project.

### Why it hurt

Teaching chapters pointed at imaginary projects; ttkbootstrap needed a locked
deps silo (ADR-001 / CER-001).

### Post-behavior

- `examples/gui/temperature_tk/` — stdlib Tkinter only
- `examples/gui/temperature_ttkbootstrap/` — local `pys.deps` + `pys.lock`

### Evidence

`python -m transpiler transpile` / analyze of each `main.pys` with
`PYS_WORKSPACE_ROOT` set to that silo directory.

## Entry 3 — Mermaid diagrams in static HTML

### Pre-behavior

````mermaid` fences became `<pre><code class="language-mermaid">` with
HTML-escaped arrows (`--&gt;`); no Mermaid runtime was loaded.

### Why it hurt

`gui_intro` showed a dead code block instead of the event-loop flowchart.

### Post-behavior

`book/build_html.py` promotes those fences to `<div class="mermaid">`
(with `html.unescape`), injects Mermaid 11 ESM only on pages that need it,
and styles the container. Pages without diagrams stay script-free.

### Evidence

`tests/test_book_links.py::test_gui_intro_mermaid_is_rendered_as_div_not_code_fence`

## Trade-offs

- Bidirectional F↔C remains a book exercise, not shipped source.
- Procedural style after OO sessions on purpose; class GUIs stay in Pokemon/shop.
- Mermaid loads from jsDelivr (offline HTML viewers without network see source text only).
