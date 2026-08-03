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

## Trade-offs

- Breaking change for existing PYS that used `public` on interface methods;
  tip points to the new form.
