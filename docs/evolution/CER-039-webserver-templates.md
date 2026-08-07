# CER-039: Template HTTP example

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Scope | `examples/webserver-templates/` |

## Context

After static files, students need server-side HTML with placeholders — a
separate folder so the templating layer is obvious.

## Entries

### 1. `{{key}}` engine + containment

- **Post-behavior:** `TemplateEngine.render` replaces `{{key}}` / `{{ key }}`,
  HTML-escapes values, blocks path traversal; routes `/hello` and `/greet`;
  port 8101.
- **Evidence:** `tests/test_webserver_templates.py`.

## Trade-offs

- No loops/conditionals yet (intentional teaching increment) — see
  [`examples/webserver-templates-logic/`](../../examples/webserver-templates-logic/)
  / [CER-040](CER-040-webserver-templates-logic.md) for `{% if %}` / `{% for %}`.
- Query-string name binding deferred — see
  [`examples/webserver-templates-query/`](../../examples/webserver-templates-query/)
  / [CER-041](CER-041-webserver-templates-query.md).
