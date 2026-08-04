# ADR-019: C-style loops have one immutable counter

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Scope | `c_for_loop`, `while_loop`, loop teaching material |

## Context

Java and C++ allow several variables in a classic `for` header:

```java
for (int x = 0, y = 10; x < 10; x++, y++) {
    // ...
}
```

Only `x` controls termination. The language does not require `y` to use the
same step, and the body may mutate it again. Synchronization is therefore a
programmer convention that can silently diverge.

PYS already separates two needs:

- `c_for_loop` is a compact, checked form for one induction variable;
- `while_loop` accepts any condition and ordinary mutable state.

## Decision

Keep `c_for_loop` deliberately narrow:

1. initializer, condition, and step name the same variable;
2. that variable is immutable in the body;
3. the header cannot declare or step additional variables.

When several values change together, declare them separately and use
while-style `loop (condition)`. Initialization, the controlling condition, and
every mutation then remain visible as ordinary statements.

## Consequences

- A C-style loop preserves a simple guarantee: one visible counter controls and
  advances the loop.
- Multi-value algorithms remain expressible without new syntax.
- Students can transfer the algorithm to Java or C++, while recognizing that
  those languages permit denser headers with fewer guarantees.
- The while-style form requires explicit updates; forgetting an update can
  still cause a non-terminating loop, as in other while loops.

## Rejected alternatives

### Comma-separated counters

This would copy Java/C++ flexibility and also copy the divergence risk. It
would make the existing body-immutability rule ambiguous or weaker.

### Grouped syntax such as `{x, y}`

`int {x,y} = 10, x < 10, {x++, y++}` has no mainstream Java/C# transfer
equivalent, adds grammar for a narrow case, and does not guarantee that both
values stay synchronized.

### Automatic lockstep

Inferring that several updates must remain equal would be surprising and would
not cover useful algorithms whose variables intentionally have different
steps. Explicit while-style state is clearer.
