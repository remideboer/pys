# ADR-009: Traits as composition (not nominal types)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-008](../evolution/CER-008-traits.md) |
| Permanent | This ADR (incl. Schärli reference); LANGUAGE §Traits; book `chapter_4_4` |
| Draft origin | `requirements/traits.md` (temporary; do not treat as canonical) |

## Context

Teaching needs reusable method bodies with explicit host dependencies, without
a second inheritance axis or duck-typed mixins. PYS traits follow the classical
composition model (Schärli et al., 2003): a trait may declare members it does
not implement (`requires` ≈ excluded / required methods) and composition
conflicts are resolved by the programmer, not by silent precedence.

`requires` is the didactic device that separates PYS traits from duck-typed
mixins: every dependency on the host is declared next to the trait’s own
methods, so the contract-plus-implementation nature is visible in source.

## Decision

1. **`trait`** declares always-public methods plus **`requires`** (fields/methods
   the host must supply). No trait fields, no constructor, no instantiation.
2. Classes compose with **`uses`** (after `inherits`, before `implements`).
3. Traits are **not nominal types** — reject in `implements`, as binding types,
   and as `Trait()`.
4. **`this.x`** in a trait method must match `requires` (or another method of
   the same trait).
5. **Requires remapping (opt-in):** `uses Trait(req: hostMember, …)` maps a
   trait `requires` name onto a host member for satisfaction and emit rewrite.
   Unmapped requirements keep exact-name matching. Remapping never applies to
   the trait’s own method names (offered contract stays fixed per host).
   See [CER-027](../evolution/CER-027-trait-requires-remapping.md).
6. **Collisions**: same method from two used traits → host must override;
   `TraitName.method(this)` selects a side (emitted as mangled helpers).
7. **Composition order independence:** `uses A, B` and `uses B, A` are
   equivalent when there is no collision (commutative / associative composition).
8. **Emit**: flatten methods into the host class (not Python MI / mixin bases);
   rewrite `self.<requires>` to the remapped host name when applicable.

## Consequences

- Distinct from `interface` (signatures only, is a type) and `inherits` (single
  superclass).
- IDE: keywords/hover/snippets/go-to on trait names; not in validated types.
- Pedagogy: JIT `J-trait`; example `examples/traits.pys`.

## Rejected alternatives

- Python mixin bases (puts traits in the type/MRO hierarchy).
- Implicit duck-typed mixins without `requires`.
- Remapping trait **method** names (would make the offered surface host-dependent).
- Trait bounds as types (deferred; open question in requirements §3.6).

## References

- N. Schärli, S. Ducasse, O. Nierstrasz, and A. P. Black, “Traits: Composable
  Units of Behaviour,” in *ECOOP 2003*, LNCS 2743, Springer, 2003.
