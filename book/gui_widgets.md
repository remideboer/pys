# 7.2. Widgets and layout

A **widget** is any visible element inside a window: a label, a button, a
text field. Every widget you create needs two things: the widget itself,
and an instruction for *where* to place it in the window — creating a
widget alone does not make it appear.

## 1. Labels — displaying text

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("Labels")

Label greeting = tk.Label(window, text="Hello there!")
greeting.pack()

window.mainloop()
```

Run it: a window titled "Labels" shows the text `Hello there!`.

`tk.Label(window, text="Hello there!")` creates the widget, and takes
`window` as its first argument — every widget needs to know which window
(or which container inside a window) it belongs to. `greeting.pack()` is
the placement instruction: `.pack()` is the simplest of Tkinter's layout
managers, and simply stacks widgets one after another, in the order you
call `.pack()` on them.

## 2. Buttons and layout ordering

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("Buttons")

Label greeting = tk.Label(window, text="Click the button below")
greeting.pack()

Button myButton = tk.Button(window, text="Click me")
myButton.pack()

window.mainloop()
```

The label appears above the button, because `greeting.pack()` was called
first. `.pack()`'s default behavior stacks top to bottom in call order —
this is worth testing directly. Clicking the button does nothing yet
(no `command`); that comes in the next chapter.

### Exercise

> Swap the two `.pack()` calls so the button is created and packed
> before the label. Run it and confirm the button now appears above the
> label. This confirms: layout order in Tkinter's `.pack()` is
> **call order**, not the order widgets were declared as variables.

## 3. `.grid()` — precise row/column placement

`.pack()` is fine for simple stacking, but falls apart quickly once you
need a form-like layout — a label next to its input field, several rows
of these, aligned. `.grid()` places each widget at an explicit row and
column instead:

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("A simple form")

Label nameLabel = tk.Label(window, text="Name:")
nameLabel.grid(row=0, column=0)

Entry nameEntry = tk.Entry(window)
nameEntry.grid(row=0, column=1)

Label ageLabel = tk.Label(window, text="Age:")
ageLabel.grid(row=1, column=0)

Entry ageEntry = tk.Entry(window)
ageEntry.grid(row=1, column=1)

window.mainloop()
```

`tk.Entry` is a single-line text field the user can type into. Two rows,
two columns, four widgets — each one explicitly told exactly where it
belongs, independent of the order the code creates them in.

> **Important**: never mix `.pack()` and `.grid()` inside the *same*
> container widget. Tkinter will raise an error. Pick one layout manager
> per container and stay consistent — this is a common early source of
> confusing crashes.

## 4. Reading a value out of a widget

A widget isn't just something to look at — it holds state you can read.
`tk.Entry` has a `.get()` method returning whatever text is currently
typed into it:

```pys
import tkinter as tk

Tk window = tk.Tk()
window.title("Reading input")

Entry nameEntry = tk.Entry(window)
nameEntry.grid(row=0, column=0)

Button showButton = tk.Button(window, text="Show name")
showButton.grid(row=0, column=1)

window.mainloop()
```

This window doesn't *do* anything with the button yet — clicking it has
no effect, because nothing has told it what function to call. That's the
subject of the next chapter: connecting a widget to a function so
something actually happens on click.

### Exercise

> Build the two-row form from §3 (name and age), and add a third row
> with a `tk.Button` labeled `"Submit"`. Don't worry about making the
> button do anything yet — just get all three rows correctly aligned in
> their columns using `.grid()`.

---

[Previous: GUI programming with Tkinter — introduction](gui_intro.md) · [Next: Events and callbacks](gui_events.md)
