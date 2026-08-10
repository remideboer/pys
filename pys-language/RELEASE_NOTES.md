# PYS Language Support 0.0.94

Trunk-based extension release. Tag: `extension-v0.0.94`.

Foreach binders require a typed element that matches the collection. Run
`python tools/local_ci.py` before tagging.

## Highlights

- **Foreach types:** `loop (T x in xs)` — binder type is required; must match
  array/`list`/`set`/`dict` element types (`pys.foreach-type-required`,
  `pys.foreach-type`). CER-054.
- Continues 0.0.93: P-eyes icons; 0.0.91 access + indent.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.94.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. For JavaScript Run/Debug, also install Node.js.
The pack includes the bundled transpiler.
