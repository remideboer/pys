# 10. Session — Patterns you name to build (and to ask an AI)

After you can write classes, interfaces, tests, and packages, the next skill is
**naming the shape of a design**. Software engineers (and AIs they supervise)
share a vocabulary: *Repository*, *Unit of Work*, *Circuit Breaker*, *RBAC*.

This session does **not** replace the Gang of Four demos under
[`examples/patterns/design/`](../examples/patterns/). It fills the gap Dutch (and
many other) SE programmes leave open: **application architecture, authorization,
resilience, integration, and how to prompt an AI by pattern name**.

### Why this matters with AI

If you say “make a shop API,” the model invents structure. If you say “use a
**Repository** port, a **service layer** use-case, and **RBAC** on write
endpoints,” you steer the design. Patterns are **steering words**.

### Map

| Chapter | You learn |
|---------|-----------|
| [10.1 App shape](chapter_9_1_app_shape.md) | Repository, Unit of Work, service layer, DTO / ACL |
| [10.2 Authorization](chapter_9_2_authorization.md) | RBAC, ACL, ABAC (authN vs authZ) |
| [10.3 Resilience](chapter_9_3_resilience.md) | Retry, timeout, circuit breaker, … |
| [10.4 Integration](chapter_9_4_integration.md) | Event sourcing, outbox, saga, request–reply |
| [10.5 Test doubles](chapter_9_5_test_doubles.md) | Dummy / Stub / Fake / Spy / Mock |
| [10.6 Composable rules](chapter_9_6_composable_rules.md) | Pipeline, Specification, Null Object, Plugin |
| [10.7 Data paths](chapter_9_7_data_paths.md) | Cache-aside, optimistic concurrency, … |
| [10.8 Prompting an AI](chapter_9_8_prompting_ai.md) | Vocabulary cards and prompt drills |

Runnable demos: [`examples/patterns/`](../examples/patterns/).

---

[Previous: Packages and source roots](chapter_7_3_packages_source_roots.md) · [Next: App shape](chapter_9_1_app_shape.md)
