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

Logical operators combine conditions. Prefer the word forms while learning:

```pys
int hour = 23

if (hour < 6 or hour >= 22) {
    print("night")
} else {
    print("day")
}

if (hour >= 9 and hour < 17) {
    print("office hours")
}

if (not (hour == 12)) {
    print("not noon")
}
```

Symbols `&&` / `||` / `!` mean the same as `and` / `or` / `not`.

## `unless` / `if not`

```pys
int x = 50
unless (x > 100) {
    print("not greater than 100")
}

if not (x > 100) {
    print("same idea with if not")
}
```

### Exercise

> Given `int hour` (0–23), print `"night"` if `hour < 6 or hour >= 22`,
> else `"day"`.

---

[Previous: Session 2](chapter_3.md) · [Next: Loops](chapter_3_2.md)
