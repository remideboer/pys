# 4.1. Control flow

## `if` / `else if` / `else`

Conditions use parentheses; bodies use braces:

<figure class="concept-diagram" role="img" aria-label="Condition branches to then path or else path">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box"><strong>condition</strong><span>x &lt; y ?</span></div>
    <div class="diagram-arrow" aria-hidden="true">↘ true</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>then</strong>
      <span>print “x is less…”</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">↙ false</div>
    <div class="diagram-box diagram-outside"><strong>else / else if</strong><span>other path</span></div>
  </div>
  <figcaption>
    One question, then pick a path — only one branch body runs.
  </figcaption>
</figure>

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

Output:

```text
x is less than y
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

Output:

```text
night
not noon
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

Output:

```text
not greater than 100
same idea with if not
```


### Exercise

> Given `int hour` (0–23), print `"night"` if `hour < 6 or hour >= 22`,
> else `"day"`.

---

[Previous: Running and checking](chapter_2_4_running_and_checking.md) · [Next: Loops](chapter_3_2_loops.md)
