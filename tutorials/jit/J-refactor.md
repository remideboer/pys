# JIT — Refactoring (educational core)

## Ops (context menu **Refactor** / lightbulb)

| Command | Fowler name | When |
|---------|-------------|------|
| Rename Symbol (F2) | Rename Variable / Function / Field | Cursor on a PYS binding |
| Extract Variable | Extract Variable | Selection is an expression |
| Extract Function | Extract Function | Selection is one or more statements |
| Inline Variable | Inline Variable | Single-assignment local |
| Inline Function | Inline Function | Simple `return expr` function |
| Safe Delete | Remove Dead Code | Declaration with no remaining refs |
| Introduce Parameter | Add Parameter | Local inside a function |

Each action shows a **preview** of edits (uncheck to exclude) and teaching text (*what* / *why*).

## Rules

1. Edits are **binding-aware** — same text in another scope is not rewritten  
2. Find Usages uses the same reference graph as Rename  
3. Extract into a class places the method in the **method section** (member kind order)  
4. Python/deps symbols are not rename targets  

Habit model: [S8](../supportive/S8-refactor-as-habit.md).  
Language order constraint: [J-member-order](J-member-order.md).
