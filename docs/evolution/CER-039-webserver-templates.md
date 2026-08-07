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

- No loops/conditionals yet (intentional teaching increment).
- Query-string name binding deferred.
