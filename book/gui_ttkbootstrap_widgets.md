# 7.6. Styled widgets

Every widget you already know from the plain-Tkinter course has a
ttkbootstrap equivalent, using the exact same layout methods
(`.pack()`, `.grid()`) you already learned — only the widget's
*construction* changes, by way of an extra `bootstyle` argument.

## 1. Buttons with color variants

```pys
import ttkbootstrap as ttkb

Window window = ttkb.Window(themename="flatly")
window.title("Button styles")

Button primaryButton = ttkb.Button(window, text="Primary", bootstyle="primary")
primaryButton.pack(pady=10)

Button successButton = ttkb.Button(window, text="Success", bootstyle="success")
successButton.pack(pady=10)

Button dangerButton = ttkb.Button(window, text="Danger", bootstyle="danger")
dangerButton.pack(pady=10)

window.mainloop()
```

Run it: three stacked buttons in primary / success / danger colors under
the `flatly` theme.

`bootstyle` accepts a small vocabulary of semantic names —
`"primary"`, `"secondary"`, `"success"`, `"danger"`, `"warning"`,
`"info"` — rather than a raw color value. This mirrors how you already
think about button *meaning* rather than button *appearance*: a
`"danger"`-styled button is understood, at a glance, to represent a
destructive or irreversible action (deleting something, cancelling
permanently), regardless of which specific theme is active. Changing the
window's `themename` later automatically adjusts what each semantic
style actually looks like, without touching a single widget's code.

`pady=10` is new: it adds 10 pixels of vertical padding around the
widget, which `.pack()` and `.grid()` both accept — worth adding here
purely so the three buttons aren't crammed together, unrelated to
ttkbootstrap itself.

## 2. Entries and labels

```pys
import ttkbootstrap as ttkb

Window window = ttkb.Window(themename="flatly")
window.title("Styled form")

Label nameLabel = ttkb.Label(window, text="Name:")
nameLabel.grid(row=0, column=0, padx=5, pady=5)

Entry nameEntry = ttkb.Entry(window, bootstyle="primary")
nameEntry.grid(row=0, column=1, padx=5, pady=5)

window.mainloop()
```

Compare this directly to the plain-Tkinter form from the widgets
chapter: the structure — `Label` then `Entry`, `.grid()` with `row`/
`column` — is unchanged. Only the class prefix (`ttkb.` instead of
`tk.`) and the optional `bootstyle` argument differ.

## 3. Outline vs. solid variants

Appending `"-outline"` to a `bootstyle` name gives a button an outlined
rather than solid-fill appearance — useful for a visual hierarchy where
one action should stand out (solid) and a secondary action shouldn't
compete with it (outline):

```pys
import ttkbootstrap as ttkb

Window window = ttkb.Window(themename="flatly")
window.title("Outline vs solid")

Button saveButton = ttkb.Button(window, text="Save", bootstyle="success")
saveButton.pack(side="left", padx=5)

Button cancelButton = ttkb.Button(window, text="Cancel", bootstyle="secondary-outline")
cancelButton.pack(side="left", padx=5)

window.mainloop()
```

`side="left"` is another `.pack()` option: it places widgets
side-by-side instead of the default top-to-bottom stacking, useful for a
row of buttons like this pair.

### Exercise

> Rebuild the name/age form from the widgets chapter using `ttkb.Label`
> and `ttkb.Entry`, with a `"primary"`-styled submit button and a
> `"secondary-outline"`-styled cancel button placed side by side beneath
> the two fields. Try at least two different `themename` values and
> note which one you'd actually choose for a real application, and why.

---

[Previous: Modern styling with ttkbootstrap](gui_ttkbootstrap_intro.md) · [Next: Restyling the temperature converter](gui_ttkbootstrap_project.md)
