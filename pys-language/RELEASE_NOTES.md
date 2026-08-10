# PYS Language Support 0.0.91

Trunk-based extension release. Tag: `extension-v0.0.91`.

Private/protected access and brace indentation now fail closed where students
hit them (string interpolations; misaligned 4-space grid). Run
`python tools/local_ci.py` before tagging.

## Highlights

- **Member access:** private/protected reads denied in string / typed
  interpolations (`Access denied`), not only bare assigns; negative regression
  corpus (`tests/test_member_access.py`, `requirements/rekenmachine.pys`).
- **Indentation (`pys.indent`):** brace-mode siblings and nests must stay on a
  4-space grid; transpile error + IDE **Fix indentation** CodeAction.
- Continues 0.0.90: Express REST shop (JS) and npm-only Deps Lock messaging.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.91.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. For JavaScript Run/Debug, also install Node.js.
The pack includes the bundled transpiler.
