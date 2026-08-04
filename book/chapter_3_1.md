# 4.1. Control flow

## `if` / `else if` / `else`

Conditions use parentheses; bodies use braces:

```pys
int x = 5
int y = 8

if (x < y) {
    print("x is less than y")
} else if (x == y) {
    print("equal")
} else {
    print("x is greater than y")
}
```

Logical operators: `and` / `or` / `not` (and `&&` / `||` / `!`).

## `unless` / `if not`

```pys
int x = 50
unless (x > 100) {
    print("not greater than 100")
}
```

### Exercise

> Given `int hour` (0–23), print `"night"` if `hour < 6 or hour >= 22`,
> else `"day"`.

---

[Previous: Session 2](chapter_3.md) · [Next: Loops](chapter_3_2.md)
