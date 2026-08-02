## PYS Language Specification — Traits

### 1. Overview

A trait is a named, always-public collection of methods that provides reusable behavior to classes without participating in the single-inheritance hierarchy. Traits sit between interfaces and abstract classes: like an interface, a trait may declare members it does not implement (`requires`); like an abstract class, a trait provides executable method bodies with direct access to host-instance state via `this`. Unlike abstract classes, a trait cannot be instantiated, carries no constructor, and multiple traits may be composed onto a single class via `uses`.

### 2. Grammar (EBNF extension)

```ebnf
(* ------------------------- Traits ------------------------- *)

trait_decl        = [ top_visibility ] , "trait" , identifier ,
                    "{" , { trait_member } , "}" ;

trait_member      = trait_method_decl | trait_requires ;

trait_method_decl = [ return_type ] , identifier ,
                    "(" , [ parameter_list ] , ")" , block ;
(* No member_access keyword: traits are always public.
   Body has direct access to host-instance state via `this`. *)

trait_requires    = "requires" , ( type_name , identifier
                                  | return_type , identifier ,
                                    "(" , [ parameter_list ] , ")" ) ;
(* Declares a field or method the host class must supply.
   No implementation here — analogous to an "excluded method" in
   classical trait composition (Schärli et al., 2003). *)
```

Amendment to `class_decl`:

```ebnf
class_decl        = [ top_visibility ] , [ "sealed" ] , "class" , identifier ,
                    [ type_params ] ,
                    [ ( "inherits" | "super" ) , identifier ] ,
                    [ "uses" , identifier , { "," , identifier } ] ,
                    [ "implements" , identifier , { "," , identifier } ] ,
                    class_body ;
```

`uses` is positioned between `inherits`/`super` and `implements` to reflect resolution order: base-class members first, then trait-supplied members, then the interface contract check.

### 3. Static semantics

1. **Statelessness of the trait itself**: a trait declares no fields of its own. All state is accessed exclusively through `this`, resolved against the host class at composition time.
2. **`requires` obligation**: for every class `C uses T`, the compiler verifies that `C` (directly, or via an ancestor in its `inherits` chain) supplies a member matching each `requires` entry in `T` by name, type, and — for methods — parameter signature. Failure is a compile-time error:
   `C uses T but does not provide 'name' (string), required by trait T`.
3. **Collision rule**: if two traits used by the same class each define a method with the same name, the class must provide an explicit override that disambiguates (e.g. `TraitA.method(this)`); the compiler must reject silent resolution. This mirrors the classical trait requirement that composition conflicts be resolved by the programmer, not by implicit scoping rules.
4. **Composition order independence**: `uses A, B` and `uses B, A` must be semantically equivalent when no collision exists — trait composition is commutative and associative, consistent with the formal trait model.
5. **No instantiation, no constructor**: `trait` cannot appear in a `constructor_call`; it has no canonical constructor form, unlike `struct`.
6. **Not a type for polymorphism**: a trait name cannot appear in `implements`, `type_expr`, or as a parameter type — it is a composition mechanism, not a nominal type. (Open design question, flagged separately: whether to permit trait names as structural/type-constraint bounds later, similar to Rust trait bounds, is deferred.)

### 4. Example

```pys
trait Printable {
    requires string name

    string print() {
        return "Item: " + this.name
    }
}

trait Comparable {
    requires int compareTo(Product other)

    bool isGreaterThan(Product other) {
        return this.compareTo(other) > 0
    }
}

class Product uses Printable, Comparable {
    private string name
    private float price

    Product(string name, float price) {
        this.name = name
        this.price = price
    }

    public int compareTo(Product other) {
        if (this.price > other.price) {
            return 1
        }
        return -1
    }
}
```

### 5. Diagnostic cases

| Case | Result |
|---|---|
| Class omits a `requires` field/method | Compile error, naming the missing member and the requiring trait |
| Two `uses`d traits share a method name, no override supplied | Compile error, demanding explicit disambiguation |
| Trait method reads `this.x` without a matching `requires` | Compile error — undeclared dependency |
| Trait listed in `implements` | Compile error — trait is not a valid interface type |

### 6. Rationale note (for material, not normative)

The `requires` clause is the deliberate didactic device separating PYS traits from ad hoc duck-typed mixins: every dependency a trait has on its host is declared in the same place its own methods are declared, making the trait's contract-plus-implementation nature visible in the source rather than left implicit — the explicit design goal stated for this feature.