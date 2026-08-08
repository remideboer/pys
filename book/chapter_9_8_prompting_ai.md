# 10.8. Prompting an AI — patterns as steering words

Large language models invent structure when you are vague. **Pattern names** are
how professional engineers steer design — in code review and in prompts.

This chapter is a playbook for Dutch (and other) SE programmes that teach
syntax but skip the shared vocabulary of systems.

## The rule

> Name the **boundary**, the **failure mode**, and the **authz model** —
> not only the feature.

<figure class="concept-diagram" role="img" aria-label="Weak vague prompt versus strong prompt that names Repository RBAC and idempotency">
  <div class="diagram-prompt-pair">
    <div class="diagram-prompt is-weak">
      <span class="diagram-prompt-label">Weak</span>
      <strong>“Make a shop API”</strong>
      <span style="display:block;margin-top:0.35rem;color:var(--muted);font-size:0.9rem">model invents structure</span>
    </div>
    <div class="diagram-prompt is-strong">
      <span class="diagram-prompt-label">Strong</span>
      <strong>service layer · Repository · RBAC · idempotency</strong>
      <span style="display:block;margin-top:0.35rem;color:var(--muted);font-size:0.9rem">you steer the design</span>
    </div>
  </div>
  <figcaption>
    Signaling with pattern names beats a vague feature request.
  </figcaption>
</figure>

| Weak prompt | Strong prompt |
|-------------|---------------|
| Make a shop API | Use a **service layer** + **Repository** ports; **RBAC** on writes; **idempotency** keys on create-order |
| Make a three-tier shop | **Multitier**: presentation → application → data access; **layer ≠ tier**; UI free of SQL |
| Make it reliable | **Retry** (3) inside, **circuit breaker** outside payment; **timeout** budget on HTTP client |
| Add events | **Transactional outbox** after commit; consumers are **idempotent**; optional **saga** for reserve+charge |
| Write tests | Inject a **Fake** repository; **Object Mother** for paid orders; assert with a **Spy** on the mailer |

## Vocabulary checklist (keep near your IDE)

<figure class="concept-diagram" role="img" aria-label="Vocabulary clusters for app shape auth resilience tests and data">
  <div class="diagram-grid-2">
    <div class="diagram-box"><strong>App shape</strong><span>Repository · UoW · Multitier · DTO/ACL · DI</span></div>
    <div class="diagram-box"><strong>Auth</strong><span>AuthN/Z · RBAC · ACL · ABAC</span></div>
    <div class="diagram-box"><strong>Resilience</strong><span>Retry · Timeout · Breaker · Idempotency</span></div>
    <div class="diagram-box"><strong>Tests</strong><span>Dummy→Mock · Mother · Builder</span></div>
  </div>
  <figcaption>
    Clusters beat a wall of unsorted names — grab the cluster you need.
  </figcaption>
</figure>

**App shape:** Repository, Unit of Work, service layer, Multitier / three-tier (layer ≠ tier), DTO, Anti-Corruption Layer, Dependency Injection  

**Auth:** Authentication vs Authorization, RBAC, ACL, ABAC  

**Resilience:** Retry, Timeout, Circuit breaker, Bulkhead, Fallback, Rate limit, Idempotency  

**Integration:** Pub-sub, CQRS, Event sourcing, Outbox, Saga, Request–reply  

**Tests:** Dummy, Stub, Fake, Spy, Mock, Object Mother, Test Data Builder, AAA / GWT  

**Data:** Cache-aside, Optimistic concurrency, Data Mapper, Active Record, Identity Map  

**Composition:** Pipeline/middleware, Specification, Null Object, Plugin  

**Avoid:** Service Locator (prefer DI), Singleton globals for app services  

## Anti-confusion table (say these out loud)

| Do not mix | Because |
|------------|---------|
| CQRS vs Event sourcing | Split models vs event log; often paired |
| Repository vs Unit of Work | Persistence API vs transaction batch |
| DI vs Service Locator | Constructor supply vs hidden lookup |
| Mock vs Fake | Expectation spy vs working mini-impl |
| AuthN vs AuthZ | Identity vs permission |
| Retry vs Circuit breaker | Re-attempt vs trip open |
| Multitier vs Hexagonal | Stacked layers vs ports around a core |
| Layer vs tier | Logical code band vs physical deploy node |

## Drill 1 — name the boundary

**Feature:** Import products from a legacy CSV with weird column names.

**Say:** “Add an **Anti-Corruption Layer** that maps CSV columns into domain
`CatalogItem`. Expose a **DTO** to the API. Domain services never see CSV keys.”

Runnable shape: [`dto_acl.pys`](../examples/patterns/application/dto_acl.pys).

## Drill 2 — name the failure

**Feature:** Call a flaky partner API for prices.

**Say:** “**Circuit breaker** (open after 2 failures) + **fallback** to last
cached price + **timeout** budget. Do not retry forever.”

## Drill 3 — name authz

**Feature:** Clerks read orders; only admins refund.

**Say:** “**RBAC** permissions `order:read` and `order:refund`. Authentication
is already JWT; do not re-check passwords in the handler.”

## Drill 4 — name the test double

**Feature:** Unit-test `CreateOrderService`.

**Say:** “Inject a **Fake** `OrderRepository`. Use **Object Mother**
`paidCatan()`. **Spy** on `Mailer` to assert one welcome mail. No mocks for
`Money` values.”

## Good full prompt (copy/adapt)

```text
Build create-order with a three-tier / multitier shape (presentation →
application service → data access). Layer ≠ tier: one process is fine for the
teaching demo; keep UI free of SQL.

Application service (service layer) depends on OrderRepository and Clock via
constructor injection (DI). Persist through a Repository port; provide an
in-memory adapter for tests. Use a Unit of Work if stock reservation and order
insert must commit together.

Authorize with RBAC: clerk=order:read, admin=order:read+order:write.
Accept Idempotency-Key: same key returns the same result.

On payment port: circuit breaker + fallback. Publish OrderCreated via
transactional outbox (do not call the broker inside the DB transaction).

Tests: Fake repository, Object Mother for fixtures, Spy on mailer.
Prefer Data Mapper style domain objects (not Active Record save() on entities).
Do not introduce a Service Locator. Multitier ≠ Hexagonal — you may combine
both (ports at the data edge).
```

## Where to practice

All demos: [`examples/patterns/`](../examples/patterns/README.md).  
Start from Session hub: [Patterns you name to build](chapter_9_session_patterns.md).  
Diagram rules: [How these diagrams work](chapter_9_0_visual_style.md) ·
[Bibliography](bibliography_visual_explanations.md).

### Exercise

> Rewrite this weak prompt into a strong one: “Add users and security to my
> API.” List at least four pattern names you would include.

---

[Previous: Data paths](chapter_9_7_data_paths.md) · [Next: From PYS to C# and Java](chapter_8_session_csharp_java.md)
