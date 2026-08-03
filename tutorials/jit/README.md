# JIT cards (just-in-time)

Open a card **when a task step needs a form or fix**. Do not read the whole folder first.

| Card | Use when you need… |
|------|--------------------|
| [J-declare](J-declare.md) | `int` / `var` / `const` / `fix` |
| [J-print-interpolate](J-print-interpolate.md) | `print`, `{x}`, `#i{x}` / `#s{…}` |
| [J-control](J-control.md) | `if` / `else` / `unless` |
| [J-switch](J-switch.md) | `switch` statement / expression, `continue` fall-through |
| [J-loop](J-loop.md) | `loop` forms |
| [J-function-import](J-function-import.md) | `function`, `import`, visibility |
| [J-class](J-class.md) | `class` / `interface` / `inherits` |
| [J-abstract](J-abstract.md) | `abstract class` / abstract methods / `void` |
| [J-trait](J-trait.md) | `trait` / `uses` / `requires`, collision override |
| [J-struct](J-struct.md) | `struct` / `fix struct`, construct, copy / `==` |
| [J-data](J-data.md) | `data` value objects (immutable, all-fields `==`) |
| [J-entity](J-entity.md) | `entity` + `identity(...)`, key equality |
| [J-lambda](J-lambda.md) | `=>` lambdas, `lambda<…>`, by-value capture |
| [J-atomic](J-atomic.md) | `atomic` vs `shared` (race-first pedagogy) |
| [J-debug](J-debug.md) | Breakpoints / step on `.pys` (DAP remap) |
| [J-enum](J-enum.md) | `enum`, `.value`, same-enum `==`, naming warning |
| [J-int-literals](J-int-literals.md) | `0b`/`0x`, width aliases, bitwise vs logical |
| [J-library](J-library.md) | external packages, `as` alias, generics on returns |
| [J-errors](J-errors.md) | decode common transpile messages |

After the card, return to the task immediately.
