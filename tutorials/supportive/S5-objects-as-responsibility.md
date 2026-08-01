# S5 — Objects as responsibility

## The idea

A class is not a bag of fields. It is a **responsibility**: something it must be
able to do consistently.

An **interface** names a responsibility without picking the implementation
(`Drivable`: start / move / stop). A **class** delivers that responsibility
(`Car`, `Truck`).

A **struct** *is* a bag of fields: schema-fixed values with no methods and
value semantics. Use a struct when there is no responsibility to name — only
data shape ([S6](S6-struct-vs-dict.md), [JIT: struct](../jit/J-struct.md)).

## Design questions

- What can every instance of this type be asked to do?  
- What varies between subtypes (override) vs what stays shared (base)?  
- Who is allowed to see fields (`private` / `protected` / `public`)?

If a class both talks to the database, draws a window, and computes invoices,
it has too many responsibilities — split before adding more methods.

## Tie-in

[T4 Fleet board](../tasks/T4-fleet-board/). Forms: [JIT: class](../jit/J-class.md).
