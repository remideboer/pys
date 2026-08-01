# JIT — Structs

## Forms

```pys
package struct Damage {
    int amount
    string type
}

fix struct Point {
    int x
    int y
}

Damage d1 = Damage(20, "physical")
Damage d2 = Damage(amount=20, type="physical")
fix Damage d3 = Damage(21, "physical")
var d4 = Damage(20, "electric")

print(d1 == d2)
d1.amount = 21
```

## Rules

1. Fields only — no methods, no `inherits` / `implements` / `sealed`  
2. Fields are always public; put `global` / `package` / `module` on the **struct**  
3. Construct with `Type(...)` (positional or named); never `new`  
4. Assignment / call / return **copy** the value  
5. `fix` on a field, binding, or `fix struct` freezes writes as documented in [LANGUAGE](../../docs/LANGUAGE.md)  
6. `==` compares fields  

Bag of fields without behavior → **struct**. Behavior / inheritance → **class** ([J-class](J-class.md)).  
When to prefer `dict`: [S6](../supportive/S6-struct-vs-dict.md).
