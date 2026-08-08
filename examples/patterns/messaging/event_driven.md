# Event-driven architecture

**Category:** Messaging  
**Status: stub — implement later**

**Wikipedia:** [Event-driven architecture](https://en.wikipedia.org/wiki/Event-driven_architecture)

## Intent

Components react to **events** (facts that happened) rather than calling each
other directly through a central orchestrator.

## Why stubbed

Architecture-scale brokers, durable logs, and async delivery are out of scope for
a tiny demo. In-process notification is already taught as
[Observer](../design/behavioral/observer.md).
