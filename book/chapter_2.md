# Session 1 — Types that protect you

You finished the basics track: values, functions, choices, loops. This
session slows down on **types** — the rules that catch whole classes of
mistakes before the program runs.

PYS is **statically typed**: every value has a type the compiler knows.
That is the same idea you will meet in C# and Java.

In this session:

1. [Formatting output](chapter_2_1.md) — interpolation and typed `#i{…}` slots
2. [Variables: var, fix, and const](chapter_2_2.md)
3. [Static types and casts](chapter_2_3.md)
4. [Running and checking your work](chapter_2_4.md)

If you still prefer top-level scripts, keep them. When you want a
C#/Java-shaped entry habit, declare a function and **call it**:

```pys
function void main() {
    print("started")
}

main()
```

Nothing magic about the name `main` — the call is what runs it.

---

[Previous: Spoilers](basics_spoilers.md) · [Next: Formatting output](chapter_2_1.md)
