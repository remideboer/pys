# CER-049: Pattern teaching examples

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Commits | (patterns tree; see git history) |
| Scope | `examples/patterns/**`; `tests/test_patterns.py` |

## Context

Students need runnable, **pure OO** references for classic and common patterns,
aligned with PYS features and the OO layered Cursor rule — not procedural
`dict`/`object` sketches.

## Entries

### 1. Twenty-three GoF demos

**Pre-behavior:** No patterns corpus.

**Post-behavior:** One `.pys` per GoF pattern under
`examples/patterns/design/{creational,structural,behavioral}/` (originally
`examples/design_patterns/…`); companion markdown; isolated `pys.toml`;
transpile gate. Nominal interface returns — see CER-010 §2.

**Evidence:** `python -m pytest -q tests/test_patterns.py`.

### 2. Companion markdown per runnable pattern

**Post-behavior:** `[pattern-name].md` beside each `.pys` (intent, UML, use cases,
run line). Root README indexes Code + Notes.

### 3. Concurrency patterns (Wikipedia Examples, option B)

**Post-behavior:** Four runnable demos under `concurrency/`; out-of-language
table for Barrier / monitor / TLS / etc.

### 4. Dependency Injection (general)

**Post-behavior:** `general/dependency_injection.pys`; Singleton cross-links.

### 5. Tree rename + categories (2026-08-08)

**Pre-behavior:** Folder named `examples/design_patterns/` with GoF categories at
the root plus `concurrency/` / `general/`.

**Post-behavior:** Renamed to **`examples/patterns/`**. GoF lives under
`design/`. Added `authentication/` (runnable), plus stub-only
`architectural/`, `messaging/`, `reactive/`. Gate: `tests/test_patterns.py`.

### 6. Authentication patterns

**Post-behavior:** Four pure-PYS demos — session-based, token-based (opaque;
JWT shop linked), API key, HTTP Basic — with companion `.md`. Stubs:
`oauth2.md`, `mtls.md`.

**Evidence:** `tests/test_patterns.py` asserts four `authentication/*.pys`.

### 7. Architectural / messaging / reactive demos

**Pre-behavior:** Markdown stubs only.

**Post-behavior:** Runnable OO demos for MVC, MVP, MVVM, hexagonal, layered,
event-driven, publish–subscribe, CQRS, and a teaching reactive push-stream
(honest note: not ReactiveX). OAuth2 / mTLS remain stubs (need IdP / TLS).

**Evidence:** `tests/test_patterns.py` folder counts; companion `.md` files.

## Trade-offs

- One file per runnable pattern for teaching density.
- Book chapters for patterns deferred.
- Stubs only where language/platform blocks honesty (OAuth2, mTLS).
- Concurrency stays inside ADR-013 / CONCURRENCY.md.
