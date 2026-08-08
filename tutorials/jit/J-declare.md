# JIT — Declarations

## Forms

```pys
int n = 3
float t = 20.5
string label = "probe-A"
bool ok = true
char grade = 'B'
var inferred = n + 1
const int MAX = 10
fix int locked = n + MAX
```

## Rules (procedural)

1. Typed name: `type name = expression`  
2. `var` — declaration form only (`var name = expression`); type comes from the initializer (must be inferable). Not a return/param/field type.  
3. `const` — compile-time constant; do not reassign  
4. `fix` — assign once from an expression, then locked  
5. Foreign/opaque values → type `object`, or omit a parameter type at that boundary  

## Not here

*Why* types matter → [S1](../supportive/S1-pys-as-contract.md)
