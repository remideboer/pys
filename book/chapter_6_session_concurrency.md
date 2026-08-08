# Session 5 — Doing several things at once

PYS has **no** Rust-style ownership/borrow checker. Concurrency is
structured around `tasks` / `task` / `await`, with explicit `shared` and
`atomic` when tasks must mutate outer state.

<figure class="concept-diagram" role="img" aria-label="Session 5 map from tasks through shared atomic to capture">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>8.1 tasks / await</strong><span>join · DAG pipelines</span></div>
    <div class="diagram-box"><strong>8.2 shared</strong><span>visible mutation across tasks</span></div>
    <div class="diagram-box"><strong>8.3 atomic</strong><span>indivisible +=</span></div>
    <div class="diagram-box"><strong>8.4 capture</strong><span>snapshot by value</span></div>
  </div>
  <figcaption>
    Structure first, then say when mutation crosses a task boundary.
  </figcaption>
</figure>

Read the deep dive any time: [`docs/CONCURRENCY.md`](../docs/CONCURRENCY.md).

1. [tasks, task, and await](chapter_6_1_tasks_await.md)
2. [shared state](chapter_6_2_shared_state.md)
3. [atomic updates](chapter_6_3_atomic_updates.md)
4. [Lambdas and capture rules](chapter_6_4_lambdas_capture.md)

---

[Previous: Restyling the temperature converter](gui_ttkbootstrap_project.md) · [Next: tasks, task, and await](chapter_6_1_tasks_await.md)
