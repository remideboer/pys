# Architecture

How the PYS toolchain is structured and how a `.pys` file becomes running Python.

Related docs: [LANGUAGE.md](LANGUAGE.md) · [CONCURRENCY.md](CONCURRENCY.md) · [pipeline-migration.md](pipeline-migration.md)

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
    Lex["lex.tokenize"]
    Parse["parse.parse_program"]
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
    Legacy["transpiler.Parser<br/>use_legacy + module load"]
    Spec["language_spec<br/>line helpers / legacy"]
  end

  Main --> Public
  Main --> Deps
  Ide --> Public
  Public --> Pipe["pipeline.compile_pys"]
  Pipe --> Lex --> Parse --> AST --> Sem --> Emit
  Emit --> Over
  Emit --> Conc
  Emit --> Imp
  Imp --> Legacy
  Emit -.->|only if use_legacy| Legacy
  Legacy --> Spec
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
| `concurrency.py` | Shared tasks/await/shared preamble |
| `imports.py` | Facade for `.pys` import resolution / visibility |
| `deps.py` | `pys.deps` → `~/.pys/repository` |
| `transpiler.py` | Public `transpile` / `run_source`; legacy `Parser` for quarantine paths and loading imported `.pys` metadata |

---

## Compiler pipeline (process)

```mermaid
flowchart TD
  Src[".pys source string<br/>+ optional source_path"] --> Lex["1. Lex<br/>tokenize"]
  Lex -->|LexError| Err["TranspileError"]
  Lex --> Parse["2. Parse<br/>parse_program"]
  Parse -->|unrepresentable| LegacyFlag["Module.use_legacy = true<br/>empty body"]
  Parse --> Tree["Module AST"]
  LegacyFlag --> Sem
  Tree --> Sem["3. Sem<br/>analyze"]
  Sem -->|fault| Err
  Sem --> Emit["4. Emit Python"]
  Emit -->|use_legacy| LegacyEmit["Parser.parse<br/>legacy line path"]
  Emit -->|AST path| Walk["Emitter.emit_module"]
  Walk --> Over["rewrite_overloaded_methods"]
  Walk --> ImpRes["imports.resolve<br/>when source_path set"]
  Over --> Out["Python source string"]
  LegacyEmit --> Out
  ImpRes --> Out
```

### Stage details

1. **Lex** — Reject illegal tokens early (e.g. tabs).
2. **Parse** — Prefer brace mode when `{`/`}` are present. Indent-mode (`then` / `func` / `repeat`) only when there are no braces. On hard parse failure, set `use_legacy` so emit can fall back for rare unparsed forms.
3. **Sem** — Owns most language rules on the AST: `let`, bindings, const/fix, loop counters, typed interpolation, member access, sealed/interfaces, shared capture (Policy B), arrays, class modifiers, await placement/cycles, import-name access when `source_path` is set.
4. **Emit** — Walk AST to Python; inject concurrency preamble and ABC/array imports as needed; resolve `.pys` imports; rewrite method overloads. Legacy `Parser.parse()` runs **only** when `use_legacy` is true.

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
    +bool use_legacy
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

When `source_path` is set, emit and sem share the imports facade:

```mermaid
flowchart LR
  Src["ImportStmt<br/>import X from foo.pys"] --> Facade["imports.translate_import"]
  Facade --> Resolve["Find foo.pys / package"]
  Resolve --> Vis["Visibility<br/>global / package / module"]
  Vis --> PyImp["from foo import X"]
  Vis -->|denied| Err["TranspileError"]
```

Loading sibling `.pys` metadata still uses the legacy module loader under that facade. Call sites in emit/sem do not construct `Parser` directly except through `imports` / `_legacy_emit`.

---

## Extension ↔ transpiler

```mermaid
flowchart LR
  subgraph vscode [Editor]
    Lang["pys-language extension"]
    Run["PYS: Run File"]
    Diag["diagnostics"]
  end

  subgraph bundled [Bundled / PATH]
    Tx["transpiler package"]
  end

  Lang --> Run
  Run --> Tx
  Lang --> Diag
  Diag --> Tx
  Tx --> Out["temp Python + debug adapter"]
```

The extension packages a copy of the transpiler (`npm run prepare`). Diagnostics and Run share the same front-end rules as `compile_pys` where possible; PYS source-level DAP stepping is deferred ([pipeline-migration.md](pipeline-migration.md) C2).

---

## Extending the pipeline

| Goal | Touch |
| --- | --- |
| New syntax | `lex` → `parse` → `ast_nodes` → `sem` (if checked) → `emit/python` · update `docs/language.ebnf` |
| New semantic rule | Prefer `sem.py` + tests under `tests/test_sem.py` |
| New backend | Add `emit/<target>.py` and a `target=` branch in `pipeline.compile_pys` |
| New dependency behavior | `deps.py` + `pys.deps` docs in the README |

Characterization goldens: `tests/golden/` (regen only via `python tests/golden/regen.py`).
