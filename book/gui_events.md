# 7.3. Events and callbacks

> This chapter uses lambdas. If you want the full treatment, see
> [Lambdas](chapter_5_2_lambdas.md). The short version: a lambda is a small,
> unnamed function you can pass around as a value — `() => print("hi")`
> is a lambda that, when called, prints `hi`. That's exactly what a
> button needs: something to call later, when it's clicked, not right
> now while the window is being built.

## 1. Connecting a button to a function

A `tk.Button` accepts a `command` argument: a value of type
`lambda<void>`, called exactly once per click.

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("A working button")

Label status = tk.Label(window, text="Not clicked yet")
status.pack()

Button myButton = tk.Button(window, text="Click me", command=() => {
    status.config(text="Clicked!")
})
myButton.pack()

window.mainloop()
```

Run it, click the button, and the label's text changes from
`Not clicked yet` to `Clicked!`. Walking through the new part:

- `command=() => { status.config(text="Clicked!") }` passes a lambda
  as the button's `command`. It takes no parameters (`()`), because
  Tkinter doesn't hand a button's command function any information about
  the click — it just calls it.
- The lambda body isn't executed when the window is built. It's stored
  by the button and only executed later, once, each time the user
  clicks — this is the event loop from the introduction chapter, made
  concrete: `mainloop()` is what actually calls this lambda, in reaction
  to the click event.
- `status.config(text="Clicked!")` changes a property of an
  **already-created** widget — this is how you update something on
  screen after the window is already showing, since you can't call
  `.pack()` a second time to "re-create" the label with new text.
- Capturing `status` in the lambda is fine: you are calling a method on
  the widget object, not reassigning the `status` variable itself.

## 2. Reading an `Entry` inside a callback

Combining this with widgets that hold input:

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("Greet me")

Entry nameEntry = tk.Entry(window)
nameEntry.grid(row=0, column=0)

Label greeting = tk.Label(window, text="")
greeting.grid(row=1, column=0)

Button greetButton = tk.Button(window, text="Greet", command=() => {
    string typedName = nameEntry.get()
    greeting.config(text="Hello, " + typedName + "!")
})
greetButton.grid(row=0, column=1)

window.mainloop()
```

Type a name, click **Greet**, and the label under the field shows
`Hello, <name>!`.

Notice `nameEntry.get()` is called **inside** the lambda, not before it —
this matters. If you called `.get()` once while building the window and
stored the result, you'd capture whatever the field held at that instant
(almost certainly empty, since the user hasn't typed anything yet). By
calling `.get()` inside the lambda, you read the field's value at the
moment of the click, which is what you actually want.

## 3. A field that starts genuinely empty: `nullable<T>`

Sometimes you want to distinguish "the user hasn't submitted anything
yet" from "the user submitted an empty answer." An `Entry`'s `.get()`
always returns a `string` — possibly an empty one, `""` — but it never
tells you "nothing has been submitted." For that distinction, keep your
own variable outside the widget, using `nullable<T>` exactly as
introduced in [Null and missing values](basics_null.md).

Because the callback **assigns** to that variable, mark it `shared`
(captured names are read-only unless `shared` or `atomic` — Session 5
covers this in depth for tasks; the same rule applies to GUI lambdas):

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("Last submitted name")

shared nullable<string> lastSubmitted = null

Entry nameEntry = tk.Entry(window)
nameEntry.grid(row=0, column=0)

Label status = tk.Label(window, text="Nothing submitted yet")
status.grid(row=1, column=0)

Button submitButton = tk.Button(window, text="Submit", command=() => {
    lastSubmitted = nameEntry.get()
    status.config(text="Last submitted: " + lastSubmitted)
})
submitButton.grid(row=0, column=1)

window.mainloop()
```

`lastSubmitted` starts as `null` — genuinely nothing, not an empty
string — and only becomes a real `string` once the button has actually
been clicked at least once. This is a small but honest example of why
`nullable<T>` earns its place even in a simple GUI: `""` (submitted, but
blank) and `null` (never submitted) are two different facts about your
program's state, and collapsing them into one would lose real
information — the same distinction taught with `null` in the basics
chapters, showing up again here in a GUI.

## 4. Binding to other events besides clicks

`command` on a button covers clicks specifically. For other kinds of
events — a key pressed inside an `Entry`, the mouse entering a widget —
Tkinter uses `.bind()` with an event name string:

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("Search on Enter")

Entry searchBox = tk.Entry(window)
searchBox.grid(row=0, column=0)
searchBox.bind("<Return>", (event) => {
    print("Search submitted: " + searchBox.get())
})

window.mainloop()
```

Focus the entry, type text, press Enter: the terminal prints
`Search submitted: <text>`. The lambda takes one parameter, `event`,
unlike the zero-parameter button `command` — `.bind()` always hands its
callback an event object describing what happened (which key, where the
mouse was, and so on), even if, as here, you don't end up using it.

### Exercise

> Extend the form from the widgets chapter (name, age, submit button).
> On submit, read both fields and display a single combined label:
> `"Name entered: <name>, Age entered: <age>"`. Then add a
> `shared nullable<string> lastName = null` variable outside the
> callback, set it inside the submit callback, and add a second button
> labeled `"Show last name"` whose callback checks: if `lastName` is
> `null`, show `"No submission yet"`; otherwise show the stored name.

---

[Previous: Widgets and layout](gui_widgets.md) · [Next: A small project: temperature converter](gui_project.md)
