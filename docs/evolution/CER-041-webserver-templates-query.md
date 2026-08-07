# CER-041: Template HTTP with query-string binding

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Scope | `examples/webserver-templates-query/` |
| Extends | [CER-040](CER-040-webserver-templates-logic.md) (if/for templates) |

## Context

CER-039 deferred query-string name binding. This separate example teaches
parsing `?a=1&b=2` on the request line and feeding named params into the
existing template context (with defaults and HTML escape).

## Entries

### 1. Query parse + route binding

- **Pre-behavior:** `Http11` discarded everything after `?`; templates only
  received hard-coded context (CER-039/040).
- **Post-behavior:** `parseQuery` (stdlib `urllib.parse.parse_qsl` → `dict`)
  fills `HttpRequest.query`; `queryGet(key, default)`; `/hello` and `/shop`
  bind `name` / `title` / `vip` / `sale` into templates; port **8103**.
- **Evidence:** `tests/test_query.pys`, `tests/test_webserver_templates_query.py`.

## Trade-offs

- Duplicate keys: last value wins (`dict(parse_qsl(...))`); blank values kept.
- No form POST body parsing (GET query only in this increment).
