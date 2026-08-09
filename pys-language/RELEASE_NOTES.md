# PYS Language Support 0.0.89

Trunk-based extension release. Tag: `extension-v0.0.89`.

Host **runtime ensure**: probe Python/Node on PATH, prompt curated installs,
and pick emit target when creating a project. Run `python tools/local_ci.py`
before tagging.

## Highlights

- **Create Project target:** QuickPick Python or JavaScript; writes
  `[project].target` into the new `pys.toml`.
- **PATH probe + install:** on activate, Create Project, Run, and Select Emit
  Target — missing Python (always) or Node (JavaScript) offers **Install** with
  a stable version list (`winget` / `brew` / docs; trusted workspace only,
  ADR-001 / CER-051).
- Continues 0.0.88: JavaScript emit, Run Project, unified `pys.toml` deps.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.89.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH (or install via the new prompt). For JavaScript
Run/Debug, also install Node.js. The pack includes the bundled transpiler.
