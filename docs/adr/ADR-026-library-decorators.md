# ADR-026: Library decorator application

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Commits | (same change set as CER-043) |

## Context

PYS historically avoided `@` in source so designers would invent real language
constructs instead of papering over gaps (`@alias`, Lombok-style `@Data`).
That rule was written as an absolute ban and blocked **library** APIs that are
decorator-shaped (FastAPI route registration, pytest marks, …). Field research
for third-party compatibility requires applying those callables from `.pys`.

## Decision

1. **Allowed:** zero or more `@expr` lines immediately above a `function`,
   `class`, or class/entity method. `expr` is a normal unary/postfix/call
   expression (e.g. `@app.get("/health")`, `@mark`). Stacked decorators are
   applied top-to-bottom as in Python. Emit writes `@…` lines before `def` /
   `class` in the Python backend.
2. **Forbidden as language design:** using `@` to invent a missing PYS feature
   (F-003 enum aliases stay real syntax later — not `@alias`). Prefer keywords /
   forms (`data`, `abstract`, …). Emit-only `@abstractmethod` for `abstract`
   methods remains an implementation detail, not a user-written decorator.
3. **Not allowed targets:** fields, bare statements, struct/data/entity type
   headers (methods on classes/entities only for members).

## Consequences

- LANGUAGE / EBNF / railroad / book document the allowed/forbidden table.
- ADR-006 / ADR-010 / ADR-011 “no `@` in source” wording is amended to this
  decision.
- Project-memory anti-`@` bullet matches: no decorator surface for missing
  constructs; library application is allowed.

## Rejected alternatives

- Keeping absolute ban and writing FastAPI only in `.py` sidecars — hides whether
  PYS can consume decorator-shaped libraries.
- A new keyword instead of `@` — breaks familiarity with library docs students
  read (FastAPI tutorial).
