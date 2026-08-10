# PYS Language Support 0.0.97

## IntelliSense (analysis-driven)

- After `.`, show accessible members (private only inside the type).
- In-scope identifiers ranked near → far (locals, params, fields, types).
- Status bar **PYS IntelliSense** toggles `pys.intellisense.enabled`.

## Create Class from call

- Unresolved `Student st = Student(naam="Jaap")` → lightbulb / command
  **Create Class from Call** scaffolds fields + `public constructor(...)`.
- Named arguments only in this release; literal types inferred when possible.

## Install

Package/install the VSIX or run `install-extension.bat`, then **Reload Window**.
