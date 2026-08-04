# CER-020: Source-root package identity

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Scope | `transpiler/project_manifest.py`, `imports.ImportResolver._same_package`, package import diagnostics; IDE 0.0.65 |
| ADR | [ADR-017](../adr/ADR-017-source-roots-same-package-tests.md) |
| Extension | 0.0.65 (`pys.package-mismatch` quick fix → move file) |

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
  the educational “Did you mean …?” diagnostic (requirements §4) with
  `code=pys.package-mismatch`, `suggested_fix` path, and IDE quick fix to
  move the file. Find Usages indexes package peers across roots
  (`package_peer_files`). Bare module imports (e.g. `from config`) resolve
  among same-package peers under other source roots. Teaching sample:
  `examples/source_roots/`; webserver uses `src/` + `tests/`.
- **Tests:** `tests/test_source_roots_package.py`
