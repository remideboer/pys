# JIT — `result`, `propagate`, and panic

Use `result<T, E>` when the caller can react to failure:

```pys
function result<int, string> readCount(bool valid) {
    if (valid == false) {
        return error("invalid count")
    }
    return ok(7)
}
```

Handle both outcomes:

```pys
result<int, string> outcome = readCount(false)
switch (outcome) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}
```

Output:

```text
invalid count
```

Or return the same error early from another result function:

```pys
function result<int, string> addOne(bool valid) {
    int value = readCount(valid) propagate
    return ok(value + 1)
}
```

Rules:

- The propagated error type must match the enclosing result's `E` exactly.
- A result never automatically becomes its success value.
- `ok()` is only for `result<void, E>`; write `case ok():` to match it.
- `error(payload)` always carries a value; switch patterns always bind one
  (`case error(message)`).
- A result switch needs `ok` plus `error`, or `default`.
- Do not propagate through a `task` or from imported top-level code.

At the `[project].main` entrypoint, an unhandled top-level propagation becomes
a panic: stderr starts with `PYS panic: ...`, PYS sites follow, and exit status
is non-zero. There is no `panic(...)` syntax.

Runnable examples:

- [`examples/results.pys`](../../examples/results.pys): success, handled error,
  switch expression, propagation, and void success.
- [`examples/result_panic/`](../../examples/result_panic/): manifest-selected
  entrypoint and terminal panic.
