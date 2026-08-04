# ADR-020: One name per declaration

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Scope | Variable, constant, field, shared, and atomic declarations |

## Context

C-family declaration syntax permits several declarators after one type:

```c
int x, y = 10;
```

For automatic local variables in C and C++, only `y` is initialized; reading
`x` before assignment is unsafe. Java and C# give the same initializer only to
`y`, but reject a read of the unassigned local `x` at compile time. Fields and
static-storage objects have different default-initialization rules, which adds
another context-sensitive distinction.

Other languages attach different meaning to comma-separated names and values.
Go uses positional initializer values (`var x, y int = 10, 10`). Python's
`x, y = 10, 10` is assignment with iterable unpacking, not a typed declaration.
Similar-looking punctuation therefore does not provide a transferable,
language-independent meaning.

PYS declaration productions already bind one `identifier`. This is consistent
across mutable variables, `var`, `fix`, `const`, `shared`, `atomic`, and fields.

## Decision

Every PYS declaration binds exactly one name. If an initializer is present, it
belongs to that name alone.

To initialize two variables, write two declarations:

```pys
int x = 10
int y = 10
```

Reject comma-separated declarators (`int x, y = 10`), repeated declarators in
one statement (`int x = 10, y = 10`), and grouped declaration syntax. Parameter
lists are unaffected: each parameter has its own explicit type-and-name slot,
and declaration-time initializer ownership is not ambiguous.

## Consequences

- A declaration can be understood without C/Java storage-context rules or
  Python/Go unpacking expectations.
- All declaration kinds keep the same one-name shape.
- Tooling, diagnostics, source maps, and refactor plans operate on one binding
  per declaration statement.
- Initializing several names takes several lines. This is deliberate: the
  comma form adds brevity but no expressive power.

## Rejected alternatives

### C/Java declarator lists

`int x, y = 10` visually suggests that both names may receive `10`, while the
initializer belongs only to `y`. Copying this form would teach a known transfer
hazard.

### Repeating `=` in one statement

`int x = 10, y = 10` is unambiguous, but saves only a line and makes PYS
declarations inconsistent with `const`, `fix`, fields, and other one-name
forms.

### Go/Python-style positional declaration

`int x, y = 10, 10` would introduce multi-target assignment semantics into a
typed declaration. PYS does not need that machinery to express two independent
bindings.

### Grouped names

Forms such as `int {x, y} = 10` have no useful C#/Java transfer precedent and
leave shared-versus-positional initializer ownership unclear.
