# PYS syntax color schemes

Human-editable source of truth for PYS TextMate colors.

**Format (usage first, then stable role, then hex):**

```text
usage description → role #RRGGBB
```

- **usage** — human label (what you see in the editor / teaching notes)
- **role** — stable id the build script maps to TextMate scopes (`strings`, `types`, …)
- **#hex** — any color; names like Yellow/Green are *not* identifiers

Example: make strings green without renaming a role:

```text
Strings, text content → strings #50FA7B
```

Edit this file, then run `npm run prepare-bundle` (or `npm run apply-syntax-colors`).

**After install (end users):**

1. Command Palette → **PYS: Customize Syntax Colors** — color square + hex +
   **Use color** (live preview). This is the supported picker UI.
2. Settings → Extensions → **PYS** → Syntax colors — hex fields only (VS Code /
   Cursor Settings UI does not show color swatches for `format: "color"`).
   Descriptions link to the command above. Swatches also appear if you edit the
   same keys in `settings.json` with color decorators enabled.

Roles applied to highlighting: `comments`, `numbers`, `strings`, `functions`, `types`,
`language-constants`, `keywords`.  
Other roles (`background`, `selection`, `foreground`, `errors`, …) are documentation only.

---

## theme: dark

Main background → background #282A36
Current line / muted UI → current-line #6272A4
Text selection → selection #44475A
Default text → foreground #F8F8F2
Comments, disabled code → comments #6272A4
Errors, warnings, deletion → errors #FF5555
Numbers, constants, booleans → numbers #FFB86C
Strings, text content → strings #007328
Functions, methods → functions #20aae0
Classes, types (incl. primitives), support → types #20e0ca
this / super, named constants → language-constants #BD93F9
Keywords, storage modifiers, decorators → keywords #FF79C6

---

## theme: light

Main background → background #FFFBEB
Current line / muted UI → current-line #6C664B
Text selection → selection #CFCFDE
Default text → foreground #1F1F1F
Comments, disabled code → comments #6C664B
Errors, warnings, deletion → errors #CB3A2A
Numbers, constants, booleans → numbers #A34D14
Strings, text content → strings #846E15
Functions, methods → functions #14710A
Classes, types (incl. primitives), support → types #036A96
this / super, named constants → language-constants #644AC9
Keywords, storage modifiers, decorators → keywords #A3144D

---

## theme: high-contrast

Main background → background #000000
Current line / muted UI → current-line #9AA5CE
Text selection → selection #44475A
Default text → foreground #FFFFFF
Comments, disabled code → comments #9AA5CE
Errors, warnings, deletion → errors #FF5555
Numbers, constants, booleans → numbers #FFB86C
Strings, text content → strings #01720C
Functions, methods → functions #1575BE
Classes, types (incl. primitives), support → types #00FFFF
this / super, named constants → language-constants #BD93F9
Keywords, storage modifiers, decorators → keywords #FF79C6
