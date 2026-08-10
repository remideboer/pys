# CER-027: Trait `requires` remapping

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-05 (amended 2026-08-10: interpolation emit) |
| Scope | `ast_nodes.py` (`TraitUse`), `parse.py`, `sem.py`, `emit/python.py`, `emit/javascript.py`; EBNF/railroad/LANGUAGE; `examples/traits.pys`; `tests/test_traits.py`; book / JIT / snippets |
| ADRs | [ADR-009](../adr/ADR-009-traits-composition.md) |
| Requirement | [`requirements/trait_requires_remapping.md`](../../requirements/trait_requires_remapping.md) |

## Context

Hosts often name fields differently from a trait’s `requires` vocabulary.
Without remapping, every host had to rename members to match the trait, which
hurt reuse. Remapping is opt-in and applies only to the dependency surface.

---

## 1. Parse / AST

**Symbols:** `TraitUse`; `ClassDef.uses: list[TraitUse]`; `_parse_trait_use`.

### Pre-behavior

`uses` was a bare identifier list — `uses Printable(name: title)` was a parse
error.

### Post-behavior

`uses TraitName` or `uses TraitName(req: host, …)`. Empty `()` rejected.
Each class `uses` entry is a `TraitUse` with optional remaps.

### Evidence

`tests/test_traits.py` remap happy path + parse/sem errors.

---

## 2. Sem satisfaction via mapped names

**Symbols:** `_check_traits`.

### Pre-behavior

Exact-name match only against host fields/methods.

### Post-behavior

For each requirement, resolve host member = remap RH if present else requires
name. Unknown LH / method LH / duplicate LH → `pys.trait-remap`. Missing RH →
`pys.trait-requires` including “mapped from Trait's 'x'” when remapped.
Trait-body `this.x ⊆ requires` check unchanged (trait vocabulary).

### Evidence

Parametrized remap error cases in `tests/test_traits.py`.

---

## 3. Emit rewrite

**Symbols:** `_trait_requires_remap`; `Member` emit; interpolated-string emit;
flattened / mangled trait methods.

### Pre-behavior

Flattened trait methods emitted `self.<requiresName>` literally.

### Post-behavior

While emitting a trait method for a host, `self.<req>` becomes `self.<host>`
for remapped requirements (fields and method calls). The same rewrite applies
inside interpolated string holes (`{this.x}` → `self.<host>` after `this`→`self`;
JS keeps `this.<host>`). Trait method *names* remain unmapped. Collision
helpers unchanged.

### Evidence

`test_requires_remap_runs_and_rewrites_emit`;
`test_multi_requires_remap_in_interpolated_string`; example `CatalogItem` /
`Point` + `CoordPrinter` sections.

## 4. Interpolation hole (amend 2026-08-10)

### Pre-behavior

`Member` emit remapped requires, but `InterpolatedString` only did a textual
`this`→`self` replace — so `print("{this.x}")` under `uses T(x: getalA)` still
emitted `self.x` and failed at runtime. Multiple remaps were already legal in
the grammar; the hole made multi-remap samples look broken.

### Why it hurt

Teaching samples like `Printer(x: getalA, y: getalB)` with interpolated
`{this.x} {this.y}` crashed; students thought only one remap worked.

### Post-behavior

Python `_apply_trait_requires_remap_text` (and the JS `this.<req>` rewrite)
runs on interpolated text while `_trait_requires_remap` is active. Legacy
return special-case that skipped f-string rewrite was removed so returns use
the same path.

### Evidence

`test_multi_requires_remap_in_interpolated_string` (emit asserts + run).

## Trade-offs

- Remapping is host-side only; the trait source still writes `this.name`.
- No syntax to rename offered trait methods (deliberate).
- Remap RHS stays a host **member name**, not an arbitrary expression.