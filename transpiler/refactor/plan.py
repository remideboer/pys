"""RefactorPlan JSON shape for IDE preview."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .catalog import catalog_entry


@dataclass
class RefactorEdit:
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    new_text: str
    kind: str = "replace"  # replace|insert|delete
    optional: bool = False
    label: str = ""


@dataclass
class RefactorConflict:
    message: str
    file: str = ""
    line: int = 0
    column: int = 0
    soft: bool = False


@dataclass
class RefactorPlan:
    ok: bool
    catalog_id: str
    title: str = ""
    summary: str = ""
    why: str = ""
    edits: list[RefactorEdit] = field(default_factory=list)
    conflicts: list[RefactorConflict] = field(default_factory=list)
    message: str = ""

    def with_catalog(self) -> RefactorPlan:
        meta = catalog_entry(self.catalog_id)
        if not self.title:
            self.title = str(meta.get("title") or self.catalog_id)
        if not self.summary:
            self.summary = str(meta.get("summary") or "")
        if not self.why:
            self.why = str(meta.get("why") or "")
        return self


def plan_to_dict(plan: RefactorPlan) -> dict[str, Any]:
    plan.with_catalog()
    return {
        "ok": plan.ok,
        "catalog_id": plan.catalog_id,
        "title": plan.title,
        "summary": plan.summary,
        "why": plan.why,
        "message": plan.message,
        "edits": [asdict(e) for e in plan.edits],
        "conflicts": [asdict(c) for c in plan.conflicts],
    }
