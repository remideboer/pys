# PYS Language Support 0.0.83

Trunk-based extension release. Tag: `extension-v0.0.83`.

Republish after 0.0.82 CI still failed on Linux: shop MySQL/JWT transpile
gates relied on a locally installed `mysql.connector`, which GitHub runners
do not have once `pys.toml` stops parent lock discovery.

## Highlights

Same language/IDE surface as 0.0.81–0.0.82:

- **`constructor`**, **`open` / `override` / `closed`**, **`static`**
- Optional **Navigate Library Sources** (`pys.navigateLibrarySources`)
- Bundled transpiler with transitive `pys.lock` recognition for analysis
  and CI stubs for MySQL shop examples without a live deps env

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.83.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
