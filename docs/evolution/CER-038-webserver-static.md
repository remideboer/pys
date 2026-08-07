# CER-038: Static-file HTTP example

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Scope | `examples/webserver-static/` |

## Context

After the REST shop progression, students need a server that maps URLs to
files under a www root (no app JSON).

## Entries

### 1. Contained static root

- **Post-behavior:** Slim HTTP/1.1; `StaticFiles.resolve` blocks `..`; MIME map;
  port 8100; `www/` demo pages; resolve tests via `PYS_STATIC_WWW`.
- **Evidence:** `tests/test_webserver_static.py`.

## Trade-offs

- Binary via latin-1 roundtrip (teaching-scale files).
