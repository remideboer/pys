# 6.3. Passing functions around

Because lambdas are values, you can pass them into helpers:

<figure class="concept-diagram" role="img" aria-label="apply helper receives a lambda cable and runs it on value">
  <div class="diagram-flow" style="min-width:32rem">
    <div class="diagram-box"><strong>5</strong><span>value</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>apply</strong>
      <span>calls fn(value)</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">←</div>
    <div class="diagram-box diagram-layer-edge" style="border-style:dashed;border-width:2px;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>n =&gt; n * 2</strong>
      <span>lambda cable</span>
    </div>
  </div>
  <figcaption>
    The helper owns the call site; you plug in which transformation to run.
  </figcaption>
</figure>

```pys
function int apply(int value, lambda<int -> int> fn) {
    return fn(value)
}

int doubled = apply(5, n => n * 2)
print(doubled)
```

Output:

```text
10
```


Prefer named functions when the logic is non-trivial or reused; prefer
lambdas for short adapters at the call site.

> **Sidebar — `.loop` on arrays**
>
> `numbers.loop(print)` means “call `print` once per element” (it maps to
> Python’s `list(map(...))`). Use an ordinary `loop (… in …)` when you need
> an `if`, `break`, or more than one statement per item — see
> [Loops](chapter_3_2_loops.md).

```pys
int[] numbers = [1, 2, 3]
numbers.loop(print)
```

Output:

```text
1
2
3
```


### Exercise

> Write `function int applyTwice(int value, lambda<int -> int> fn)` that
> applies `fn` twice. Call it with `n => n + 1` starting from `0`.

---

[Previous: Lambdas](chapter_5_2_lambdas.md) · [Next: GUI programming with Tkinter — introduction](gui_intro.md)
