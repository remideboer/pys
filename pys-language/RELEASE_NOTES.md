# PYS Language Support 0.0.81

Trunk-based extension release. Tag: `extension-v0.0.81`.

## Highlights

- **`constructor` keyword** — write `public constructor(...)` on class and
  entity (not the type name). `this(...)` chains overloads;
  `super(...)` / implicit zero-arg `super()` for parents
  ([ADR-027](../docs/adr/ADR-027-constructor-keyword.md)).
- **`open` / `override` / `closed`** — methods closed by default; mark
  sockets with `open`, plug in with `override` or `override closed`;
  `closed class` blocks further inherits (replaces `sealed`)
  ([ADR-028](../docs/adr/ADR-028-open-override-closed.md)).
- **`static` members** — class-wide fields and methods; no `this` inside
  static methods; incompatible with `open`/`override`
  ([ADR-029](../docs/adr/ADR-029-static-members.md)).
- **IDE** — keyword highlight, hover, completions, indent-on-enter, and
  snippets for constructor / open / override / closed class / static;
  entity and trait-`uses` snippets updated to `constructor`.
- **Bundled transpiler** — includes the language changes above (plus prior
  `var`-as-type / `object` work from 0.0.80).

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.81.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
