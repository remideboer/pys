# Temperature converter — ttkbootstrap (procedural)

Book twin for [gui_ttkbootstrap_project.md](../../../book/gui_ttkbootstrap_project.md).
Same Celsius→Fahrenheit logic as `../temperature_tk/`, with themed widgets.

From this folder (so the local lock is used):

```bash
cd examples/gui/temperature_ttkbootstrap
python -m transpiler deps lock pys.deps
python -m transpiler run main.pys
```

Or from the repo root with an explicit workspace:

```bash
set PYS_WORKSPACE_ROOT=%CD%\examples\gui\temperature_ttkbootstrap
python -m transpiler run examples/gui/temperature_ttkbootstrap/main.pys
```
