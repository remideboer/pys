# 7.5. Modern styling with ttkbootstrap

> This short series assumes you've completed the procedural Tkinter
> course, including the [temperature converter project](gui_project.md).
> Nothing about widgets, layout, or event handling changes here — this
> is purely about making the same applications look considerably more
> modern, with only small code changes.

## 1. Why a separate library for this

Plain Tkinter widgets — `tk.Button`, `tk.Entry` — render using your
operating system's oldest, plainest widget style. `ttk` (Tkinter's own
"themed" widget set, still part of the Python standard library) improves
this somewhat by using platform-native styling, but doesn't offer the
flat, colorful, Bootstrap-like look common in modern web and desktop
apps. **ttkbootstrap** solves this: it's a theming layer built on top of
`ttk`, providing ready-made, professional-looking themes and simple
color-variant styling for every standard widget, without inventing a
new, incompatible widget API the way some alternatives do.

ttkbootstrap is a third-party package. In a PYS project you declare it in
`pys.toml` and lock it (same pattern as PyQt in the examples tree), then
run from that project folder so `PYS_WORKSPACE_ROOT` picks up the lock:

```toml
[interpreter]
version = ">=3.10"

[dependencies]
ttkbootstrap = { version = "1.10.1", build = "run" }
```

```bash
python -m transpiler deps lock
python -m transpiler run main.pys
```

A complete silo is under
[`examples/gui/temperature_ttkbootstrap/`](../examples/gui/temperature_ttkbootstrap/).

ttkbootstrap is MIT-licensed — free to use, including commercially.

## 2. Your first ttkbootstrap window

```pys
import ttkbootstrap as ttkb

Window window = ttkb.Window(themename="flatly")
window.title("Styled window")
window.geometry("300x150")

window.mainloop()
```

The only structural difference from the plain-Tkinter version: instead
of `tk.Tk()`, you create a `ttkb.Window`, and you pass it a
`themename` — the single choice that determines the entire application's
color scheme and widget appearance from that point on. Everything else
you already know (`.title()`, `.geometry()`, `.mainloop()`) works
identically, because `ttkb.Window` is built as a drop-in replacement for
`tk.Tk`. Declare the type as `Window`, not `ttkb.Window`.

### A few themes to try

| Theme name | Look |
|---|---|
| `"flatly"` | Clean, light, blue accents — a common default |
| `"darkly"` | Dark mode, high contrast |
| `"cosmo"` | Light, rounded, soft colors |
| `"superhero"` | Dark, bold accent colors |

### Exercise

> Run the example above with `themename="flatly"`, then change it to
> `"darkly"` and run it again. Nothing else in the code changes — note
> exactly what does and doesn't visually change between the two runs.

---

[Previous: A small project: temperature converter](gui_project.md) · [Next: Styled widgets](gui_ttkbootstrap_widgets.md)
