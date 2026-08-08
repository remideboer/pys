# ADR-010: Abstract classes as nominal incomplete types

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-009](../evolution/CER-009-abstract-classes.md) |
| Permanent | This ADR (incl. litmus / construct table); LANGUAGE §Abstract; book `chapter_4_3_abstract_classes` |
| Draft origin | `requirements/abstract_class.md` (temporary; do not treat as canonical) |

## Context

Teaching needs shared state and template methods with deferred variation points,
without collapsing into interfaces (signatures only) or traits (composition, not
types).

### When abstract class vs interface vs trait

| Construct | Owns state | Provides bodies | Requires subtype relation | Typical use |
| --- | --- | --- | --- | --- |
| Interface | No | No | Yes (nominal contract) | Polymorphism via pure contract |
| Trait | No (borrows host’s) | Yes | No | Horizontal reuse across unrelated types |
| Abstract class | Yes | Partial (mix) | Yes (taxonomic `is-a`) | Vertical reuse + enforced variation point |
| Concrete class | Yes | Yes (all) | — | Instantiable end product |

**Litmus test (template method):** if shared logic must call back into a method
that *varies per subclass* (e.g. `contains` calling abstract `get`), an abstract
class is warranted. If the shared logic never needs to vary, prefer a trait or a
plain utility function — inheritance would be over-engineering.

Worked teaching shape (requirement): `AbstractList` owns `size` / shared
`isEmpty`/`contains`; `ArrayListPys` vs `LinkedListPys` supply different `get`/
`add` storage strategies. That is *is-a* + polymorphism, not “I also do X”
(`uses`).

## Decision

1. **`abstract class`** is a nominal type: bindings and polymorphism allowed;
   direct `AbstractName(...)` rejected.
2. Header modifiers: `[closed | abstract]` — mutually exclusive
   ([ADR-028](ADR-028-open-override-closed.md); formerly `sealed`).
3. Abstract methods: only inside an abstract class; require `member_access` +
   `abstract` + return type; no `{` body. Abstract methods are **implicitly
   open** sockets for `override` (ADR-028).
4. **`void`** is a return type; `void` methods must not `return expr`.
5. Concrete subclasses must **`override`** every inherited abstract method
   (name + arity; return type when both known). Intermediate abstract ancestors
   may leave methods unimplemented.
6. **Emit**: subclass `ABC`; each abstract method gets `@abstractmethod` +
   `pass`. Constructors use `constructor` ([ADR-027](ADR-027-constructor-keyword.md));
   call via `super(...)`.
7. Users do not write `@abstractmethod` in PYS — `abstract` emits it. Library
   decorator application (`@expr` on methods) is allowed ([ADR-026](ADR-026-library-decorators.md)).

## Consequences

- Distinct from `interface` (no fields/bodies) and `trait` (not a type).
- IDE: keywords/`void`, hover, snippets; extension ≥ 0.0.42.
- Pedagogy: JIT `J-abstract`; example `examples/abstract_classes.pys`.

## Rejected alternatives

- Allowing abstract methods on concrete classes.
- Treating abstract classes as non-types (like traits).
- Emitting without ABC (weaker runtime contract for teaching demos).
