# 10.5. Test doubles — Dummy, Stub, Fake, Spy, Mock

Session 6 taught TDD. This chapter names the **stand-ins** you inject behind a
port so tests stay fast and focused.

<figure class="concept-diagram" role="img" aria-label="Mailer port with five labeled doubles around Notifier">
  <div class="diagram-stack">
    <div class="diagram-box diagram-layer-edge" style="border-style:dashed;border-width:2px;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Mailer (port)</strong>
      <span>Notifier depends on this socket</span>
    </div>
    <div class="diagram-grid-5">
      <div class="diagram-box"><strong>Dummy</strong><span>must not run</span></div>
      <div class="diagram-box"><strong>Stub</strong><span>canned / no-op</span></div>
      <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center"><strong>Fake</strong><span>mini working impl</span></div>
      <div class="diagram-box"><strong>Spy</strong><span>records calls</span></div>
      <div class="diagram-box"><strong>Mock</strong><span>checks expect</span></div>
    </div>
  </div>
  <figcaption>
    One port, five jobs — pick the double that matches what the test needs.
  </figcaption>
</figure>

| Double | Job |
|--------|-----|
| **Dummy** | Fills a parameter; must not be used |
| **Stub** | Provides canned answers / no-op |
| **Fake** | Working simplified implementation (in-memory DB) |
| **Spy** | Records calls for assertions |
| **Mock** | Checks expectations (fail if wrong collaborator use) |

Demo: [`test_doubles.pys`](../examples/patterns/testing/test_doubles.pys)

```text
python -m transpiler run examples/patterns/testing/test_doubles.pys
```

**Output:**

```text
stub-ok
1
2
mock-ok
```

## Object Mother vs Test Data Builder

- **Object Mother:** named methods (`paidCatan()`) for common valid objects.
- **Test Data Builder:** fluent `withX` for one-off variations.

<figure class="concept-diagram" role="img" aria-label="Object Mother named recipe versus Builder fluent withX path">
  <div class="diagram-grid-2">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Object Mother</strong>
      <span>paidCatan() · named valid fixture</span>
    </div>
    <div class="diagram-box">
      <strong>Test Data Builder</strong>
      <span>withCustomer · withTotal · build()</span>
    </div>
  </div>
  <figcaption>
    Mother for the usual case; Builder when one test needs a one-off twist.
  </figcaption>
</figure>

Demos: [`object_mother.pys`](../examples/patterns/testing/object_mother.pys),
[`test_data_builder.pys`](../examples/patterns/testing/test_data_builder.pys)

### Prompt dialogue

> **You:** Inject a Fake `OrderRepository` in unit tests. Use an Object Mother
> for a paid order fixture. Do not mock value objects.
>
> **Not:** “Mock all the things.”

### Arrange–Act–Assert / Given–When–Then

Same rhythm Session 6 uses — now you can say the names when prompting.

---

[Previous: Integration](chapter_9_4_integration.md) · [Next: Composable rules](chapter_9_6_composable_rules.md)
