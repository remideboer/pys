# JIT — Common errors

| Message pattern | Likely fix |
|-----------------|------------|
| Typed interpolation `#s{}` requires string, but … is int | Change marker (`#i`) or convert/ redesign type |
| Cannot find module 'X' | Wrong name/path; add `.pys` neighbor; or stdlib/`pys.deps` package |
| Cannot import 'f' … module-scoped | Export with `package`/`global`, or don’t import it |
| Unknown type 'T' | Declare class/interface, or import library type / use primitive |
| Loop counter … immutable | Don’t assign to the C-style loop variable inside the body |
| Use `var` instead of `let` | `let` is rejected — use `var` |
| Class methods must not use `function` | `public name()` not `public function name()` |
| `ok(...)` / `err(...)` needs an expected `result<T, E>` type | Declare a result binding, pass it to a result parameter, or return it from a result function |
| `propagate` only applies to result values | Remove `propagate`, or change the called API to return `result<T,E>` |
| `propagate` requires an enclosing function that returns `result<T, E>` | Change the function return type, or handle with an exhaustive result `switch` |
| Cannot propagate error type … | Use exactly the same `E`, or explicitly convert the error before returning |
| Result switch is not exhaustive | Add the missing `case ok(value)` / `case err(error)`, or add `default` |
| Entrypoint conflicts with `[project].main` | Run the configured entrypoint or use **PYS: Set as entrypoint** |
| `PYS panic: …` | An error reached the entrypoint; read the following PYS propagation sites and handle it earlier if recovery is possible |

Pipeline model: [S2](../supportive/S2-transpile-mental-model.md)
