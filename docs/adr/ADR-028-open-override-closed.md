# ADR-028: Extension points — `open`, `override`, `closed`

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Code detail | [CER-046](../evolution/CER-046-open-override-closed.md) |
| Source | `requirements/open_override_closed.md` |
| Amends | [ADR-010](ADR-010-abstract-classes.md) (`sealed` → `closed`) |

## Context

Class-level `sealed` blocked inheritance, but methods were freely redefinable
(Python virtual default). That couples visibility with overridability and allows
accidental overrides. Bloch’s Effective Java Item 19 argues for designing for
inheritance or prohibiting it; C#’s `virtual`/`override` still allows silent
hiding.

## Decision

1. **Class header:** `[closed | abstract]` mutually exclusive. Classes remain
   inheritable by default; only `closed class` forbids subclasses. `sealed` is
   removed (mechanical rename to `closed`).
2. **Methods closed by default.** Extension modifiers:
   - none / standalone `closed` → not overridable
   - `open` → subclass may `override`
   - `override` → plugs into ancestor `open` or `abstract` (or implicit root);
     remains open for further override
   - `override closed` → plugs in and seals the chain
3. **Abstract methods** are implicitly open sockets; redundant `open` allowed;
   `closed` on abstract is an error.
4. **Errors** for: `override` with no open/abstract ancestor; private +
   open/override/closed; `open` on a method of a `closed class`; same-name
   subclass method without `override`.
5. **Implicit root** (not nameable/constructible): conceptual
   `open toString` / `equals` / `hashCode`. Semantic attachment only — no
   synthetic Python base. `data`/`entity` synthesized equality counts as
   compiler `override`s; user may not re-declare those (ADR-011).

## Consequences

- Every intentional override site must mark base `open` and child `override`.
- Teaching book §5.2 replaces “free bump replace” with the open/override model.
- OCP vocabulary (`open`/`closed`) appears in source at class and method grain.

## Rejected alternatives

- Java implicit-virtual default.
- C# `virtual`/`sealed override` pair (two words, silent hide risk).
- Reusing `sealed` at method level (`closed` keeps one meaning: end of the line).
