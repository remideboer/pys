# S7 — Order as a transferable habit

## The idea

PYS makes **kind order** (imports first; const → fix → fields → constructors →
methods; and the matching rules for struct / trait / entity) a **parse error**.
Java, C#, Kotlin, and PEP 8 usually only **recommend** the same shape via style
guides or linters — their compilers stay silent when a method sits above a field.

Teach both layers:

1. The concrete PYS rule (so the program compiles).
2. The expectation that students keep the same discipline when the compiler
   stops enforcing it.

Framing line:

> PYS enforces this because it is good practice everywhere; most other
> languages only recommend it.

That matches the transfer story used for lambda capture and for Hibernate
`equals` / `hashCode` postmortems: the win is the habit that survives leaving
PYS, not mere compliance with one toolchain.

## Why force relocate?

Changing a field from mutable to `fix` (or adding a constructor) should
**move** the declaration into the right section. Structure after a refactor
should still advertise kind order — not only happen to compile.

## What not to over-teach

Do **not** claim other languages will reject out-of-order members. Students who
only hear “the PYS compiler made me” drop the habit the moment they open an IDE
that doesn’t.

JIT forms / error table: [J-member-order](../jit/J-member-order.md).  
Drills: [P-member-order](../practice/P-member-order.md).
