# 10.5. Test doubles — Dummy, Stub, Fake, Spy, Mock

Session 6 taught TDD. This chapter names the **stand-ins** you inject behind a
port so tests stay fast and focused.

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
