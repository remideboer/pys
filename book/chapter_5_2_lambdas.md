# 6.2. Lambdas

A lambda type lists **inputs left of `->`** and the **return type on the
right**: `lambda<int -> bool>` means “one `int` in, `bool` out”.
Sugar `lambda<int>` (or explicit `lambda<-> int>`) means no parameters,
returns `int`.

<figure class="concept-diagram" role="img" aria-label="Lambda value typed as lambda int to bool then called later">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>lambda&lt;int → bool&gt;</strong>
      <span>n =&gt; n % 2 == 0</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">bind</div>
    <div class="diagram-box"><strong>isEven</strong><span>a value you can call later</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>isEven(4)</strong><span>True</span></div>
  </div>
  <figcaption>
    The type tag is part of the value story: bind once, call when you need
    the answer.
  </figcaption>
</figure>

```pys
lambda<int -> bool> isEven = n => n % 2 == 0
print(isEven(4))
print(isEven(5))

lambda<int, int -> int> safeDivide = (a, b) => {
    if (b == 0) {
        return 0
    }
    return a / b
}
print(safeDivide(10, 2))
```

Output:

```text
True
False
5.0
```


Parameter types on `(a, b)` are omitted here: the binding’s `lambda<…>`
already names them. You may write `(int a, int b)` if you want the types
repeated next to the names.

Forms: `n => expr`, `(params) => expr`, `(params) => { … }`, `() => …`.

Captures are **by value** at creation and read-only unless the outer name
is `shared` or `atomic` — concurrency keywords taught in
[shared state](chapter_6_2_shared_state.md) and [atomic updates](chapter_6_3_atomic_updates.md). Until
then, treat captured names as snapshots you can read, not reassign.

### Exercise

> Write `lambda<string -> string> shout` that adds `"!"` and call it on
> `"hey"`.

---

[Previous: Functions that return values](chapter_5_1_functions_return.md) · [Next: Passing functions around](chapter_5_3_passing_functions.md)
