# PYS Language Support 0.0.88

Trunk-based extension release. Tag: `extension-v0.0.88`.

Ships the **JavaScript / Node** emit backend with teaching-core parity,
unified `pys.toml` deps, **Run Project** from the manifest, and Debug for
both Python and JavaScript. Run `python tools/local_ci.py` before tagging.

## Highlights

- **JavaScript emit target:** `pys.emitTarget` / status bar selector; Run and
  Debug pass `--target python|javascript` (ADR-030 / CER-050). Node DAP via
  `pwa-node` + shared line-map remapping.
- **Unified `pys.toml`:** `[interpreter]`, `[dependencies]`, and
  `[dependencies.npm]` in one file; central npm cache under
  `~/.pys/repository/npm/` (no student silo `package.json`).
- **Run Project:** right-click `pys.toml` → **Run Project** runs
  `[project].main` using optional `[project].target` (default `python`).
- **Brace-scope fix:** indexed assigns such as `this.map[c.getId()] = c`
  rewrite loop binders on the LHS (CER-015).

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.88.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. For JavaScript Run/Debug, also install Node.js.
The pack includes the bundled transpiler.
