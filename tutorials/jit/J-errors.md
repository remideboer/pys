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

Pipeline model: [S2](../supportive/S2-transpile-mental-model.md)
