# PYS Language Support 0.0.96

## Live diagnostics (unsaved buffer)

- Analyze uses the editor buffer (`--stdin`), not only the last saved file.
- Errors clear/update ~300ms after typing — no save required.

## Beginner-visible Error paint

- Error ranges get a red background highlight (plus overview ruler), not only a
  thin squiggle.

## `require` vs `requires`

- Host obligations must be spelled `requires` (exact).
- Typo `require` → clear error + quick fix to `requires`.
- `require` is not highlighted as a keyword.

## Install

Package with `vsce package` from `pys-language/`, then install the VSIX, or run
`install-extension.bat` from the repo root. **Reload Window** after install.
