# 4.2. Loops

Three shapes:

```pys
# C-style
loop (int i = 0, i < 3, i++) {
    print(i)
}

# while-style
int n = 0
loop (n < 3) {
    print(n)
    n++
}

# foreach
list<string> xs = ["a", "b"]
loop (string x in xs) {
    print(x)
}
```

`break` leaves the loop early; `continue` skips to the next iteration.
Names declared inside `{ … }` are **block-scoped** — they do not exist
after the closing brace.

### Exercise

> Sum the numbers 1..10 into `int total` with a C-style loop and print the
> total with `#i{total}`.

---

[Previous: Control flow](chapter_3_1.md) · [Next: Arrays and lists](chapter_3_3.md)
