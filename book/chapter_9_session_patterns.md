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

<figure class="concept-diagram" role="img" aria-label="Session 10 chapter stack from diagram style through prompting an AI">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>10.0 Diagram style</strong><span>how figures match mental models</span></div>
    <div class="diagram-box"><strong>10.1 App shape</strong><span>Aggregate · Repository, UoW, service, DTO/ACL</span></div>
    <div class="diagram-box"><strong>10.1a Multitier</strong><span>three-tier · layer ≠ tier</span></div>
    <div class="diagram-box"><strong>10.2 Authorization</strong><span>RBAC, ACL, ABAC</span></div>
    <div class="diagram-box"><strong>10.3 Resilience</strong><span>retry, breaker, idempotency, …</span></div>
    <div class="diagram-box"><strong>10.4 Integration</strong><span>events, outbox, saga, reply</span></div>
    <div class="diagram-box"><strong>10.5 Test doubles</strong><span>Dummy → Mock; fixtures</span></div>
    <div class="diagram-box"><strong>10.6 Composable rules</strong><span>pipeline, spec, plugin</span></div>
    <div class="diagram-box"><strong>10.7 Data paths</strong><span>cache, versions, mappers</span></div>
    <div class="diagram-box"><strong>10.8 Prompting an AI</strong><span>name the pattern to steer</span></div>
  </div>
  <figcaption>
    Read top to bottom. Figures in later chapters reuse the same boxes and
    boundaries introduced in <a href="chapter_9_0_visual_style.md">10.0</a>.
  </figcaption>
</figure>

| Chapter | You learn |
|---------|-----------|
| [10.0 How these diagrams work](chapter_9_0_visual_style.md) | Visual style + research notes |
| [10.1 App shape](chapter_9_1_app_shape.md) | Aggregate; Repository, Unit of Work, service layer, DTO / ACL |
| [10.1a Multitier](chapter_9_1a_multitier.md) | n-tier / three-tier; layer ≠ tier; vs hexagonal |
| [10.2 Authorization](chapter_9_2_authorization.md) | RBAC, ACL, ABAC (authN vs authZ) |
| [10.3 Resilience](chapter_9_3_resilience.md) | Retry, timeout, circuit breaker, … |
| [10.4 Integration](chapter_9_4_integration.md) | Event sourcing, outbox, saga, request–reply |
| [10.5 Test doubles](chapter_9_5_test_doubles.md) | Dummy / Stub / Fake / Spy / Mock |
| [10.6 Composable rules](chapter_9_6_composable_rules.md) | Pipeline, Specification, Null Object, Plugin |
| [10.7 Data paths](chapter_9_7_data_paths.md) | Cache-aside, optimistic concurrency, … |
| [10.8 Prompting an AI](chapter_9_8_prompting_ai.md) | Vocabulary cards and prompt drills |

Runnable demos: [`examples/patterns/`](../examples/patterns/).

---

[Previous: Packages and source roots](chapter_7_3_packages_source_roots.md) · [Next: How these diagrams work](chapter_9_0_visual_style.md)
