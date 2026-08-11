# CER-061: Settings UI syntax color pickers

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-11 |
| Scope | `pys-language/package.json` `pys.syntaxColors.*`; `syntax-colors-ui.js`; `syntax-color-picker.js`; `extension.js` |
| Builds on | [CER-060](CER-060-java-like-type-highlighting.md) role-based schemes |

## Context

After install, end users had no way to tweak PYS highlighting except editing
`editor.tokenColorCustomizations` JSON. Maintainers already edit
`syntax-color-schemes.md` at build time; students/teachers need a Settings
color picker (same UX as other IDE color fields).

### Pre-behavior

- Colors only via extension `configurationDefaults` + optional raw JSON
- No `pys.syntaxColors.*` settings

### Post-behavior

- Settings → Extensions → **PYS** exposes `format: "color"` hex fields for roles:
  comments, numbers, strings, functions, types, language constants, keywords
- **Important (host limitation):** the graphical Settings UI shows **hex text only** —
  VS Code/Cursor do not render color swatches there for `format: "color"`
  ([vscode#245848](https://github.com/microsoft/vscode/issues/245848) /
  [#106041](https://github.com/microsoft/vscode/issues/106041)). Swatches *do*
  appear when editing those keys in `settings.json` (color decorators), and in
  our dedicated picker UI.
- Command **PYS: Customize Syntax Colors** is the supported swatch UX: color
  square + hex per role, live preview while adjusting, **Use color** writes the
  Settings field and updates `editor.tokenColorCustomizations` immediately.
  Setting descriptions link to this command.
- Defaults shown in Settings come from the **dark** palette in
  `syntax-color-schemes.md` (synced by `apply-syntax-colors.js`)
- An explicit user/workspace value writes matching TextMate rules into
  `editor.tokenColorCustomizations` for dark / light / high-contrast
  (override applies to **all** themes until **Reset Setting**)
- Unrelated token rules (other languages) are preserved; managed PYS scope
  arrays are replaced as a unit
- **Reset Setting** clears the `pys.syntaxColors.*` value; activation sync
  removes managed overrides so per-theme extension defaults return
- **Packaging:** `ROLE_SCOPES` / `THEME_KEYS` live in packaged
  `syntax-color-roles.js`. Runtime UI must **not** `require('./scripts/…')` —
  `.vscodeignore` excludes `scripts/` from the VSIX; that crash killed
  `activate` (grammar still worked; diagnostics never registered).

### Evidence

- `pys-language/test/syntax-colors.test.js` (merge + package settings)
- `pys-language/test/packaging-runtime.test.js` (no `./scripts/` requires)
- Manual: Command Palette → **PYS: Customize Syntax Colors**
- Cursor exthost: `Extension activated success: remideboer.pys-language`

## Trade-offs

- One override color for all themes (simpler UX; not per-theme pickers)
- Writing `editor.tokenColorCustomizations` is the supported VS Code mechanism
  for TextMate foreground overrides (no separate runtime theme API)
- Preview while dragging writes Global token customizations; closing the panel
  re-syncs from saved `pys.syntaxColors.*` values
- Cannot put native swatches in the Settings form until the editor host adds
  that widget — do not treat missing Settings swatches as a stale VSIX
