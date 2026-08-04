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


Breakdown:

- `function` — we are declaring a function.
- `void` — this function does **not** hand back a result (it only prints).
- `greet` — the name we will call.
- `(string name)` — one *parameter*: an input drawer labeled `name` with
  type `string`.
- `{ ... }` — the *body*: what runs when we call `greet(...)`.
- `greet("Ada")` — a *call*: run the body with `name` set to `"Ada"`.

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
That value is stored in `sum`.

### Exercise

> Write `function string shout(string text)` that returns the text with
> `"!"` added at the end. Call it from top level and print the result.

---

[Previous: Back to the basics](basics.md) · [Next: Processing input](basics_input.md)
