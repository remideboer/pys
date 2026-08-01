# Practice — Struct vs dict; fix mutability

Time-box: 5–10 minutes.

## 1. Pick the type

For each need, write `struct`, `dict`, or `class`:

1. Hit points + damage kind, compared by value, no methods  
2. JSON blob from an HTTP API with unknown keys  
3. Game unit that can `takeDamage` and track private health  

## 2. Fix the broken program

This should fail to transpile — repair it so `d` stays immutable and construction stays legal:

```pys
struct Damage {
    int amount
    string type
}

fix Damage d = Damage(20, "physical")
d.amount = 21
```

Also illegal (fields have no access modifiers):

```pys
struct Damage {
    public int amount
}
```

## Check

1 → struct · 2 → dict · 3 → class  
Repair: remove the field write (or drop `fix` on the binding if mutation is intentional).  
Drop `public` on struct fields; use `package struct` / `global struct` when exporting the type.
