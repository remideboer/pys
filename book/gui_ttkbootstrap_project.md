# 7.7. Restyling the temperature converter

The clearest way to see what ttkbootstrap changes — and, just as
importantly, what it *doesn't* — is to take the finished capstone
project from the procedural Tkinter course and restyle it, without
touching any of its logic.

A runnable twin lives at
[`examples/gui/temperature_ttkbootstrap/`](../examples/gui/temperature_ttkbootstrap/).

## 1. Side by side

**Before (plain Tkinter):** same `parseCelsius` / `parseFloat` helpers and
layout as [gui_project.md](gui_project.md) — only the import and widget
constructors differ below.

**After (ttkbootstrap):**

```pys
import ttkbootstrap as ttkb

function result<float, string> parseCelsius(string input) {
    return parseFloat(input.strip())
}

Window window = ttkb.Window(themename="flatly")
window.title("Celsius to Fahrenheit")

Label instructions = ttkb.Label(window, text="Enter a temperature in Celsius:")
instructions.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

Entry celsiusEntry = ttkb.Entry(window)
celsiusEntry.grid(row=1, column=0, padx=10, pady=5)

Label resultLabel = ttkb.Label(window, text="", bootstyle="info")
resultLabel.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

Button convertButton = ttkb.Button(window, text="Convert", bootstyle="primary", command=() => {
    result<float, string> parsed = parseCelsius(celsiusEntry.get())
    switch (parsed) {
        case ok(celsius): {
            float fahrenheit = celsius * 9 / 5 + 32
            resultLabel.config(text=celsius + "°C is " + fahrenheit + "°F", bootstyle="success")
        }
        case error(message): {
            resultLabel.config(text="Error: " + message, bootstyle="danger")
        }
    }
})
convertButton.grid(row=1, column=1, padx=10, pady=5)

window.mainloop()
```

Same trials as the plain converter: `100` → success-styled result text;
`abc` → danger-styled error text.

## 2. What changed, and what deliberately didn't

| Changed | Unchanged |
|---|---|
| `import tkinter as tk` → `import ttkbootstrap as ttkb` | `parseCelsius` / `parseFloat` — identical |
| `tk.Tk()` → `ttkb.Window(themename="flatly")` | The `result<T,E>` / `switch` / `ok`/`error` pattern inside the callback |
| `tk.Label`/`tk.Entry`/`tk.Button` → `ttkb.Label`/`ttkb.Entry`/`ttkb.Button` | `.grid(row=..., column=...)` positions |
| Added `bootstyle` to the button and, dynamically, to the result label | The lambda passed as `command` |
| Added `padx`/`pady` for breathing room between widgets | The event loop, `.mainloop()` |

The result label's `bootstyle` is set **dynamically, inside the
callback** — `"success"` on a valid conversion, `"danger"` on a parse
error. This is a meaningful use of styling, not just decoration: the
color itself now carries information the user can register at a glance,
before even reading the text — a valid result looks distinctly different
from an error, reinforcing the same `ok`/`error` distinction your code is
already making, visually.

## 3. The broader lesson

This restyling exercise demonstrates something worth stating explicitly:
**presentation and logic are separable**, and a well-structured program
makes that separation easy rather than painful. `parseCelsius` didn't
need to change at all to support an entirely different visual library —
because it never depended on Tkinter in the first place; it's a plain
function operating on `string`, `float`, and `result<T,E>`. Only the
top-level UI wiring (window and widgets) needed touching. The
same principle shows up again in class-based GUI examples later: keeping
application logic independent of *how* it is displayed makes a change
like "we're switching UI libraries" a small, contained edit instead of a
rewrite.

### Exercise

> Take your extended converter from the procedural course's exercise
> (the one with both Celsius→Fahrenheit and Fahrenheit→Celsius). Restyle
> it fully with ttkbootstrap, using `"success"`/`"danger"` result
> styling for both directions, and pick a `themename` other than
> `"flatly"`. Confirm for yourself that, once again, neither parsing
> function needed to change.

---

[Previous: Styled widgets](gui_ttkbootstrap_widgets.md) · [Next: Session 5 — Doing several things at once](chapter_6_session_concurrency.md)
