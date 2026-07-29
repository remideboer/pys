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
2. `var` — type comes from the initializer (must be inferable)  
3. `const` — compile-time constant; do not reassign  
4. `fix` — assign once from an expression, then locked  

## Not here

*Why* types matter → [S1](../supportive/S1-pys-as-contract.md)
