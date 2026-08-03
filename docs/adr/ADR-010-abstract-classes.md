# ADR-010: Abstract classes as nominal incomplete types

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-009](../evolution/CER-009-abstract-classes.md) |
| Source | [`requirements/abstract_class.md`](../../requirements/abstract_class.md) |

## Context

Teaching needs shared state and template methods with deferred variation points,
without collapsing into interfaces (signatures only) or traits (composition, not
types).

## Decision

1. **`abstract class`** is a nominal type: bindings and polymorphism allowed;
   direct `AbstractName(...)` rejected.
2. Header modifiers: `[sealed | abstract]` — mutually exclusive.
3. Abstract methods: only inside an abstract class; require `member_access` +
   `abstract` + return type; no `{` body.
4. **`void`** is a return type; `void` methods must not `return expr`.
5. Concrete subclasses must implement every inherited abstract method (name +
   arity; return type when both known). Intermediate abstract ancestors may
   leave methods unimplemented.
6. **Emit**: subclass `ABC`; each abstract method gets `@abstractmethod` +
   `pass`. Constructors allowed; call via `super(...)`.
7. No `@` in PYS source.

## Consequences

- Distinct from `interface` (no fields/bodies) and `trait` (not a type).
- IDE: keywords/`void`, hover, snippets; extension ≥ 0.0.42.
- Pedagogy: JIT `J-abstract`; example `examples/abstract_classes.pys`.

## Rejected alternatives

- Allowing abstract methods on concrete classes.
- Treating abstract classes as non-types (like traits).
- Emitting without ABC (weaker runtime contract for teaching demos).
