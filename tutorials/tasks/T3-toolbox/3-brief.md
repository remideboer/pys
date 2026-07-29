# T3 level C — conventional brief

## Situation

Team A owns `measures.pys`. Team B owns `report.pys` in the **same folder**.

Team B must:

- print a header via a function Team A exports  
- read a `global const` unit string (e.g. `"C"`) from Team A  

Team A also has an experimental helper that must remain file-private.

## Deliverable

Two `.pys` files meeting the situation. Run `report.pys` as the entry file.

## Done when

T3 success criteria hold; attempting to import the private helper fails on purpose.
