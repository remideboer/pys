# CI failure patterns (this repo)

Recurring red builds here are usually **local gates we skipped**, not flaky
infra. Before pushing language / sem / examples / extension changes, run:

```text
python tools/local_ci.py
```

That script fails fast on:

1. `python -m pytest -q`
2. `npm test` in `pys-language/`

## Quick local gate (language / sem only)

```text
python -m pytest -q
```

If you touched call checking, types, constructors, or generics, also spot-check:

```text
python -m pytest -q tests/test_acceptance_examples.py tests/test_sem.py::test_examples_main_pys_compiles_on_ast
```

`examples/main.pys` is a **dense showcase**: many features in one file. Sem
tightenings that only have unit tests often fail here first.

## Quick local gate (extension / publish)

```text
python tools/local_ci.py
```

Or just the extension suite: `cd pys-language && npm test`.

---

## Pattern catalog

### 1. Showcase / acceptance transpile breaks

| Symptom | `examples/main.pys failed to transpile: …` or `test_acceptance_*` / `test_examples_root_pys_transpile` |
| Cause | Sem/parser now rejects code the showcase already uses (generics, ctors, named args, nullability, ordering, …) |
| Prevent | After any sem assignability / call-binding change: transpile `examples/main.pys` and run `tests/test_acceptance_examples.py` before commit |
| Related | CER-048 §2 (generic ctor vs unbound `T`); pipeline migration A5 |

### 2. `run_source` / deps inherit monorepo `pys.lock`

| Symptom | Platform mismatch (`win-amd64` lock on Linux CI), missing MySQL connector, unexpected third-party import |
| Cause | Test or example walks up to repo-root `pys.lock` instead of an isolated project |
| Prevent | Set `PYS_WORKSPACE_ROOT` to the example directory, or give the example its own `pys.toml`; never rely on root MySQL lock for dep-free examples |
| Related | CER-001 §4; `.cursor/rules/project-memory.mdc` |

### 3. Extension package version / RELEASE_NOTES / npm test

| Symptom | `npm test` fails: RELEASE_NOTES did not match `/static/` (or other highlight word); or version pin mismatch |
| Cause | (a) Notes rewrite omitted an **old** forever-keyword assert, or (b) `package.json` version bumped without notes naming that version, or (c) hard-pinned version string in tests |
| Prevent | Run `python tools/local_ci.py` after bumping version / rewriting notes. Notes must contain the **current version string only** — do not require forever feature keywords in notes (grammar/`extension.js` tests own surface DoD). Tag only `extension-v<version>` from `main` tip |
| Related | CER-001 §8; `pys-language/PUBLISH.md`; `project-main.test.js` notes check |

### 4. Docs surface drift (book / railroad / EBNF)

| Symptom | Doc or teaching CI / review catches old syntax; students copy broken ` ```pys ` fences |
| Cause | LANGUAGE / EBNF updated without `book/` + `book/html/` and/or `docs/language-railroad.html` |
| Prevent | Same change set: LANGUAGE + EBNF + railroad HTML + beginner book + `python book/build_html.py` |
| Related | Feature maturity DoD; CER-024 |

### 5. Golden / emit snapshot drift

| Symptom | `test_golden_transpile` or emit snapshot mismatch |
| Cause | Emit or builtin gating changed without updating goldens that still expect old Python |
| Prevent | Re-run golden tests locally; update intentional snapshots in the same commit |
| Related | CER-030 (parseFloat gating) |

### 6. Library-test / shop gates (FastAPI, GUI)

| Symptom | `library-tests/fastapi-shop` or GUI example transpile fails in CI |
| Cause | Named-arg / type / decorator rules applied to PYS callables incorrectly, or library kwargs treated as PYS-strict |
| Prevent | Keep “no mix” / strict binding for **known PYS** callables; allow mixed kwargs for unknown library callees (Tk, FastAPI DI) |
| Related | CER-048; ADR-026 |

---

## How to add a pattern

When a CI failure repeats (or would have been caught by a 30-second local
command), add a row here in the same fix commit. Link the CER/ADR if one
exists. Prefer **prevent** commands over “remember to be careful.”
