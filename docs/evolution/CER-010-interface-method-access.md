# CER-010: Interface methods without access modifiers

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (interface-access increment) |
| Scope | `parse.py`; `docs/language.ebnf`; `docs/language-railroad.html`; `docs/LANGUAGE.md`; `examples/interfaces.pys`; tutorials T4 / J-class; `pys-language/*`; tests |
| ADRs | — (surface cleanup of existing interface contract) |

## Context

Interface methods are always public and abstract. Requiring `public` on every
signature duplicated that fact and conflicted with trait-style bare signatures.

### Pre-behavior

```pys
package interface Loadable {
    public load(int weight)
    public int capacity()
}
```

Access keywords inside interface bodies were silently accepted (and discarded).

### Post-behavior

```pys
package interface Loadable {
    load(int weight)
    int capacity()
}
```

- Grammar: `interface_method` has no `member_access`.
- Parse: `public` / `private` / `protected` / `module` on an interface method
  → `pys.interface-access` with tip to omit the modifier.
- Implementing **class** methods still require `public` (unchanged).
- IDE ≥ 0.0.43: hover/snippets updated.

### Evidence

`tests/test_sem.py::test_sem_interface_access_modifier_rejected`;
`tests/test_transpiler_brace_blocks.py::test_interface_access_modifier_is_rejected`;
`examples/interfaces.pys`.

### 2. Nominal return types on interface methods (2026-08-08)

**Pre-behavior:** Parser only skipped a return type when it was in the builtin
`_TYPES` set. `Button createButton()` treated `Button` as the method name and
failed (`Expected LPAREN, got IDENT createButton`).

**Why it hurt:** GoF / real OO interfaces need product return types; EBNF already
allowed `return_type` = `type_name | void`.

**Post-behavior:** Interface signatures use the same return-type lookahead as
class/trait methods (nominal types, generics, trailing `[]`). Examples:
`examples/patterns/design/creational/abstract_factory.pys`.

**Teaching / IDE:** `book/chapter_4_2_interfaces.md` (§ Return types on the
socket); hover + `interface` snippet in `pys-language/` mention nominal returns.

**Evidence:** `tests/test_interface_return_types.py`.

### 3. Shop ports use interfaces (2026-08-08)

**Pre-behavior:** `examples/database` and `examples/rest-api/shop/*` declared
Repository / Data Mapper contracts as bare `abstract class` (no fields or
shared bodies), with README claiming abstract was required for `list<Product>`.

**Why it hurt:** Violated construct fit (socket → `interface`); the README
rationale was obsolete after §2.

**Post-behavior:** Those ports are `interface`; implementors use `implements`.
README updated. Legitimate abstracts with shared code unchanged
(`examples/abstract_classes.pys`, patterns template bases).

**Evidence:** transpile of converted `repositories.pys` / `mappers.pys` modules.

## Trade-offs

- Breaking change for existing PYS that used `public` on interface methods;
  tip points to the new form.
