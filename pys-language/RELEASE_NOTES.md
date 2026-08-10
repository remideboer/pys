# PYS Language Support 0.0.95

## Trait `uses` remaps inside string interpolations

- Multi-remap `uses Trait(req: field, …)` already remapped `this.req` in ordinary
  member access; **interpolations** (`"{this.req}"`) still emitted the trait
  require name and crashed at runtime.
- Python and JavaScript emit now rewrite remapped requires inside interpolated
  strings (and f-string returns). Regression covers the calculator-style sample.
- Teaching: `examples/traits.pys` + book traits chapter; CER-027 amended.

## Install

Package with `vsce package` from `pys-language/`, then install the VSIX, or run
`install-extension.bat` from the repo root. **Reload Window** after install.
