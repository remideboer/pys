# 10.4. What has no direct twin

Not everything maps 1:1 — and that is fine.

| PYS | Transfer note |
|-----|----------------|
| Transpile-to-Python runtime | C#/Java have their own VMs; mental model still “compile then run” |
| `tasks` / `task` / `await` | Closest everyday cousins: `async`/`await`, `Task`/`CompletableFuture`, structured concurrency libraries — learn those deliberately |
| `shared` / `atomic` | Explicit concurrency primitives / `Interlocked` / `AtomicInteger` |
| `trait` + `uses` | Prefer interfaces (+ default methods) or composition |
| `pys.toml` source roots | Test projects / source sets in the IDE |
| `pys.toml` `[project].main` | C# startup object / top-level project entry; Java `main` class or build-tool main class |
| Top-level statements | C# has top-level statements; Java traditionally wants `main` |
| `result<T,E>` + `propagate` | C#/Java usually use exceptions; map the intent deliberately, because the control-flow model differs |

When you hit a wall in C# or Java, ask: “Is this a new platform rule, or
the same design idea with different spelling?” Most of Session 1–4 was
the second kind.

## Transferring recoverable-error code

PYS puts an expected failure in the return type:

```pys
function result<int, string> readCount(bool valid) {
    if (valid == false) {
        return err("invalid count")
    }
    return ok(7)
}

result<int, string> outcome = readCount(false)
switch (outcome) {
    case ok(value):
        print(value)
    case err(error):
        print(error)
}
```

Output:

```text
invalid count
```

The caller can see `string` as the exact error type. It must either match both
outcomes or write `propagate` in another function whose error type is exactly
the same.

Everyday C# more often expresses the same *user story* with an exception:

```csharp
static int ReadCount(bool valid)
{
    if (!valid)
        throw new FormatException("invalid count");
    return 7;
}

try
{
    Console.WriteLine(ReadCount(false));
}
catch (FormatException error)
{
    Console.WriteLine(error.Message);
}
```

Output:

```text
invalid count
```

This is not a spelling-only translation:

- `int` does not advertise `FormatException` in the C# signature.
- The exception is not a normal return value.
- Control jumps up the stack until a matching `catch` is found.
- An uncaught exception ends the process, roughly the observable role of a PYS
  panic, but it may come from any throwing operation rather than only an
  unhandled result at the entrypoint.

Java has both unchecked and checked exceptions. A checked declaration makes
one possibility visible:

```java
static int readCount(boolean valid) throws java.io.IOException {
    if (!valid) {
        throw new java.io.IOException("invalid count");
    }
    return 7;
}

public static void main(String[] args) {
    try {
        System.out.println(readCount(false));
    } catch (java.io.IOException error) {
        System.out.println(error.getMessage());
    }
}
```

Output:

```text
invalid count
```

`throws IOException` is closer to visible failure than the C# signature, but
it still uses stack unwinding and does not make success/error variants into a
value that can be switched over. Java unchecked exceptions need not appear in
the signature at all.

## A transfer checklist

When moving a PYS result API:

1. Decide which `err(E)` values are expected, recoverable conditions.
2. In C#/Java, choose a specific exception type or a project-specific result
   class according to the target codebase's conventions.
3. Translate a handling `switch` to a narrow `catch` (or explicit result
   inspection), not a blanket `catch (Exception)`.
4. Translate `propagate` to deliberate exception propagation or rethrowing.
   Do not add an empty catch merely to silence the compiler.
5. Put the final handler at the application boundary when the program can
   report the problem usefully. Do not assume every uncaught exception is an
   intentional equivalent of PYS panic.

### Exercise

> List three PYS habits you will keep on day one of C# or Java (casing,
> member order, preferring immutable locals, …). Keep the list.
>
> Then map one `result<int,string>` function to C# or Java. Write down whether
> its error is represented by a specific exception or an explicit result
> class, and why. Expected deliverable: both the target signature and its
> handling call site.

---

[Previous: Control flow and collections](chapter_8_3_control_flow_collections.md) · [Next (optional): From source file to running process](under_the_hood_entrypoint.md)
