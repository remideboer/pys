# 2.8. Expressing success and failure

Some operations have two honest outcomes: a value, or a problem the caller can
handle. PYS writes both in the type:

```pys
function result<int, string> checkAge(int age) {
    if (age < 0) {
        return error("age cannot be negative")
    }
    return ok(age)
}
```

- `result<int, string>` means “success contains an `int`; failure contains a
  `string`”.
- `ok(age)` constructs the success outcome.
- `error("...")` constructs the failure outcome.
- `ok` and `error` are PYS words. You cannot reuse them as names.

This function only declares behavior, so it produces no output by itself.

## Handle both outcomes

A result does **not** silently become its success value. Use a result `switch`
to handle it:

```pys
function result<int, string> checkAge(int age) {
    if (age < 0) {
        return error("age cannot be negative")
    }
    return ok(age)
}

result<int, string> accepted = checkAge(15)
switch (accepted) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}

result<int, string> rejected = checkAge(-2)
switch (rejected) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}
```

Output:

```text
15
age cannot be negative
```

`case ok(value)` gives that arm the success payload. `case error(message)` gives
that arm the error payload. The names `value` and `message` exist only in their
own arm. Because `error` is a PYS word, you cannot use it as the binding name.

The switch must cover both outcomes. A `default` arm may stand in for one, but
naming both is usually clearer. A plain value such as `case 15:` is not a
result pattern.

## Return the error early with `propagate`

Sometimes a function cannot solve a failure but its caller can. Postfix
`propagate` says:

> Give me the success payload. If this is an error, stop this function and
> return the same error now.

> **Sidebar — why not a tiny `?` operator?**
>
> A one-character operator is easy to type without thinking (languages that
> offer cheap “just unwrap” forms see that pattern abused). PYS uses the
> word `propagate` so the early-return edge stays deliberate and readable.
> There is also no `try`/`catch` in PYS — recoverable failure stays in the
> `result` type.

```pys
function result<int, string> checkAge(int age) {
    if (age < 0) {
        return error("age cannot be negative")
    }
    return ok(age)
}

function result<int, string> ageNextYear(int age) {
    int checked = checkAge(age) propagate
    print("age accepted")
    return ok(checked + 1)
}

result<int, string> first = ageNextYear(15)
switch (first) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}

result<int, string> second = ageNextYear(-2)
switch (second) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}
```

Output:

```text
age accepted
16
age cannot be negative
```

The second call skips `print("age accepted")`: propagation leaves the function
first. The error type must match exactly. For example, a function returning
`result<int, string>` cannot directly propagate `result<int, int>`.

## Success without a payload

Use `result<void, E>` when success only means “completed”:

```pys
function result<void, string> save(bool allowed) {
    if (allowed == false) {
        return error("save denied")
    }
    return ok()
}

result<void, string> outcome = save(true)
switch (outcome) {
    case ok():
        print("saved")
    case error(message):
        print(message)
}
```

Output:

```text
saved
```

Only a `void` success uses `ok()` and `case ok()` without a payload. `error`
always needs an error value.

## When an error reaches the program boundary

The directly run file is the **entrypoint**. It may propagate at top level:

```pys
function result<int, string> readCount() {
    return error("count is missing")
}

int count = readCount() propagate
print(count)
```

Expected stdout: no output. Expected stderr starts with:

```text
PYS panic: count is missing
  at ... in <entrypoint>
```

Expected exit status: non-zero. PYS calls this outcome a **panic**. It is not a
`panic(...)` command: it means an error reached the entrypoint with nobody left
to handle it. Statements after the failing propagation do not run.

Larger projects put the authoritative entrypoint in `pys.toml`:

```toml
[project]
main = "src/app.pys"
```

Run and Debug use that same file. Imported files may return results from
functions, but may not propagate at top level.

> **Do not confuse `result` and `enum`.** A result always models success versus
> recoverable failure and carries payloads. An enum, taught later, models any
> fixed set of named choices such as colors or order states.

### Exercise

> Write `function result<int, string> half(int number)`. Return
> `error("must be even")` when `number % 2 != 0`; otherwise return
> `ok(number / 2)`. Handle calls with `8` and `7`. Expected output: `4`, then
> `must be even`.

---

[Previous: Null and missing values](basics_null.md) · [Next: Structuring code](basics_structuring.md)
