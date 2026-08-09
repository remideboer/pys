# PYS Language Support 0.0.90

Trunk-based extension release. Tag: `extension-v0.0.90`.

Express REST shop on the JavaScript target, plus JS emit fixes needed to run
it from **Run Project**. Run `python tools/local_ci.py` before tagging.

## Highlights

- **Express shop examples:** `examples/by-target/javascript/rest-api/express/`
  — memory → mysql2 → JWT (ports 8190–8192); layered OO, no DIY HTTP stack.
- **JS emit:** map `express` (default import), `crypto` / `buffer`; `json` and
  `time` shims; entity `export`; dict/`self.` subscript fixes.
- **Deps Lock:** npm-only `pys.toml` explains that there is no `pys.lock`
  (packages install on Run).
- Continues 0.0.89: runtime ensure on Create Project / activate.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.90.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. For JavaScript Run/Debug, also install Node.js.
The pack includes the bundled transpiler.
