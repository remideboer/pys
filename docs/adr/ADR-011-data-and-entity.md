# ADR-011: `data` value objects and `entity` identity types

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-011](../evolution/CER-011-data-and-entity.md) |
| Permanent | [`docs/DATA_ENTITY.md`](../DATA_ENTITY.md) (full rationale + references) |
| Draft origin | `requirements/data_entity.md` (temporary; do not treat as canonical) |

## Context

Teaching (and production) needs a clear split between **Value Objects**
(structural equality, immutable) and **Entities** (identity equality via
immutable keys) — Evans (2003). Mainstream languages defer this to frameworks
(JPA `@Id`, EF `[Key]`, ActiveRecord), leaving `equals`/`hashCode` footguns
undocumented at the type level. Documented production defects (HashSet lookup
after `persist`, Lombok `@Data` on entities, proxy vs non-proxy inequality)
recur precisely because the *language* offers no compile-time guarantee.

`struct` remains an identity-free bag without a generated VO/Entity contract
([ADR-005](ADR-005-structs-as-value-types.md)). Full rationale, Java/C#
anti-examples, production cases, and bibliographic references live in
[`docs/DATA_ENTITY.md`](../DATA_ENTITY.md).

## Decision

1. **`data`**: fields only; implicitly `fix` + public; implicit positional /
   named ctor; copy on assign/call/return; generated `==` / hash / string form
   over **all** fields; no `inherits` / `uses` / `implements` / hand equals.
2. **`entity`**: explicit ctor; optional `member_access` on fields/methods
   (omit ⇒ `module`); root requires
   `identity(...)`; identity fields must be `fix`; generated equality over
   identity keys only (parent keys then local); `inherits` entity-only;
   optional local `identity` appends to parent keys; no `uses` / `implements`;
   ban hand `equals` / `hashCode` / `toString` (and Python magic aliases).
   ADR-023 permits `nullable<T>` for non-identity fields, but every field named
   by `identity(...)` must have a non-null type.
3. **Emit**: `data` → `@dataclass(frozen=True)` + struct copy helper;
   `entity` → class + `__eq__` / `__hash__` / `__repr__` on keys + fix-field
   setattr guard.
4. No `@` as a substitute for missing language constructs (use real keywords
   such as `data`). Library decorator application is allowed ([ADR-026](ADR-026-library-decorators.md)).
   ADR-001 boundaries unchanged. ADR-005 unchanged.

## Consequences

- Students see VO vs Entity as distinct keywords, not annotation conventions.
- IDE ≥ 0.0.44: keywords, hover, snippets; docs `DATA_ENTITY.md`, JIT cards.
- Examples: `examples/data.pys`, `examples/entities.pys`,
  `examples/database/` (MySQL shop CRUD + identity demos).
- SQL nullable columns map to explicit nullable non-identity fields; a mapper
  may not invent empty/zero values for SQL `NULL`.

## Rejected alternatives

- Extending `struct` with optional identity (collapses VO/Entity into one bag).
- Framework-only identity (Hibernate-style) without language checks.
- Generating getters/setters (PYS uses `member_access` on fields directly).
