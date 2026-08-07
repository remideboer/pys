# 9.2. Better PYS with TDD

**Test-driven development** flips the order:

1. Write a failing check for behavior you want.
2. Write the smallest code that makes it pass.
3. Clean up names and structure while tests stay green.

For students, the win is not ceremony — it is feedback every few minutes.
Keep examples tiny: one function, two assertions, one commit of learning.

When a test “needs” a private field, treat that as a design smell: improve
the API (`package` / `public` methods), do not invent a language bypass.

### Exercise

> Using TDD order, implement `function string grade(int score)` that
> returns `"pass"` if `score >= 60`, else `"fail"`. Write the checks before
> the final body.

---

[Previous: Writing a first test](chapter_7_1_first_test.md) · [Next: Packages and source roots](chapter_7_3_packages_source_roots.md)
