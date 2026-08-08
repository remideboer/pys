# 2.1. Functions

A **function** is a named recipe: a block of instructions you can run by
calling its name. So far every line ran once, top to bottom. Functions let
you package a step and reuse it.

## A function that prints

```pys
function void greet(string name) {
    print("Hello, " + name + "!")
}

greet("Ada")
greet("Tom")
```

Output:

```text
Hello, Ada!
Hello, Tom!
```

You can also pass arguments **by name** when there are several parameters.
Use **only** named or **only** positional in one call — never mix:

```pys
function void greetTwice(string name, int times) {
    print(name)
}

greetTwice(name="Ada", times=2)
# greetTwice("Ada", times=2)  // illegal: mixed styles
```

Compiles; prints `Ada` (once in this short body — `times` is unused here to
keep the demo focused on call style).

Breakdown:

- `function` — we are declaring a function.
- `void` — this function does **not** hand back a result (it only prints).
- `greet` — the name we will call.
- `(string name)` — one *parameter*: an input drawer labeled `name` with
  type `string`.
- `{ ... }` — the *body*: what runs when we call `greet(...)`.
- `greet("Ada")` — a *call*: run the body with `name` set to `"Ada"`.
- `greetTwice(name="Ada", times=2)` — the same idea with **named** arguments.

Think of a function as a **reusable machine** (the gear): the same block of
code can run many times. Values may go **in** (parameters). Something may
come **out** (a `return` value) — or, for `void`, only a side effect such
as printing.

<figure class="concept-diagram" role="img" aria-label="Function greet as a reusable gear box: string name in, body prints Hello, void so no value out">
  <div class="fn-flow">
    <div class="fn-port">
      <span class="fn-port-label">input</span>
      <code>name</code>
      <span class="fn-type">string</span>
    </div>
    <div class="fn-arrow" aria-hidden="true">→</div>
    <div class="fn-box">
      <div class="fn-box-head">
        <span class="fn-gear" title="reusable block" aria-hidden="true">⚙</span>
        <code>greet</code>
        <span class="fn-repeat">call again</span>
      </div>
      <pre class="fn-body">print("Hello, " + name + "!")</pre>
      <span class="fn-box-foot"><code>void</code> — no value returned to the caller</span>
    </div>
    <div class="fn-arrow" aria-hidden="true">→</div>
    <div class="fn-port fn-side">
      <span class="fn-port-label">effect</span>
      <span>prints on screen</span>
    </div>
  </div>
  <figcaption>
    One named recipe. Each call feeds a new <code>name</code> into the same
    body — that is why <code>greet("Ada")</code> and <code>greet("Tom")</code>
    both work.
  </figcaption>
</figure>

Notice we **call** `greet` ourselves. Declaring a function does not run it.
(There is no hidden auto-start `main` in PYS.)

## A function that returns a value

When a function computes something for the caller, put the return type
after `function` and use `return`:

```pys
function int add(int a, int b) {
    return a + b
}

int sum = add(2, 3)
print(sum)
```

Output:

```text
5
```


`return a + b` finishes the function and sends `5` back to the caller.
That value is stored in `sum`. Same machine idea — now with a real
**output** port instead of only a print effect:

<figure class="concept-diagram" role="img" aria-label="Function add as a reusable gear box: ints a and b in, returns int sum">
  <div class="fn-flow">
    <div class="fn-port">
      <span class="fn-port-label">inputs</span>
      <code>a</code>, <code>b</code>
      <span class="fn-type">int</span>
    </div>
    <div class="fn-arrow" aria-hidden="true">→</div>
    <div class="fn-box">
      <div class="fn-box-head">
        <span class="fn-gear" title="reusable block" aria-hidden="true">⚙</span>
        <code>add</code>
        <span class="fn-repeat">call again</span>
      </div>
      <pre class="fn-body">return a + b</pre>
      <span class="fn-box-foot">returns <code>int</code></span>
    </div>
    <div class="fn-arrow" aria-hidden="true">→</div>
    <div class="fn-port fn-out">
      <span class="fn-port-label">output</span>
      <code>5</code>
      <span class="fn-type">int → <code>sum</code></span>
    </div>
  </div>
  <figcaption>
    Inputs enter the gear; the body runs; a typed value comes out to the
    caller. You can call <code>add</code> again with different numbers.
  </figcaption>
</figure>

### Exercise

> Write `function string shout(string text)` that returns the text with
> `"!"` added at the end. Call it from top level and print the result.

---

[Previous: Back to the basics](basics.md) · [Next: Processing input](basics_input.md)
