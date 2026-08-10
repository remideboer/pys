"""Create Class planner from named constructor calls."""
from __future__ import annotations

from pathlib import Path

from transpiler.pipeline import compile_pys
from transpiler.refactor.apply import apply_plan_to_files
from transpiler.refactor.create_class import plan_create_class


def test_create_class_from_named_call(tmp_path: Path) -> None:
    src = 'Student st = Student(naam="Jaap")\n'
    path = tmp_path / "t.pys"
    path.write_text(src, encoding="utf-8")
    plan = plan_create_class(path, line=1, column=20)
    assert plan.ok is True
    assert plan.edits
    after = apply_plan_to_files(plan, {str(path.resolve()): src})
    text = after[str(path.resolve())]
    assert "class Student {" in text
    assert "public string naam" in text
    assert "public constructor(string naam)" in text
    assert 'Student st = Student(naam="Jaap")' in text
    compile_pys(text)


def test_create_class_refuses_existing_type(tmp_path: Path) -> None:
    src = """
class Student {
    public string naam
    public constructor(string naam) {
        this.naam = naam
    }
}
Student st = Student(naam="Jaap")
"""
    path = tmp_path / "t.pys"
    path.write_text(src, encoding="utf-8")
    # Cursor on the call line
    line = next(i + 1 for i, L in enumerate(src.splitlines()) if "Student st" in L)
    plan = plan_create_class(path, line=line, column=10)
    assert plan.ok is False
    assert any("already" in c.message.lower() for c in plan.conflicts)
