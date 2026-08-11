# CER-060: Java-like primitive / type TextMate scopes

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-11 |
| Scope | `pys-language/syntaxes/pys.tmLanguage.json`; `package.json` tokenColorCustomizations; grammar tests |
| Inspired by | [vscode-java](https://github.com/redhat-developer/vscode-java) / [java.tmLanguage.json](https://github.com/microsoft/vscode/blob/main/extensions/java/syntaxes/java.tmLanguage.json) (`storage.type.primitive.java`) |

## Context

On field lines such as `private string name` / `private Heritage heritage`,
themes painted `string` like `private` because builtins used bare
`storage.type.pys` (often themed with the `storage.*` / keyword family), while
user types used `entity.name.type.pys`.

### Pre-behavior

- Builtins → `storage.type.pys`
- User types → `entity.name.type.pys` (+ optional semantic `pysType` → class)
- No shared type-color defaults beyond decorator rules

### Post-behavior

- Builtins → **`storage.type.primitive.pys`** (Java-style primitive scope; `var` stays `storage.type.pys`)
- Extension `configurationDefaults` force the **same foreground** for
  `storage.type.primitive.pys` and `entity.name.type*.pys` (dark / light / HC)
  from the canonical palette in
  [`pys-language/syntax-color-schemes.md`](../../pys-language/syntax-color-schemes.md)
  (usage-first lines under `theme: dark|light|high-contrast`; applied by
  `scripts/apply-syntax-colors.js` during `npm run prepare-bundle`)
  (Cyan for types; Pink for modifiers/keywords)
- Modifiers remain `storage.modifier.pys` (Pink — distinct from Cyan types)
- End-user color overrides: Settings pickers — [CER-061](CER-061-syntax-color-settings-ui.md)
- **Method decls:** return type requires whitespace before the name
  (`void greet` not `greet`→`gree`+`t`). Call sites `Type.method(` /
  `receiver.method(` use class/variable + `entity.name.function.pys`.

### Evidence

- `pys-language/test/grammar-fields.test.js`
- Manual: `requirements/area51.pys` field block + `Character.greet()`

## Trade-offs

- Does not port JDT semantic highlighting or QuickFixes (see CER-059 for QF hygiene)
- Forced type colors override theme defaults for those scopes (same pattern as existing decorator rules)
