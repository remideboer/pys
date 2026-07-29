# S5 — Objects as responsibility

## The idea

A class is not a bag of fields. It is a **responsibility**: something it must be
able to do consistently.

An **interface** names a responsibility without picking the implementation
(`Drivable`: start / move / stop). A **class** delivers that responsibility
(`Car`, `Truck`).

## Design questions

- What can every instance of this type be asked to do?  
- What varies between subtypes (override) vs what stays shared (base)?  
- Who is allowed to see fields (`private` / `protected` / `public`)?

If a class both talks to the database, draws a window, and computes invoices,
it has too many responsibilities — split before adding more methods.

## Tie-in

[T4 Fleet board](../tasks/T4-fleet-board/). Forms: [JIT: class](../jit/J-class.md).
