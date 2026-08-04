# CER-020: Source-root package identity

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Scope | `transpiler/project_manifest.py`, `imports.ImportResolver._same_package`, package import diagnostics |
| ADR | [ADR-017](../adr/ADR-017-source-roots-same-package-tests.md) |

## Context

`package` visibility meant “same filesystem folder,” which blocked
production-like `src/` + `tests/` trees (surfaced by `examples/webserver/`).

## Entries

### Package identity via `pys.toml` `[source_roots]`

- **Pre-behavior:** `_same_package` compared `Path.parent` only.
- **Why it hurt:** Tests could not share `package` with production without
  co-locating files or widening to `public`.
- **Post-behavior:** With `[source_roots]`, package id is the directory path
  relative to the containing root; mirrored paths across roots match. Without
  a manifest, same-folder legacy remains. Mismatched package imports append
  the educational “Did you mean …?” diagnostic (requirements §4).
- **Tests:** `tests/test_source_roots_package.py`
