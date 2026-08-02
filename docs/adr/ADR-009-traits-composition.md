# ADR-009: Traits as composition (not nominal types)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-008](../evolution/CER-008-traits.md) |
| Source | [`requirements/traits.md`](../../requirements/traits.md) |

## Context

Teaching needs reusable method bodies with explicit host dependencies, without
a second inheritance axis or duck-typed mixins.

## Decision

1. **`trait`** declares always-public methods plus **`requires`** (fields/methods
   the host must supply). No trait fields, no constructor, no instantiation.
2. Classes compose with **`uses`** (after `inherits`, before `implements`).
3. Traits are **not nominal types** — reject in `implements`, as binding types,
   and as `Trait()`.
4. **`this.x`** in a trait method must match `requires` (or another method of
   the same trait).
5. **Collisions**: same method from two used traits → host must override;
   `TraitName.method(this)` selects a side (emitted as mangled helpers).
6. **Emit**: flatten methods into the host class (not Python MI / mixin bases).

## Consequences

- Distinct from `interface` (signatures only, is a type) and `inherits` (single
  superclass).
- IDE: keywords/hover/snippets/go-to on trait names; not in validated types.
- Pedagogy: JIT `J-trait`; example `examples/traits.pys`.

## Rejected alternatives

- Python mixin bases (puts traits in the type/MRO hierarchy).
- Implicit duck-typed mixins without `requires`.
- Trait bounds as types (deferred; open question in requirements §3.6).
