# PYS Language Support 0.0.80

Trunk-based extension release. Tag: `extension-v0.0.80`.

## Highlights

- **`var` is declaration-only** — `var name = expr` stays for locals and
  script-top inference. Using `var` as a return type, parameter type, field
  type, or generic argument is rejected (`pys.var-as-type`) with tips and IDE
  quick fixes ([ADR-025](../docs/adr/ADR-025-var-declaration-only.md) /
  [CER-042](../docs/evolution/CER-042-var-declaration-only.md)).
- **`object` type** — opaque foreign values (sockets, locks, driver cells);
  anything may assign into `object`. Parameter types may still be omitted at
  foreign boundaries.
- **Examples / book** — production-style webserver and shop examples migrated
  off type-position `var`; beginner chapters document the illegal positions.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.80.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
