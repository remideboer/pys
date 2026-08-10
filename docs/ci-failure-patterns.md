# CI failure patterns (this repo)

Recurring red builds here are usually **local gates we skipped**, not flaky
infra. Feature maturity DoD **§12** requires a **considerable ahead-of-time**
effort to analyse blast radius and prevent CI failures — not push-and-fix.

Before claiming a change set done (and before pushing language / sem /
examples / book / extension changes), run:

```text
python -m pytest -q
```

When extension / highlights / RELEASE_NOTES / publish surface moved:

```text
python tools/local_ci.py
```

That script fails fast on:

1. `python -m pytest -q`
2. `npm test` in `pys-language/`

## Ahead-of-time analysis (DoD §12)

Do this **before** calling the work complete — ideally while planning and again
after the last edit:

1. **Blast radius** — Which suites can break? (full pytest, goldens, acceptance /
   `main.pys`, book link/order tests, example folder-count gates, npm extension
   tests, lock/`PYS_WORKSPACE_ROOT`, railroad/EBNF, version/notes pins.)
2. **Catalog** — Read matching rows below; apply **Prevent** in the same change
   set (do not wait for CI).
3. **Grep dependents** — Old paths, `# N.` SUMMARY headings, assert counts,
   version strings, snapshot names.
4. **Run the real gate** — Full `pytest -q` (or `local_ci.py`); fix everything
   here; if a new failure mode appears, **add a row** in this file in the fix
   commit.

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
| Prevent | After any sem assignability / call-binding change: transpile `examples/main.pys` (also `--target javascript`) and run `tests/test_acceptance_examples.py` before commit |
| Related | CER-048 §2 (generic ctor vs unbound `T`); CER-050 §6; pipeline migration A5; MySQL/GUI under `examples/by-target/` / `examples/gui/` |

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

### 7. Book SUMMARY renumber / structural layout drift

| Symptom | `test_book_links.py` / `ValueError: substring not found` for `# N. Under the hood` (or similar); nav order asserts fail |
| Cause | Inserted or renumbered `book/SUMMARY.md` parts (e.g. new Session 10 Patterns) without updating tests that hard-code `# N. …` headings or relative order |
| Prevent | Same change set: grep `tests/` (and docs) for old `# N.` / session titles; update asserts; run **`python -m pytest -q`** (full suite), not only `test_patterns.py` / demo gates. Rebuild `book/html/` |
| Related | Feature maturity DoD §2, §6, §12 |

### 8. Example corpus gate count drift

| Symptom | `test_patterns.py` (or similar) `assert len(folder) == N` fails |
| Cause | Added/removed `examples/patterns/**/*.pys` without updating folder counts |
| Prevent | Update gate asserts in the same commit as new demos; run the gate + full pytest before done |
| Related | CER-049; Feature maturity DoD §12 |

### 9. Node DAP / prepare_debug JS / extension remap drift

| Symptom | `test_prepare_debug` fails on missing `js` / `runtimeExecutable`; npm `debug-map` / `debug-launch` tests fail; Debug still Python-gated in extension |
| Cause | JS emit maps use `js` keys but prepare/remap still assume `py`; launch adapter or tracker registered only for `python` |
| Prevent | Same change set: `prepare_debug(..., target=javascript)`, target-neutral `debug-map.js`, `debug-launch.js` + tracker for `pwa-node`; run `python -m pytest -q` and `python tools/local_ci.py` |
| Related | ADR-014; CER-014; CER-050 §10; F-010 item 1 |

### 10. Still teaching `pys.deps` / silo `package.json`

| Symptom | Docs/book/examples still show indented `pys.deps` or student `package.json`; create-project writes `pys.deps`; lock menus only on `pys.deps` |
| Cause | Deps unified into `pys.toml` without a dependent hunt |
| Prevent | Same change set: migrate corpus, create-project, menus, README/book/LANGUAGE/ADRs; `python tools/local_ci.py` |
| Related | ADR-002; ADR-030; CER-050 §11 |

### 11. Run Project / `[project].target` drift

| Symptom | Right-click `pys.toml` missing **Run Project**; JS silos need status-bar emit; CLI `--target` default ignores toml |
| Cause | Manifest target / `pys.runProject` landed without menus, silo tomls, or CLI default |
| Prevent | Same change set: `load_project_emit_target`, extension menus (`navigation@0`), migrate by-target `target = "javascript"`, tests in `test_entrypoint_panic` + `project-main.test.js`; `python tools/local_ci.py` |
| Related | ADR-030; CER-050 §12 |

### 12. `[project].main` blocks test suite `run_source`

| Symptom | Shop/webserver suite tests fail with `pys.entrypoint-conflict` after adding `[project].main` |
| Cause | `resolve_entrypoint` treated every non-main `.pys` as a conflict, including `[source_roots] test = "tests"` |
| Prevent | Allow explicit run of files under source roots named `test`/`tests`; cover in `test_entrypoint_panic`; run shop/webserver suite gates before release |
| Related | CER-025; ADR-017 |

### 13. By-target Python MySQL compile needs stub site (CI vs local)

| Symptom | `test_by_target_python_mysql_compiles` fails on Linux CI: `Cannot find module 'mysql.connector'`; may pass locally if the connector is installed on the host Python |
| Cause | Acceptance transpile of `examples/by-target/python/mysql` used bare `transpile_with_modules` with no `mysql_connector_site` / `PYS_WORKSPACE_ROOT`; silo has `[dependencies]` but no lock and CI has no wheel |
| Prevent | Same pattern as `test_shop_mysql_main_transpiles` / `test_example_database_shop_transpiles`: inject `mysql_connector_site`, set `PYS_WORKSPACE_ROOT` to the silo; never rely on a host-installed `mysql-connector-python` for compile gates. Before push: `python -m pytest -q tests/test_acceptance_examples.py` (and full `pytest -q` / `local_ci` on release) |
| Related | CER-001 §4; ADR-002; examples/by-target |

### 14. Member access denial only tested on one use site

| Symptom | Private/protected field readable via `"…{obj.field}…"`, `print(obj.field)`, call args, etc., while `obj.field = …` correctly denies |
| Cause | `_check_oop` / regression suite covered a single assign shape; other use sites (especially `InterpolatedString` raw text) skipped `check_member` |
| Prevent | Keep `tests/test_member_access.py` green; for any new access/visibility rule, add **negative** cases for assign, print/read, decl RHS, call arg, string + typed interpolation, subclass; mirror `requirements/rekenmachine.pys` uncomment-to-fail lines. DoD §2 negative regressions. |
| Related | CER-052; Feature maturity DoD §2; `tests/test_sem.py` interpolation cases |

---

## How to add a pattern

When a CI failure repeats (or would have been caught by a 30-second local
command), add a row here in the same fix commit. Link the CER/ADR if one
exists. Prefer **prevent** commands over “remember to be careful.”
