# PYS Language Support 0.0.87

Trunk-based extension release. Tag: `extension-v0.0.87`.

Adds a selectable **JavaScript / Node** emit target for Run (MVP teaching
surface). Python remains the reference backend and the only Debug target.
Run `python tools/local_ci.py` before tagging.

## Highlights

- **Emit target selector:** workspace setting `pys.emitTarget`
  (`python` | `javascript`), status bar `PYS → Python|Node`, and command
  `pys.selectEmitTarget` (QuickPick).
- **Run** passes `--target` to `python -m transpiler run …`. JavaScript
  writes temp `.mjs` and executes with **Node** on PATH (ADR-030 / CER-050).
- **Debug** stays Python-only; choosing JavaScript shows a clear message
  instead of starting debugpy.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.87.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. For JavaScript Run, also install Node.js.
The pack includes the bundled transpiler.
