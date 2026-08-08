# PYS Language Support 0.0.85

Trunk-based extension release. Tag: `extension-v0.0.85`.

## Highlights

- **Named call arguments** for functions, methods, and class constructors:
  all-positional **or** all-named — mixing is a compile error (CER-048).
  Example: `greet(times=2, name="Ada")`.
- **Generic constructors** no longer false-fail when call-site type args are
  erased (`Pair<Car, Truck>(car, truck)` compiles again).
- Contributor note: recurring CI gates documented in
  `docs/ci-failure-patterns.md` (showcase `examples/main.pys`, lock isolation,
  book/railroad sync).

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.85.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
