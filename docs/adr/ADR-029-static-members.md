# ADR-029: Class `static` members

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Code detail | [CER-047](../evolution/CER-047-static-members.md) |
| Source | `requirements/static.md` |

## Context

Students need class-wide storage and helpers (shared counters, factories,
`Math`-style APIs). C#, Java, and JavaScript all use the keyword **`static`**
for this. Renaming would break three-way transfer; the “opaque English word”
problem is solved by teaching against the process memory model (class-wide vs
per-instance), not by inventing a new label.

## Decision

1. Keep the keyword **`static`** (no rename).
2. Grammar: optional `static` after `member_access` on const / fix / mutable
   fields and on concrete methods (before extension modifiers).
3. **Static field:** one shared storage cell for the class; not per instance.
4. **Static method:** no instance — `this` / `self` in the body is an Error
   with a tip pointing at the memory chapter (“Processes, threads, and
   memory” / class-wide vs per-instance).
5. **`static` + `open` / `override` / `override closed`:** Error — polymorphism
   needs an instance to dispatch.
6. **`static const`:** allowed; redundant with `const`’s class-wide meaning
   (same documentation posture as standalone `closed`).
7. **Not on** constructors, abstract methods, struct/data/entity fields, or
   trait methods in this decision (class members only).

## Consequences

- Emit Python `@staticmethod` (no `self`) and class attributes for static
  fields.
- Book memory chapter must name `static` and show class-wide vs instance.
- IDE: keyword highlight + hover; diagnostics with tips.

## Rejected alternatives

- Renaming to `shared` / `class` / `own` (weaker transfer than `static`).
- Implicit-virtual static override (contradicts ADR-028).
