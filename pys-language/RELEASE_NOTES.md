# PYS Language Support 0.0.86

Trunk-based extension release. Tag: `extension-v0.0.86`.

Republish of the 0.0.85 surface after publish CI failed on a stale
`RELEASE_NOTES` keyword assert (`/static/`). Notes now only need to name the
current version; grammar / `extension.js` tests still cover lasting keywords.
Run `python tools/local_ci.py` before tagging.

## Highlights

- **Named call arguments** for functions, methods, and class constructors:
  all-positional **or** all-named — mixing is a compile error (CER-048).
  Example: `greet(times=2, name="Ada")`.
- **Generic constructors** no longer false-fail when call-site type args are
  erased (`Pair<Car, Truck>(car, truck)` compiles again).
- Contributor tooling: `tools/local_ci.py` (pytest + `pys-language` npm test)
  and updated [`docs/ci-failure-patterns.md`](../docs/ci-failure-patterns.md).

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.86.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
