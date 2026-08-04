# 9.4. What has no direct twin

Not everything maps 1:1 — and that is fine.

| PYS | Transfer note |
|-----|----------------|
| Transpile-to-Python runtime | C#/Java have their own VMs; mental model still “compile then run” |
| `tasks` / `task` / `await` | Closest everyday cousins: `async`/`await`, `Task`/`CompletableFuture`, structured concurrency libraries — learn those deliberately |
| `shared` / `atomic` | Explicit concurrency primitives / `Interlocked` / `AtomicInteger` |
| `trait` + `uses` | Prefer interfaces (+ default methods) or composition |
| `pys.toml` source roots | Test projects / source sets in the IDE |
| Top-level statements | C# has top-level statements; Java traditionally wants `main` |
| No `try`/`catch` in PYS grammar | You **will** learn exceptions in C#/Java — treat them as a new chapter, not a PYS gap to invent |

When you hit a wall in C# or Java, ask: “Is this a new platform rule, or
the same design idea with different spelling?” Most of Session 1–4 was
the second kind.

### Exercise

> List three PYS habits you will keep on day one of C# or Java (casing,
> member order, preferring immutable locals, …). Keep the list.

---

[Previous: Control flow and collections](chapter_8_3.md) · [Next: Exercise — Contact book](exercises_contact_book.md)
