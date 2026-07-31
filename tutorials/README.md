# PYS tutorials

This track is built with **4C/ID** (van Merriënboer), **scaffolding that fades**, and
**just-in-time (JIT)** help. It is not a chapter list of “variables → loops → classes”.

## How learning is organized

| 4C/ID component | Where it lives | What you do with it |
|-----------------|----------------|---------------------|
| **Learning tasks** | [`tasks/`](tasks/) | Whole, realistic problems. Complexity rises across task classes. |
| **Supportive information** | [`supportive/`](supportive/) | Mental models and *why* — for non-routine decisions. |
| **JIT / procedural information** | [`jit/`](jit/) | Short how-to cards — open **only when stuck on a step**. |
| **Part-task practice** | [`practice/`](practice/) | Tiny drills for habits that must become automatic. |

### Scaffolding (inside each task class)

1. **Worked example** — full solution. Study it; explain each decision out loud.
2. **Completion problem** — same kind of task, gaps marked `TODO`. You finish it.
3. **Conventional problem** — brief + success criteria only. You design the solution.

Do **A → B → C** in order. Skipping A is fine only if you can already narrate a solution.

### Task classes (whole-task sequence)

| Class | Authentic whole task | Recurrent skills practiced | Non-recurrent thinking |
|-------|----------------------|----------------------------|-------------------------|
| [T1 Sensor log](tasks/T1-sensor-log/) | Log lab readings with typed values | declarations, print, `#i`/`#s` | which type / const vs fix |
| [T2 Batch filter](tasks/T2-batch-filter/) | Filter a shipment batch | `if`/`unless`, `loop`, tuples | when to branch vs loop |
| [T3 Toolbox](tasks/T3-toolbox/) | Share helpers across files | `function`, `import`, visibility | what to export |
| [T4 Fleet board](tasks/T4-fleet-board/) | Model vehicles with contracts | class, interface, `inherits` | responsibility boundaries |

Start: **[00 — Start here](00-start-here.md)**. Teachers: **[TEACHER.md](TEACHER.md)**.

## Run a task file

```bash
python -m pip install -e .
python -m transpiler run tutorials/tasks/T1-sensor-log/1-worked.pys
```

Or open the file in Cursor/VS Code with the PYS extension and use **Run**.

## Reference (not the tutorial)

- Grammar: [`../docs/language.ebnf`](../docs/language.ebnf)
- Overview: [`../docs/LANGUAGE.md`](../docs/LANGUAGE.md)
- Architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- Showcase (dense): [`../examples/main.pys`](../examples/main.pys)
