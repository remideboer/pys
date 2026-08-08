# ADR-027: Explicit `constructor` keyword

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Code detail | [CER-045](../evolution/CER-045-constructor-keyword.md) |
| Source | `requirements/contructor_keyword.md` |

## Context

Constructors were declared by repeating the enclosing type name
(`public constructor(...)`). That convention is opaque for beginners and conflicts
with the curriculum’s JavaScript track, where `constructor` is the reserved
word.

## Decision

1. **Grammar:** `constructor_decl = { decorator } , member_access , "constructor" ,
   "(" , [ parameter_list ] , ")" , block` — for both `class` and `entity`.
2. **Reject** the old class-name form with a FatalParseError tip to use
   `constructor`.
3. **Chaining:** `this(args)` delegates to another constructor of the same type
   (emit `self.__init__(...)`). `super(args)` calls the ancestor constructor.
   Missing both still injects implicit `super().__init__()`.
4. **Transfer table (teaching):** JS identical; C#/Java drop the keyword and
   reuse the type name.
5. Related field/`fix` rules and the implicit root for `override toString`
   etc. are specified with [ADR-028](ADR-028-open-override-closed.md).

## Consequences

- Mechanical migrate of every `.pys` ctor and book fences in the same change set.
- Snippets / IDE highlight `constructor`.
- Appendix B keywords gain `constructor`.

## Rejected alternatives

- Keeping class-name ctors as a deprecated alias (students would learn two forms).
- A short alias `ctor` (less transferable to JS).
