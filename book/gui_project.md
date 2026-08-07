# 7.4. A small project: temperature converter

Everything in this short course so far comes together in one small,
complete, procedural application: a Celsius-to-Fahrenheit converter with
input validation.

A runnable twin of this project lives at
[`examples/gui/temperature_tk/`](../examples/gui/temperature_tk/).

## 1. Plan before code

Before writing anything, it helps to state the plan in plain language:

1. One `Entry` for the Celsius value.
2. One `Button` that, on click, reads the entry, converts it, and shows
   the result.
3. The entry's text is always a `string` — the user could type letters,
   not just numbers. The conversion needs to handle that possibility
   instead of crashing.

Point 3 is exactly the kind of situation `result<T,E>` exists for:
parsing user input is a classic recoverable-failure case, not a
programmer bug. PYS has no `try`/`catch`; instead
`parseFloat(string)` returns `result<float, string>` — `ok` when the
text can be parsed as a float, `error` with a message when it cannot.

```pys
import tkinter as tk

function result<float, string> parseCelsius(string input) {
    return parseFloat(input.strip())
}

Tk window = tk.Tk()
window.title("Celsius to Fahrenheit")

Label instructions = tk.Label(window, text="Enter a temperature in Celsius:")
instructions.grid(row=0, column=0, columnspan=2)

Entry celsiusEntry = tk.Entry(window)
celsiusEntry.grid(row=1, column=0)

Label resultLabel = tk.Label(window, text="")
resultLabel.grid(row=2, column=0, columnspan=2)

Button convertButton = tk.Button(window, text="Convert", command=() => {
    result<float, string> parsed = parseCelsius(celsiusEntry.get())

    switch (parsed) {
        case ok(celsius): {
            float fahrenheit = celsius * 9 / 5 + 32
            resultLabel.config(text=celsius + "°C is " + fahrenheit + "°F")
        }
        case error(message): {
            resultLabel.config(text="Error: " + message)
        }
    }
})
convertButton.grid(row=1, column=1)

window.mainloop()
```

Try `100` → the label should show something like `100.0°C is 212.0°F`.
Try `abc` → an error label (message comes from the failed parse). Use
`str(...)` when building the label text: floats do not concatenate with
strings directly.

## 2. “Looks like a float” vs “is parseable as a float”

`parseFloat` is compact, and when you need the value anyway it is the
right tool — one parse, one `result`. That is **not** the same strategy as
hand-checking characters yourself.

A character scanner can define *exactly* what counts (optional `+`/`-`,
digits, at most one `.`). `parseFloat` delegates to the Python emit
target's float parser, which accepts a **wider** set: scientific notation
(`"1e10"`), `"inf"` / `"nan"`, underscores (`"1_000.5"`), and so on.

| Input | Strict scanner (digits / one dot) | `parseFloat` |
|---|---|---|
| `"3.14"` | accept | `ok(3.14)` |
| `"1e10"` | reject | `ok(1e10)` |
| `"inf"` / `"nan"` | reject | `ok` with those values |
| `"1_000.5"` | reject | `ok(1000.5)` |

So **"looks like"** and **"is parseable as"** are not automatically the
same. Choosing `parseFloat` is a trade-off: less code and one source of
truth for the value you will use, versus accepting the emit target's
broader rules. Prefer a hand-written check only when the form must enforce
a strict format you own.

If you only need a yes/no without keeping the value, you can still wrap
the same builtin:

```pys
function bool looksLikeFloat(string input) {
    result<float, string> parsed = parseFloat(input.strip())
    switch (parsed) {
        case ok(value): return true
        case error(message): return false
    }
}
```

For this converter we need the number, so `parseCelsius` returns the
`parseFloat` result directly — no second parse.

## 3. What this example is demonstrating, deliberately

- **`parseCelsius` is a plain function**, not a method on any class —
  this whole course has been, and remains, entirely procedural. It's
  called from inside the button's callback lambda, exactly like any
  other function call.
- **The `result<T,E>` from the error-handling chapters isn't just a
  console-program idea** — it fits naturally into GUI callbacks too. The
  callback reads a `result`, and a `switch` on `ok(...)`/`error(...)`
  decides what to display.
- **`columnspan=2`** is a small `.grid()` feature not covered yet:
  it lets a widget span more than one column, useful for a label meant
  to sit above two aligned columns rather than only occupying one.

## 4. Extending it

### Exercise

> Add a second `Entry` and `Button` pair below the first, converting
> Fahrenheit back to Celsius — reusing `parseFloat` (or a tiny
> `parseFahrenheit` that calls it) for parsing. Then: change
> `resultLabel`'s starting text to something that distinguishes "not
> converted yet" from "converted, result was an error" — using what you
> now know about `nullable<T>` versus a plain `string`, is a
> `nullable<string>` the right tool for that distinction here, or does
> the `result<T,E>` already flowing through this example cover it? Write
> one sentence justifying your answer before moving on.

## 5. Where to go from here

This concludes the procedural Tkinter course. Everything shown here —
widgets, `.pack()`/`.grid()`, `command`/`.bind()` callbacks as lambdas,
`result<T,E>` inside an event handler — remains valid PYS when you build
class-based GUIs later. What changes in those larger apps is
*organization*: instead of top-level statements holding every widget
as a local variable, an application becomes a `class` with widgets as
fields and callbacks as methods referencing `this`. The GUI concepts
themselves — the event loop, layout managers, reading widget state,
choosing between `nullable<T>` and `result<T,E>` for a given kind of
absence or failure — carry over completely unchanged.

Next: modern styling with **ttkbootstrap**, without rewriting the logic.

---

[Previous: Events and callbacks](gui_events.md) · [Next: Modern styling with ttkbootstrap](gui_ttkbootstrap_intro.md)
