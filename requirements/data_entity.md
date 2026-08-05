## PYS Language Specification — `data` Types and `entity` Types

> **Absorbed into permanent docs.** Canonical copy (including references [1]–[8]):
> [`docs/DATA_ENTITY.md`](../docs/DATA_ENTITY.md) · decision: [ADR-011](../docs/adr/ADR-011-data-and-entity.md).
> This file is a historical draft only.

### 1. Overview

Two constructs express "bundled data" with opposite equality semantics, deliberately kept separate from `struct`:

- **`data`**: immutable, structural (whole-object) equality — Value Object semantics per Evans (2003). Two instances with identical field values are interchangeable; there is no notion of "which one is the real one." Changing a value produces a different `data` instance, never a mutation of the original.
- **`entity`**: identity-based equality — equality is determined *exclusively* by one or more designated key fields (`identity(...)`), which must be immutable (`fix`). Non-key fields may be mutable. Represents domain entities / database rows: two instances sharing a key are the same logical row even if other fields differ, and two instances with different keys are different rows even if all other fields happen to match.

Neither construct may carry a `uses` clause (traits) — this preserves the "pure data" guarantee already established for `struct`.

### 2. EBNF

```ebnf
(* ------------------------- Data types (Value Objects) ------------------------- *)

data_decl         = [ top_visibility ] , "data" , identifier , data_body ;
(* Structural equality/hashCode/toString auto-generated over ALL
   fields, never overridable. All fields implicitly fix — no "fix"
   keyword needed, analogous to trait members being implicitly public.
   No "inherits", no "uses", no "implements". *)

data_body         = "{" , { data_field_decl } , "}" ;
data_field_decl   = type_name , identifier , [ "=" , expression ] ;

(* ------------------------- Entities ------------------------- *)

entity_decl       = [ top_visibility ] , "entity" , identifier ,
                    [ "inherits" , identifier ] ,
                    [ "identity" , "(" , identifier , { "," , identifier } , ")" ] ,
                    entity_body ;
(* Root entity (no "inherits"): identity(...) is MANDATORY.
   Derived entity ("inherits" present): identity(...) is OPTIONAL.
     - Omitted: equality uses exactly the parent's key fields, unchanged.
     - Present: named fields are APPENDED to the parent's key fields
       (parent fields first, in declared order), forming a composite
       key across the inheritance boundary — models a join-table
       compound primary key (e.g. order_id + line_number).
   Every field named in a derived identity(...) must be declared "fix"
   in THIS entity's own body. Inherited key fields are already
   guaranteed fix by the parent's declaration. *)

entity_body       = "{" , { entity_member } , "}" ;
entity_member     = entity_field_decl | method_decl | constructor_decl ;
entity_field_decl = member_access , [ "fix" ] , type_name , identifier ,
                    [ "=" , expression ] ;
```

### 3. Static semantics

1. **`data` fields** are implicitly `fix`; no explicit constructor is written — a canonical positional constructor `Name(field1, field2, ...)` and a named-argument form `Name(field = expr, ...)` are implicit, matching the existing `struct` constructor convention.
2. **`data` equality**: `equals`/`hashCode`/`toString` are generated over *all* fields, in declaration order, and may not be hand-declared inside `data_body` — a method named `equals`, `hashCode`, or `toString` there is a compile-time error.
3. **`entity` identity fields must be `fix`.** Every identifier listed in `identity(...)` must resolve to a field declared `fix`. Violation: `entity Customer: identity field 'customerId' must be declared fix`. Rationale: a mutable field feeding `hashCode` corrupts hash-based collections if changed post-insertion — structurally prevented rather than merely documented.
4. **`entity` equality/hashCode may not be hand-overridden**, for the same reason as point 2 — an entity's identity guarantee must not be silently widened back to full-field comparison.
5. **Compound keys**: `identity(a, b)` requires equality on *all* named fields, order as declared. No arity limit.
6. **Inheritance chain**: `entity B inherits A` requires `A` to be an `entity`.
   - If `B` omits `identity(...)`, `B`'s equality uses exactly `A`'s key fields.
   - If `B` declares `identity(...)`, its fields are appended after `A`'s key fields (parent-first ordering), forming a composite key spanning the inheritance boundary.
7. **No `uses`**: neither `data` nor `entity` may carry a `uses` clause.
8. **No getters/setters are generated.** PYS has no property/accessor syntax distinct from field access; `member_access` on a field already controls read/write visibility directly (as in `class`), so there is nothing additional to synthesize.

### 4. Examples

**`data` — DDD Value Object, Evans' canonical case:**

```pys
data Money {
    int amountCents
    string currency
}

Money m1 = Money(10000, "USD")
Money m2 = Money(10000, "USD")
# m1 == m2 → true — interchangeable, "which $100 is this" is meaningless

Money m3 = Money(m1.amountCents, "EUR")   # changing currency yields a
                                           # DIFFERENT Money, not an edit
# m1 == m3 → false
```

**`entity` — single key, mutable non-key fields:**

```pys
entity Customer identity(customerId) {
    private fix int customerId
    private string name
    private string email

    Customer(int customerId, string name, string email) {
        this.customerId = customerId
        this.name = name
        this.email = email
    }
}

Customer c1 = Customer(7, "Ana", "ana@x.nl")
Customer c2 = Customer(7, "Ana B.", "anab@x.nl")   # same row, fields updated
# c1 == c2 → true

Customer c3 = Customer(8, "Ana", "ana@x.nl")        # coincidentally identical data
# c1 == c3 → false — different row
```

**`entity` inheritance with composite key extension (join-table pattern):**

```pys
entity Order identity(orderId) {
    private fix int orderId
    private DateTime placedAt
}

# Effective key becomes (orderId, lineNumber) — parent field first.
entity OrderLine inherits Order identity(lineNumber) {
    private fix int lineNumber
    private string productSku
    private int quantity
}

OrderLine l1 = OrderLine(orderId=100, placedAt=t1, lineNumber=1, productSku="SKU-A", quantity=2)
OrderLine l2 = OrderLine(orderId=100, placedAt=t2, lineNumber=1, productSku="SKU-B", quantity=5)
# l1 == l2 → true: (100, 1) matches on both

OrderLine l3 = OrderLine(orderId=100, placedAt=t1, lineNumber=2, productSku="SKU-A", quantity=2)
# l1 == l3 → false: lineNumber differs
```

**`entity` inheritance without key extension (shared key, e.g. `Account`/`User`):**

```pys
entity Account identity(accountId) {
    private fix int accountId
    private DateTime createdAt
}

entity User inherits Account {
    private string username
    private string passwordHash
}

User u1 = User(accountId=42, createdAt=t1, username="remi", passwordHash="a")
User u2 = User(accountId=42, createdAt=t1, username="remi", passwordHash="b")  # password changed
# u1 == u2 → true — same row, identity is accountId alone
```

### 5. Comparison table — full construct family

| Construct | Owns state | Identity | Equality/hashCode/toString | Constructor | Getters/setters | Mutability | Inheritance | Typical use |
|---|---|---|---|---|---|---|---|---|
| `struct` | Yes | No | None generated | Implicit canonical | N/A — fields public | Field-level (`fix` optional per field) | No | Ad-hoc grouped data, no comparison semantics assumed |
| `data` | Yes | No | Structural, all fields, auto-generated, non-overridable | Implicit canonical | N/A — fields implicitly fix, accessed directly | Fully immutable | No | DDD Value Objects (`Money`, `Point`, `Color`) |
| `entity` | Yes | Yes, explicit `identity(...)` | Identity-only (key fields), auto-generated, non-overridable | Explicit, hand-written | N/A — `member_access` on fields covers this | Key fields `fix`; other fields mutable | Yes (`inherits` another `entity`, key extensible) | Database rows, domain entities with a lifecycle |
| `class` | Yes | Implicit (reference) | Reference by default, manually overridable | Explicit, hand-written | N/A — `member_access` on fields covers this | Unrestricted | Yes (single, `inherits`) | General-purpose objects |
| `abstract class` | Yes | Implicit (reference) | — | Explicit, hand-written; may be invoked via `super(...)` | N/A | Unrestricted | Yes (single, enforces override) | Polymorphic variation point (template method) |
| `interface` | No | — | — | None (no instantiation) | — | — | Multiple (`implements`) | Pure contract |
| `trait` | No (borrows host's) | — | — | None (no instantiation) | — | — | Multiple (`uses`), with `requires` | Horizontal behavior reuse across unrelated types |

Note on the "getters/setters" column: PYS has no property/accessor syntax separate from field declaration — `member_access` on a field (`public`/`private`/`protected`/`module`) already governs read/write access directly, so no construct in this family needs to synthesize accessor methods the way Java historically did before `record`.

Below design rationale should be a first page readme entry also reiterated 

## Design Rationale — Why `entity` Is a Language Construct, Not a Framework Concern

### 1. The problem `entity` addresses is real and recurring, not hypothetical

Every mainstream general-purpose language leaves identity-based equality entirely to frameworks. Java has no `entity` keyword — Hibernate/JPA implements identity semantics through the `@Entity`/`@Id` annotation pair, runtime bytecode manipulation, and a convention that `equals`/`hashCode` should be overridden by hand. C# has the equivalent situation with Entity Framework's `[Key]` attribute. Ruby's ActiveRecord infers identity from a database-generated `id` column with no compile-time guarantee at all. In every one of these ecosystems, the *language* provides no static guarantee that an object claiming to represent a persistent row actually behaves consistently as one. The guarantee, where it exists, is bolted on by a library, at runtime, and only insofar as the developer follows the convention correctly.

This is not a minor inconvenience. It produces one of the most well-documented, recurring defect classes in enterprise software built on these frameworks: an entity's `equals`/`hashCode` implemented incorrectly (or left as default reference equality) causes silent failures the moment the entity crosses a boundary the framework does not fully control — placed in a `HashSet` before being persisted (no ID yet, so identity is undefined), compared across two different fetches of "the same" row, or serialized and deserialized across a service boundary. The infamous Hibernate guidance — "never use a mutable field in `equals`, prefer a business key over the surrogate key, and be extremely careful with `hashCode` before the entity is persisted" — exists precisely because the *language* underneath Hibernate offers no way to declare and enforce these constraints. The framework improvises a discipline that the type system does not check.

### 2. Why this matters specifically for PYS as a teaching language

PYS's stated design philosophy elsewhere in this specification (traits' `requires`, interfaces' statelessness, entities' mandatory `identity(...)`) is to take implicit conventions that experienced developers eventually learn the hard way, and make them explicit, compiler-checked declarations instead. The Hibernate `equals`-on-`@Id` problem is arguably the single most transferable example of this philosophy applied to a real, well-known, widely-encountered production issue — most students who go on to build anything with persistence will meet a version of this problem, usually without being told in advance that it exists.

By giving `entity` first-class syntax — `identity(...)` as a mandatory, statically checked clause; identity fields forced to be `fix`; `equals`/`hashCode` generated and *not* overridable — PYS converts a pattern that is normally learned through a production incident (or a code review comment) into something a student can observe and reason about directly in the language. The pedagogical value is not merely "PYS is more convenient than Java here." It is that the construct itself narrates the problem it solves: a student who later encounters Hibernate's actual guidance documents will recognize every constraint PYS enforces at compile time as the exact same constraint Hibernate's documentation *asks developers to remember by discipline*. The comparison is the lesson.

### 3. Why this is legitimate for a general-purpose language, not scope creep into a DSL

The objection worth pre-empting: database interaction is a specific concern, and one might argue that baking `identity`/entity semantics into a general-purpose language oversteps into what should be an external library's responsibility (as every other mainstream language treats it). Two points justify the opposite conclusion for PYS specifically:

First, the *problem* — "a bundle of data that has an identity distinct from its current field values" — is not actually database-specific. It is the general Entity pattern (Evans, 2003) as opposed to the Value Object pattern, and it recurs anywhere an object needs to be tracked as "the same thing" across mutation, independent of storage technology: session state, in-memory caches, message correlation, domain models with no persistence layer at all. The database row is the most common and most pedagogically legible instance of the pattern, not its exclusive domain. Framing `entity` around "identity vs. value equality" rather than "database row" keeps it a general-purpose language feature that happens to map cleanly onto persistence use cases, rather than a persistence feature masquerading as a language construct.

Second, PYS's explicit pedagogical mandate is to make implicit, framework-improvised conventions visible and checkable wherever doing so teaches a transferable lesson at low added complexity. The same argument that justified `requires` in traits (making a trait's dependency on its host explicit rather than duck-typed) and `identity(...)` field immutability (making the mutable-hashCode footgun structurally impossible rather than a warning in documentation) applies here without modification. A general-purpose language does not forfeit its right to solve a well-understood, high-frequency defect class at the type level simply because other general-purpose languages chose not to. That choice, in Java's and C#'s case, was a historical accident of when persistence frameworks matured relative to the language (JPA predates and shaped `record`'s design goals, which were explicitly *not* aimed at entities) — not a principled argument that the language layer is the wrong place for it.

### 4. Summary for requirements documentation

- **Problem statement**: identity-based equality is a recurring, well-documented source of defects in production systems (Hibernate `equals`/`hashCode` misuse being the canonical example), and no mainstream general-purpose language provides compile-time guarantees for it — the responsibility is deferred entirely to frameworks, which can only enforce discipline through documentation and convention, not through the type system.
- **PYS's response**: `entity` makes the Entity/Value Object distinction (Evans, 2003) a first-class, statically checked language construct — `identity(...)` is mandatory and explicit, identity fields are compiler-enforced immutable, and generated equality cannot be silently widened by hand-written overrides.
- **Justification for a general-purpose language**: the underlying pattern (identity vs. value semantics) is general, not persistence-specific; database mapping is its most common but not its only application.
- **Didactic payoff**: students encounter the safeguard and the historical problem it solves in the same construct, giving the lesson built-in transferability to any framework-based environment (JPA, EF Core, ActiveRecord) they subsequently work in.

**Java (JPA/Hibernate) — the problem**

```java
@Entity
public class Customer {
    @Id
    @GeneratedValue
    private Long id;          // null until persist() assigns it
    private String name;

    // Default equals() = reference equality — most teams override it.
    // Common "fix" that is itself the bug:
    @Override
    public boolean equals(Object o) {
        if (!(o instanceof Customer)) return false;
        return id.equals(((Customer) o).id);   // NPE if id is still null!
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);   // hashCode changes once id is assigned
    }
}
```

```java
Customer c = new Customer("Ana");
Set<Customer> seen = new HashSet<>();
seen.add(c);                // stored using hashCode() while id == null
em.persist(c);               // id is now assigned by the database
seen.contains(c);            // → often FALSE: hashCode changed after insertion,
                              //   c is now in the wrong hash bucket
```

**Problem, pointed out**: nothing in Java's type system prevents `equals`/`hashCode` from depending on a field (`id`) that is null at construction time and mutates later. The bug only manifests once an instance crosses a hash-based collection boundary before/after persistence — invisible in a code review, invisible at compile time.

---

**C# (EF Core) — the same problem**

```csharp
public class Customer
{
    public int Id { get; set; }      // 0 (default) until SaveChanges()
    public string Name { get; set; }

    public override bool Equals(object obj) =>
        obj is Customer c && Id == c.Id;   // 0 == 0 for ALL unsaved customers!

    public override int GetHashCode() => Id.GetHashCode();
}
```

```csharp
var c1 = new Customer { Name = "Ana" };
var c2 = new Customer { Name = "Ben" };
c1.Equals(c2);   // → TRUE before SaveChanges(): both Id == 0
```

**Problem, pointed out**: `Id` is a plain mutable auto-property. Nothing stops it from being used in `Equals`/`GetHashCode` while still holding its default value, and nothing stops a developer from also mutating `Id` later by hand — both are silent, compiler-accepted mistakes.

---

**PYS — the same pattern, made structurally impossible**

```pys
entity Customer identity(customerId) {
    private fix int customerId
    private string name

    Customer(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}
```

```pys
Customer c1 = Customer(1, "Ana")
Customer c2 = Customer(1, "Ana B.")
# c1 == c2 → true (same customerId), auto-generated, cannot be overridden
```

**What is structurally prevented, compared to the two examples above**:
1. `identity(customerId)` requires `customerId` to be declared `fix` — a compile error if it is not, so the field used for equality can never be reassigned after construction (rules out the C# `Equals`-mutation risk).
2. There is no default-zero/null identity value to accidentally construct — `customerId` must be supplied at construction, so two "not yet real" instances can never coincidentally compare equal the way `c1.Equals(c2)` did in C#.
3. `equals`/`hashCode` are generated directly from `identity(...)` and a hand-written `equals` or `hashCode` inside `entity_body` is a compile-time error — the exact "well-intentioned override that introduces the null-pointer bug" seen in the Java example cannot be written at all.

**Documented real-world cases (with sources)**

1. **HashSet lookup failure after `persist()`** — Vlad Mihalcea documents a reproducible case where Hibernate throws an AssertionError because the entity is not found after being persisted: when first stored in a Set, the identifier was still null; after persisting, it was assigned an auto-generated value, so the hashCode differs and the object can no longer be found in the Set. (vladmihalcea.com, "How to implement equals and hashCode using the JPA entity identifier")

2. **Silent data corruption in production** — a Quarkus/Panache practitioner report explicitly describes a production incident: a Set-based guard allowed duplicates because equality was based on object identity — two instances representing the same database row were "different" in Java, which is not a loud failure but silent data corruption. (the-main-thread.com, "Stop Breaking HashSet: equals() and hashCode() for JPA in Quarkus", 2026)

3. **Proxy vs. non-proxy inconsistency** — a JPA Buddy analysis shows that even the "correct" ID-based `equals`/`hashCode` implementation fails once a proxy object and a non-proxy object referring to the same database record are placed together in a HashSet — the size of the HashSet should be 1, but Hibernate's proxy mechanism silently undermines this. (jpa-buddy.com)

4. **Lombok `@Data` on JPA entities: cascading bugs** — a practical guide documents that Lombok's @Data annotation generates equals/hashCode/toString over all fields including lazy-loaded relations, which causes a LazyInitializationException outside an active transaction, and leads to a stack overflow in circular entity relationships. (Medium, "Understanding and Resolving Lombok @Data Pitfalls in JPA/Hibernate Entities", 2023)

**Addition to the design philosophy**

These four cases share exactly the same underlying pattern that PYS's `entity` construct structurally prevents:

| Documented problem | Root cause (language provides no guarantee) | PYS prevention |
|---|---|---|
| HashSet lookup fails after persist (Mihalcea) | `id` is null/mutable before and after assignment; nothing forbids using it in `hashCode` | `identity(...)` field is compiler-enforced `fix`; no construction without a value is possible |
| Silent data corruption in production (the-main-thread) | Default reference equality gets "fixed" with a manual, error-prone override | Equality is auto-generated; a hand-written override of `equals`/`hashCode` is a compile error |
| Proxy vs. non-proxy inconsistency (jpa-buddy) | Equality logic depends on *how* the object was loaded, not solely on its key | No proxy concept needed — `identity(...)` is the sole source of equality, regardless of how/when the object was created |
| Lombok `@Data` on entities (Medium) | One generic "generate over all fields" mechanism gets misapplied to both Value Objects and Entities, with no linguistic distinction | `data` and `entity` are *separate* constructs with *separate* generation rules — the mistake is impossible to make by construction, since you cannot accidentally apply "all-fields" equality to an entity |

**Key point for requirements/teacher docs**: these are not edge cases or theoretical concerns — they are production incidents actively documented and discussed by the Hibernate community to this day (source 2 dates from 2026). This underscores that the problem has not been solved by decades of framework maturity, but keeps recurring structurally as long as the language itself provides no guarantee. PYS's `entity`/`data` separation demonstrates to students that a language-level solution eliminates this entire problem space by design, rather than managing it through documentation and discipline.

[1] V. Mihalcea, "How to implement equals and hashCode using the JPA entity identifier (Primary Key)," vladmihalcea.com. [Online]. Available: https://vladmihalcea.com/how-to-implement-equals-and-hashcode-using-the-jpa-entity-identifier/. [Accessed: Aug. 3, 2026].

[2] V. Mihalcea, "The best way to implement equals, hashCode, and toString with JPA and Hibernate," vladmihalcea.com, Nov. 19, 2020. [Online]. Available: https://vladmihalcea.com/the-best-way-to-implement-equals-hashcode-and-tostring-with-jpa-and-hibernate/. [Accessed: Aug. 3, 2026].

[3] "Stop Breaking HashSet: equals() and hashCode() for JPA in Quarkus," the-main-thread.com, Mar. 6, 2026. [Online]. Available: https://www.the-main-thread.com/p/equals-hashcode-jpa-quarkus-panache-equalsverifier. [Accessed: Aug. 3, 2026].

[4] "(Hopefully) the final article about equals and hashCode for JPA entities with DB-generated IDs," jpa-buddy.com. [Online]. Available: https://jpa-buddy.com/blog/hopefully-the-final-article-about-equals-and-hashcode-for-jpa-entities-with-db-generated-ids/. [Accessed: Aug. 3, 2026].

[5] J. B. Friedli, "Lombok @Data and JPA Entities: Deep Dive," Medium, Apr. 20, 2025. [Online]. Available: https://medium.com/@jonas.friedli/lombok-data-and-jpa-entities-deep-dive-d955de9647e3. [Accessed: Aug. 3, 2026].

[6] "Understanding and Resolving Lombok @Data Pitfalls in JPA/Hibernate Entities," Medium, Dec. 15, 2023. [Online]. Available: https://medium.com/@devchaghtai/understanding-and-resolving-lombok-data-pitfalls-in-jpa-hibernate-entities-ebc76000da18. [Accessed: Aug. 3, 2026].

[7] E. Evans, Domain-Driven Design: Tackling Complexity in the Heart of Software. Boston, MA, USA: Addison-Wesley, 2003.

[8] G. Booch, Object-Oriented Analysis and Design with Applications, 2nd ed. Redwood City, CA, USA: Benjamin/Cummings, 1994.