# PYS Language Support 0.0.92

Trunk-based extension release. Tag: `extension-v0.0.92`.

Extension and `.pys` file icons: braces + eye (U+1F441). Run
`python tools/local_ci.py` before tagging.

## Highlights

- **Icons:** marketplace, activity bar, and `.pys` file icons use `{ 👁 }`
  (braces + eye U+1F441); light/dark file variants.
- Continues 0.0.91: private access in interpolations; brace indent (`pys.indent`).

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.92.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. For JavaScript Run/Debug, also install Node.js.
The pack includes the bundled transpiler.
