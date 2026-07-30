# JIT — Control flow

## Forms

```pys
if (n > 0) {
    print("pos")
} else if (n == 0) {
    print("zero")
} else {
    print("neg")
}

unless (ok) {
    print("not ok")
}
# same as unless
if not (ok) {
    print("not ok")
}
```

## Rules

1. Condition in `(…)`  
2. Body in `{ … }`  
3. `unless (cond)` ≡ `if not (cond)` — use when the negative case is the story you want to name
