# 2.3. Making choices

Programs often need to pick a path: *if this is true, do A; otherwise do B*.

## `if` / `else`

```pys
int temperature = 18

if (temperature < 15) {
    print("Wear a coat")
} else {
    print("A sweater is enough")
}
```

Output:

```text
A sweater is enough
```


- The condition sits in parentheses: `(temperature < 15)`.
- If it is true, the first `{ ... }` block runs.
- If not, the `else` block runs.

Chain more cases with `else if`:

```pys
int score = 75

if (score >= 90) {
    print("Excellent")
} else if (score >= 60) {
    print("Pass")
} else {
    print("Try again")
}
```

Output:

```text
Pass
```


## `unless` — when you think in negatives

```pys
int lives = 3

unless (lives == 0) {
    print("Keep playing")
}
```

Output:

```text
Keep playing
```


`unless (condition)` means “if the condition is **not** true”. The same
idea with different words:

```pys
int lives = 3

if not (lives == 0) {
    print("Keep playing")
}
```

Output:

```text
Keep playing
```


> **Sidebar — modulo `%`**
>
> `n % 2` is the remainder after dividing `n` by 2. If the remainder is
> `0`, `n` is even; otherwise it is odd.

### Exercise

> Ask for an integer with `input` (import from `builtins`). If it is even,
> print `"even"`; otherwise print `"odd"`. Hint: `n % 2 == 0` means even.

---

[Previous: Processing input](basics_input.md) · [Next: Data structures](basics_data.md)
