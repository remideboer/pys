# JIT — Loops

## Forms

```pys
loop (int i = 0, i < 3, i++) {
    print("#i{i}")
}

loop (n > 0) {
    n = n - 1
}

loop (string item in names) {
    print(item)
}

loop (tuple<int, string> row in rows) {
    print("#i{row[0]} #s{row[1]}")
}
```

## Rules

1. Prefer a typed loop variable when the collection’s element type is known  
2. Loop counters in the C-style header are immutable inside the body  
3. Loop binders and names declared inside `{ … }` are **block-scoped** — they
   do not exist after the closing brace  
4. `break` / `continue` / `pass` work as in the showcase examples
