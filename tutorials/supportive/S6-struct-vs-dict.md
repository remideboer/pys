# S6 — Struct vs dict vs class

## The idea

| Need | Prefer |
|------|--------|
| Fixed schema, nominal type, value copy / `==` by fields | `struct` |
| Open keys, heterogeneous payload, Python interop | `dict` |
| Behavior, identity, inheritance / interfaces | `class` |

## Side by side

```pys
package struct Damage {
    int amount
    string type
}

Damage d = Damage(20, "physical")
d.amount = 21
print(d == Damage(amount=21, type="physical"))
```

```pys
dict bag = {"amount": 20, "type": "physical"}
bag["amount"] = 21
```

```pys
class Unit {
    private int health
    public Unit(int health) {
        this.health = health
    }
    public takeDamage(Damage damage) {
        this.health = this.health - damage.amount
    }
}
```

## Design differences

- **Copy:** struct args/assigns are copies; mutating a parameter does not change the caller. Dict and class instances are shared by reference in the usual Python sense after emit.  
- **Schema:** struct fields are declared; dict keys are open.  
- **Null:** struct fields reject `null`; dict values may be `None`.  
- **Hash:** only all-`fix` / `fix struct` types are hashable.  
- **Access:** struct **fields** are always public; control who can import the type with `global` / `package` / `module` on the struct. Dict keys have no access control; class fields use per-member modifiers.

## Tie-in

Forms: [JIT: struct](../jit/J-struct.md). Responsibility model: [S5](S5-objects-as-responsibility.md).
