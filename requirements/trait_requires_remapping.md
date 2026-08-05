## PYS Language Specification — Trait Requirement Remapping

**Status:** Implemented — [ADR-009](../docs/adr/ADR-009-traits-composition.md) / [CER-027](../docs/evolution/CER-027-trait-requires-remapping.md).

### 1. Overview

A `uses` clause may optionally remap the names a trait's `requires` items expect onto the actual member names present in the host class. This allows a trait to remain agnostic of any particular host's naming choices, increasing reuse across classes that model the same underlying dependency under different names.

Remapping applies **exclusively to `requires` items** — a trait's own declared methods always keep their own names in every host, unmapped and unaliased. This reflects a deliberate split in what a trait exposes: its **dependency surface** (`requires`, host-specific, remappable) and its **offered surface** (its methods, universal, fixed). Mixing the two would let a trait's public contract shift per host, which defeats the purpose of a trait having a stable surface at all.

### 2. Grammar

```ebnf
(* Amendment to class_decl's uses clause *)
class_decl        = [ top_visibility ] , [ "sealed" ] , "class" , identifier ,
                    [ type_params ] ,
                    [ ( "inherits" | "super" ) , identifier ] ,
                    [ "uses" , trait_use , { "," , trait_use } ] ,
                    [ "implements" , identifier , { "," , identifier } ] ,
                    class_body ;

trait_use         = identifier , [ trait_remap ] ;
trait_remap       = "(" , remap_entry , { "," , remap_entry } , ")" ;
remap_entry       = identifier , ":" , identifier ;
(* Left identifier: the name as declared in the trait's own "requires"
   clause. Right identifier: the host class member that actually
   satisfies it. Order-independent; at most one entry per requirement. *)
```

### 3. Static semantics

1. **Default is exact name matching.** A `trait_use` without `trait_remap` behaves exactly as previously specified — remapping is opt-in and fully backward compatible with existing `uses` declarations.
2. **Resolution order**: for each `requires` item declared by the trait, the compiler first checks whether a `remap_entry` names it. If so, the entry's right-hand identifier is used as the actual host member to validate (same type/signature check as an unmapped `requires`). If not, the existing exact-name rule applies unchanged.
3. **Unknown left-hand identifiers are a compile-time error.** A `remap_entry` whose left-hand name does not correspond to any `requires` item declared by the trait is rejected:
   ```
   Error: Trait 'Printable' declares no requirement named 'label' — did you mean 'name'?
   ```
4. **Missing host member after remapping** produces the same diagnostic category as an unmapped missing requirement, with the mapped name included for clarity:
   ```
   Error: Klant uses Printable but does not provide 'naam' (string, mapped
   from Printable's 'name'), required by trait Printable.
   ```
5. **Remapping never applies to a trait's own method names.** `Printable.print()` remains `print()` in every host regardless of any `trait_remap` present on that host's `uses` clause — there is no syntax by which a host can rename a trait's offered methods. Attempting to write a `remap_entry` whose left-hand identifier matches a trait method name rather than a `requires` item is the same "unknown requirement" error as point 3, since method names are not valid remap targets.
6. **Collision rule (established previously) is unaffected.** If two used traits define methods with the same name, the host class must still supply an explicit disambiguating override — remapping addresses `requires`-level naming differences only, not method-name collisions between traits.

### 4. Examples

**Basic remapping — a single `requires` item:**

```pys
trait Printable {
    requires string name

    string print() {
        return "Item: " + this.name
    }
}

class Klant uses Printable(name: naam) {
    private string naam
    private string email

    Klant(string naam, string email) {
        this.naam = naam
        this.email = email
    }
}
```

`print()` reads `this.name` as written in the trait, but for `Klant` this resolves to `this.naam` at composition time. `Printable` remains reusable for any host, regardless of that host's own field-naming choices — and `print()` itself is still called `print()`, not renamed, on `Klant`.

**Partial remapping — some requirements match by coincidence, others don't:**

```pys
trait Auditable {
    requires string owner
    requires DateTime createdAt

    string auditLine() {
        return this.owner + " @ " + this.createdAt
    }
}

class Invoice uses Auditable(owner: billedTo) {
    private string billedTo
    private DateTime createdAt   # exact match, no remap entry needed

    Invoice(string billedTo, DateTime createdAt) {
        this.billedTo = billedTo
        this.createdAt = createdAt
    }
}
```

`owner` is remapped to `billedTo`; `createdAt` matches exactly and needs no entry. Remapping is per-requirement, not all-or-nothing for the trait.

**Multiple used traits, each remapped independently:**

```pys
trait Printable {
    requires string name
    string print() { return "Item: " + this.name }
}

trait Discountable {
    requires float price
    float discountedPrice(float pct) { return this.price * (1 - pct) }
}

class Product uses Printable(name: title), Discountable(price: unitPrice) {
    private string title
    private float unitPrice

    Product(string title, float unitPrice) {
        this.title = title
        this.unitPrice = unitPrice
    }
}
```

Each `trait_use` in the comma-separated `uses` list carries its own independent `trait_remap` — remapping one trait's requirements has no bearing on another's.

**What remains illegal — attempting to rename an offered method:**

```pys
class Klant uses Printable(print: describe) {   # ERROR
    ...
}
```

```
Error: Trait 'Printable' declares no requirement named 'print' — 'print' is
a method offered by the trait, not a dependency it requires. Trait method
names cannot be remapped.
```

### 5. Rationale summary

| Surface | Remappable? | Reason |
|---|---|---|
| `requires` items | Yes, per-item, via `uses TraitName(traitName: hostName, ...)` | These represent the trait's *dependency* on its host; the host's own naming conventions should not force every trait it uses to share its vocabulary |
| Trait's own methods | No | These represent the trait's *offered contract*; keeping them fixed across every host preserves a single, predictable public surface a caller can rely on regardless of which class composed the trait in |