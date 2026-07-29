# S3 — Visibility and modules

## The idea

A module is a **door**. Visibility chooses who may walk through it.

| Modifier | Door policy |
|----------|-------------|
| (default) module | Locked — only this file |
| `package` | Same folder may enter |
| `global` | Any importer may enter |

Imports do not bypass locks. If `greet` is `package` and you import from another
folder, the door stays closed.

## Design question (non-recurrent)

Before exporting, ask: **who is the customer of this name?**

- Helper used once → keep module-private  
- Shared in a lab folder → `package`  
- Project-wide constant/API → `global`  

Exporting everything “just in case” destroys the point of modules.

## Tie-in

Task class [T3 Toolbox](../tasks/T3-toolbox/) forces this choice.  
Forms: [JIT: function & import](../jit/J-function-import.md).
