# PYS Language Support 0.0.103

## Fix: extension activation (diagnostics were dead)

- Packaged VSIX excludes `scripts/`, but syntax-color UI required
  `./scripts/apply-syntax-colors.js` → **activate crashed** on every open of a
  `.pys` file. Language mode/highlighting still worked; Run/diagnostics did not.
- Role maps now live in packaged `syntax-color-roles.js`. Syntax-color setup is
  isolated so a UI failure cannot kill diagnostics.

## Install

Package/install the VSIX or run `install-extension.bat`, then **Reload Window**.
