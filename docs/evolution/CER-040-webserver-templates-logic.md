# CER-040: Template HTTP with if/for

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Scope | `examples/webserver-templates-logic/` |
| Extends | [CER-039](CER-039-webserver-templates.md) (placeholders only) |

## Context

CER-039 deferred loops/conditionals. This separate example teaches
`{% if %}` / `{% else %}` / `{% endif %}` and `{% for %}` / `{% endfor %}`
without rewriting the placeholder-only server.

## Entries

### 1. Control-flow template engine

- **Pre-behavior:** Only `{{ key }}` substitution (CER-039).
- **Post-behavior:** Nested-aware `if`/`for` blocks, dotted `{{ p.name }}`,
  HTML escape, path containment; demo `/shop` and `/empty` on port **8102**.
- **Evidence:** `tests/test_logic.pys`, `tests/test_webserver_templates_logic.py`.

## Trade-offs

- No `{% elif %}`; truthiness is Python-ish (empty list/string false).
- Template tag characters built via `chr(123/125)` so PYS emit does not treat
  `{{` in engine source as format strings.
