# PYS Language Support 0.0.84

Trunk-based extension release. Tag: `extension-v0.0.84`.

Republish of 0.0.83 after a pinned extension test still expected `0.0.81`.
The manifest test now checks that `RELEASE_NOTES.md` names the current
`package.json` version instead of a hard-coded string.

## Highlights

Same language/IDE surface as 0.0.81+:

- **`constructor`**, **`open` / `override` / `closed`**, **`static`**
- Optional **Navigate Library Sources** (`pys.navigateLibrarySources`)
- Bundled transpiler with transitive `pys.lock` recognition and CI-safe
  MySQL shop transpile stubs

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.84.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
