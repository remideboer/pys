"""Rename Symbol refactor."""
from __future__ import annotations

import re
from pathlib import Path

from ..lex import KEYWORDS
from .catalog import catalog_entry
from .plan import RefactorConflict, RefactorEdit, RefactorPlan
from .refs import build_index, resolve_at


_IDENT = re.compile(r"^[A-Za-z_]\w*$")


def plan_rename(
    source_path: Path,
    *,
    line: int,
    column: int,
    new_name: str,
) -> RefactorPlan:
    meta = catalog_entry("rename-symbol")
    plan = RefactorPlan(
        ok=False,
        catalog_id="rename-symbol",
        title=str(meta["title"]),
        summary=str(meta["summary"]),
        why=str(meta["why"]),
    )
    new_name = (new_name or "").strip()
    if not _IDENT.match(new_name):
        plan.conflicts.append(
            RefactorConflict(message=f"Invalid identifier {new_name!r}.")
        )
        return plan
    if new_name in KEYWORDS:
        plan.conflicts.append(
            RefactorConflict(message=f"{new_name!r} is a PYS keyword.")
        )
        return plan

    index = build_index(source_path)
    decl = resolve_at(index, source_path, line, column)
    if decl is None:
        plan.conflicts.append(
            RefactorConflict(
                message="No PYS declaration under the cursor (deps/Python symbols cannot be renamed).",
                file=str(source_path),
                line=line,
                column=column,
            )
        )
        return plan
    if new_name == decl.name:
        plan.ok = True
        plan.message = "Name unchanged."
        return plan

    # Clash: same scope sibling with new_name — soft check: any decl with same name in same file top-level kinds
    for other in index.sites_by_decl:
        if other.name == new_name and other.file == decl.file and other.kind == decl.kind:
            plan.conflicts.append(
                RefactorConflict(
                    message=f"Name {new_name!r} already used by another {other.kind} in this file.",
                    file=other.file,
                    line=other.line,
                    column=other.column,
                    soft=True,
                )
            )

    for site in index.sites_for(decl):
        plan.edits.append(
            RefactorEdit(
                file=site.file,
                line=site.line,
                column=site.column,
                end_line=site.line,
                end_column=site.end_column,
                new_text=new_name,
                kind="replace",
                label=f"{site.kind} {decl.name} → {new_name}",
            )
        )
    plan.ok = True
    if not plan.edits:
        plan.ok = False
        plan.conflicts.append(RefactorConflict(message="No editable sites found."))
    return plan
