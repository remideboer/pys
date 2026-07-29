# T2 level C — conventional brief

## Situation

Inbound batch:

| id | label | weight |
|----|-------|--------|
| 301 | glass | 8 |
| 302 | brick | 18 |
| 303 | paper | 2 |
| 304 | steel | 30 |

**Light lane:** weight < 10 — print `LIGHT …`  
**Heavy lane:** weight ≥ 10 — print `HEAVY …`

## Deliverable

One `.pys` file that prints every row into the correct lane (four lines).

## Constraints

- Use a loop (do not copy-paste four separate `if` blocks as your only structure).  
- Typed interpolation on ids/labels/weights.  
- `THRESHOLD` (or equivalent) should be a named constant.

## Done when

T2 success criteria hold; changing the threshold in one place would retarget the lanes.
