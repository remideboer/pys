# Drill — Declarations

Pick one binder for each intent: `const`, `fix`, `var`, or a plain typed binding (`int …`).

1. Math π used across the project, never reassigned.  
2. `total` computed once from `a + b`, then must not change.  
3. Loop index you update yourself in a while-style loop.  
4. Temperature reading you may overwrite each sample.  
5. A flag inferred from `n > 0` where you do not want to repeat the type name.

## Check

1 `global const` or `const` · 2 `fix` · 3 typed `int` (not const/fix) · 4 typed `float` · 5 `var`

Forms: [JIT declare](../jit/J-declare.md)
