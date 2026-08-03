# Architecture

How the PYS toolchain is structured and how a `.pys` file becomes running Python.

Related docs: [LANGUAGE.md](LANGUAGE.md) · [CONCURRENCY.md](CONCURRENCY.md) · [pipeline-migration.md](pipeline-migration.md) · [evolution/](evolution/README.md) (code CERs) · [adr/](adr/README.md) (ADRs) · [TODO-FUTURE.md](TODO-FUTURE.md) (deferred work)

---

## Big picture

```mermaid
flowchart LR
  subgraph authors [Authoring]
    PYS[".pys source"]
    Ext["VS Code / Cursor<br/>pys-language"]
  end

  subgraph toolchain [Toolchain]
    CLI["python -m transpiler"]
    Pipe["pipeline.compile_pys"]
    Deps["deps / pys.deps"]
  end

  subgraph runtime [Runtime]
    Gen["Generated .py"]
    Py["Python 3.10+"]
    Repo["~/.pys/repository"]
  end

  PYS --> Ext
  PYS --> CLI
  Ext --> CLI
  CLI --> Deps
  Deps --> Repo
  CLI --> Pipe
  Pipe --> Gen
  Gen --> Py
  Repo -.-> Py
```

Students edit `.pys`. Run/transpile goes through the CLI (or the extension wrapping it). Dependencies are resolved from `pys.deps` into a shared cache; generated Python then runs with that `PYTHONPATH`.

---

## Component architecture

```mermaid
flowchart TB
  subgraph entry [Entry points]
    Main["__main__.py<br/>transpile / run"]
    Public["transpile / run_source<br/>__init__.py"]
    Ide["ide.py<br/>diagnostics JSON"]
  end

  subgraph front [Front end]
    Lex["lex.tokenize_with_flags"]
    Parse["parse.parse_program<br/>peg packrat optional"]
    AST["ast_nodes.Module"]
    Sem["sem.analyze"]
  end

  subgraph back [Back end]
    Emit["emit/python.emit"]
    Over["emit/overloads"]
    Conc["concurrency.CONCURRENCY_PREAMBLE"]
    Imp["imports.make_resolver"]
  end

  subgraph support [Support]
    Deps["deps.py"]
    Spec["language_spec<br/>emit helpers / line tests"]
  end

  Main --> Public
  Main --> Deps
  Ide --> Public
  Ide --> Imp
  Ide --> Parse
  Public --> Pipe["pipeline.compile_pys"]
  Pipe --> Lex --> Parse --> AST --> Sem --> Emit
  Emit --> Over
  Emit --> Conc
  Emit --> Imp
  Emit --> Spec
  Imp --> Parse
```

| Module | Role |
| --- | --- |
| `pipeline.py` | Orchestrates **lex → parse → sem → emit** |
| `lex.py` | Tokens with line/column spans |
| `parse.py` | Brace (and limited indent) recursive-descent → AST |
| `ast_nodes.py` | Target-neutral statements / expressions |
| `sem.py` | Semantic checks on the AST (types, access, tasks, arrays, …) |
| `emit/python.py` | Python text from AST |
| `emit/overloads.py` | Post-pass arity dispatch for overloaded methods |
| `concurrency.py` | Shared tasks/await/shared/atomic preamble |
| `imports.py` | AST-based `.pys` import resolution / visibility |
| `deps.py` | `pys.deps` → `~/.pys/repository` |
| `transpiler.py` | Public `transpile` / `run_source` / `TranspileError` |
| `language_spec.py` | Shared string helpers for emit; `LANGUAGE.translate_line` tests |
| `ide.py` | Go-to-definition / diagnostics via AST pipeline |

---

## Compiler pipeline (process)

```mermaid
flowchart TD
  Src[".pys source string<br/>+ optional source_path"] --> Lex["1. Lex<br/>tokenize"]
  Lex -->|LexError| Err["TranspileError"]
  Lex --> Parse["2. Parse<br/>parse_program"]
  Parse -->|ParseError| Err
  Parse --> Tree["Module AST"]
  Tree --> Sem["3. Sem<br/>analyze"]
  Sem -->|fault| Err
  Sem --> Emit["4. Emit Python"]
  Emit --> Walk["Emitter.emit_module"]
  Walk --> Over["rewrite_overloaded_methods"]
  Walk --> ImpRes["imports.resolve<br/>when source_path set"]
  Over --> Out["Python source string"]
  ImpRes --> Out
```

### Stage details

1. **Lex** — Reject illegal tokens early (e.g. tabs).
2. **Parse** — Prefer brace mode when `{`/`}` are present. Indent-mode (`then` / `func` / `repeat`) only when there are no braces. Failures raise `TranspileError` (no legacy fallback).
3. **Sem** — Owns language rules on the AST: `let`, bindings, const/fix, loop counters, typed interpolation, member access, sealed/interfaces, shared/atomic capture (Policy B), arrays, class modifiers, await placement/cycles, import-name access when `source_path` is set.
4. **Emit** — Walk AST to Python; inject concurrency preamble and ABC/array imports as needed; resolve `.pys` imports via `ImportResolver`; rewrite method overloads.

---

## Run vs transpile (sequence)

```mermaid
sequenceDiagram
  actor User
  participant CLI as __main__
  participant Deps as deps.py
  participant Pipe as compile_pys
  participant Py as python.exe

  User->>CLI: run path.pys
  CLI->>Deps: find pys.deps / resolve packages
  Deps-->>CLI: PYTHONPATH entries
  CLI->>Pipe: compile_pys(source, source_path)
  Note over Pipe: lex → parse → sem → emit
  Pipe-->>CLI: Python text
  CLI->>CLI: write temp .py (+ sibling modules)
  CLI->>Py: exec with env PYTHONPATH
  Py-->>User: stdout / traceback
```

`transpile` stops after `compile_pys` and writes the requested `.py` file (no execute).

---

## AST shape (UML)

High-level view of the module tree the parser produces and sem/emit consume:

```mermaid
classDiagram
  direction TB
  class Module {
    +str source
    +list~Node~ body
    +bool brace_mode
  }

  class Node {
    +Span span
  }

  class Expr
  class Stmt

  Module "1" --> "*" Node : body
  Node <|-- Expr
  Node <|-- Stmt

  class FunctionDef {
    +str name
    +list~str~ params
    +str return_type
    +str visibility
    +Block body
  }
  class ClassDef {
    +str name
    +list~str~ bases
    +bool sealed
    +list~FieldDecl~ fields
    +list~MethodDef~ methods
  }
  class StructDef {
    +str name
    +bool type_fix
    +list~str~ type_params
    +list~StructField~ fields
  }
  class TasksBlock {
    +int group_id
    +list~TaskDef~ tasks
  }
  class ImportStmt {
    +str kind
    +str module
    +str name
  }
  class AssignStmt {
    +str name
    +Expr value
    +str declare_type
  }

  Stmt <|-- FunctionDef
  Stmt <|-- ClassDef
  Stmt <|-- StructDef
  Stmt <|-- TasksBlock
  Stmt <|-- ImportStmt
  Stmt <|-- AssignStmt
  Stmt <|-- PrintStmt
  Stmt <|-- IfStmt
  Stmt <|-- ForRangeStmt
  Stmt <|-- ForEachStmt

  class Call {
    +Expr callee
    +list~Expr~ args
  }
  class Member {
    +Expr object
    +str name
  }
  class AwaitExpr {
    +Expr target
  }
  class InterpolatedString {
    +str raw
  }

  Expr <|-- Call
  Expr <|-- Member
  Expr <|-- AwaitExpr
  Expr <|-- InterpolatedString
  Expr <|-- BinaryOp
  Expr <|-- Identifier
  Expr <|-- Literal
```

---

## Import resolution

When `source_path` is set, emit and sem share the AST-based imports facade:

```mermaid
flowchart LR
  Src["ImportStmt<br/>import X from foo.pys"] --> Facade["imports.translate_import"]
  Facade --> Resolve["Find foo.pys / package"]
  Resolve --> Vis["Visibility<br/>global / package / module"]
  Vis --> PyImp["from foo import X"]
  Vis -->|denied| Err["TranspileError"]
```

Sibling `.pys` metadata is loaded with `parse_program` + `module_info_from_ast` (exports, sealed, class graph). No legacy `Parser` on this path.

---

## Extension ↔ transpiler

```mermaid
flowchart LR
  subgraph vscode [Editor]
    Lang["pys-language extension"]
    Run["PYS: Run File"]
    Debug["PYS: Debug File"]
    Diag["diagnostics"]
  end

  subgraph bundled [Bundled / PATH]
    Tx["transpiler package"]
  end

  Lang --> Run
  Lang --> Debug
  Run --> Tx
  Debug --> Prep["prepare_debug maps"]
  Prep --> Tx
  Debug --> Dbgpy["debugpy on temp .py"]
  Diag --> Tx
  Prep --> Remap["DebugAdapterTracker remap to .pys"]
  Dbgpy --> Remap
```

The extension packages a copy of the transpiler (`npm run prepare`). Diagnostics and Run share the same front-end rules as `compile_pys` where possible. Debug prepares generated modules + line maps and remaps breakpoints/stack frames to `.pys` ([ADR-014](adr/ADR-014-pys-dap-stepping.md)).
---

## Extending the pipeline

| Goal | Touch |
| --- | --- |
| New syntax | `lex` → `parse` → `ast_nodes` → `sem` (if checked) → `emit/python` · update `docs/language.ebnf` |
| New semantic rule | Prefer `sem.py` + tests under `tests/test_sem.py` |
| New backend | Add `emit/<target>.py` and a `target=` branch in `pipeline.compile_pys` |
| New dependency behavior | `deps.py` + `pys.deps` docs in the README |

Characterization goldens: `tests/golden/` (regen only via `python tests/golden/regen.py`).

Why recent security and performance code moved the way it did (pre/post behavior,
not architecture diagrams): [`evolution/`](evolution/README.md).
System-level decisions: [`adr/`](adr/README.md). Both are project memory —
see `.cursor/rules/project-memory.mdc`.
