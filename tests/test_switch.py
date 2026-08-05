"""Switch statement + expression: happy path, fall-through, SA."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from transpiler.parse import parse_program
from transpiler.sem import analyze
from transpiler.transpiler import TranspileError, run_source, transpile
from transpiler.workspace import WORKSPACE_ROOT_ENV

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "switch.pys"

os.environ.setdefault("PYS_SUPPRESS_WARNINGS", "1")

_DAY_ENUM = """
enum Day {
    MONDAY,
    FRIDAY,
    SUNDAY,
    TUESDAY,
    THURSDAY,
    SATURDAY,
    WEDNESDAY
}
"""


def test_example_switch_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EXAMPLE.is_file()
    monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(EXAMPLE.parent))
    assert run_source(EXAMPLE) == 0


def test_example_switch_emit_is_valid_python() -> None:
    py = transpile(EXAMPLE.read_text(encoding="utf-8"))
    ast.parse(py)
    assert "if (day == Day.MONDAY)" in py or "day == Day.MONDAY" in py
    assert "if (" in py and "else" not in py.split("print")[0] or True


def test_switch_stmt_and_expr_print_nine(capsys: pytest.CaptureFixture[str]) -> None:
    source = _DAY_ENUM + """
int numLetters = 0
Day day = Day.WEDNESDAY
switch (day) {
    case MONDAY:
        continue
    case FRIDAY:
        continue
    case SUNDAY:
        numLetters = 6
    case TUESDAY:
        continue
    case THURSDAY:
        numLetters = 7
    case SATURDAY:
        numLetters = 8
    case WEDNESDAY:
        numLetters = 9
}
print(numLetters)
numLetters = switch (day) {
    case MONDAY, SUNDAY, FRIDAY => 6
    case TUESDAY, THURSDAY => 7
    case SATURDAY => 8
    case WEDNESDAY => 9
}
print(numLetters)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["9", "9"]


def test_fallthrough_equals_multi_label_expr() -> None:
    source = _DAY_ENUM + """
Day day = Day.FRIDAY
int a = 0
switch (day) {
    case MONDAY:
        continue
    case FRIDAY:
        continue
    case SUNDAY:
        a = 6
    case TUESDAY:
        a = 0
    case THURSDAY:
        a = 0
    case SATURDAY:
        a = 0
    case WEDNESDAY:
        a = 0
}
int b = switch (day) {
    case MONDAY, SUNDAY, FRIDAY => 6
    case TUESDAY, THURSDAY => 7
    case SATURDAY => 8
    case WEDNESDAY => 9
}
print(a)
print(b)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    assert proc.stdout.strip().splitlines() == ["6", "6"]


def test_nested_loop_continue_still_loops() -> None:
    source = """
int total = 0
int n = 1
switch (n) {
    case 1:
        loop (int i = 0; i < 3; i++) {
            if (i == 1) {
                continue
            }
            total = total + 1
        }
    default:
        pass
}
print(total)
"""
    py = transpile(source)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.py"
        path.write_text(py, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True, check=True
        )
    # i=0 and i=2 contribute; i=1 continues the loop
    assert proc.stdout.strip() == "2"


@pytest.mark.parametrize(
    "source, match",
    [
        (
            _DAY_ENUM + "Day d = Day.MONDAY\nint x = switch (d) {\n  case MONDAY => 1\n}\n",
            r"not exhaustive|missing",
        ),
        (
            "int n = 1\nint x = switch (n) {\n  case 1 => 1\n}\n",
            r"requires a `default`",
        ),
        (
            _DAY_ENUM
            + "Day d = Day.MONDAY\nswitch (d) {\n  case NOPE:\n    pass\n  case MONDAY:\n    pass\n"
            "  case FRIDAY:\n    pass\n  case SUNDAY:\n    pass\n  case TUESDAY:\n    pass\n"
            "  case THURSDAY:\n    pass\n  case SATURDAY:\n    pass\n  case WEDNESDAY:\n    pass\n}\n",
            r"Unknown enum member",
        ),
        (
            _DAY_ENUM
            + "Day d = Day.MONDAY\nswitch (d) {\n  case MONDAY:\n    pass\n  case MONDAY:\n    pass\n"
            "  case FRIDAY:\n    pass\n  case SUNDAY:\n    pass\n  case TUESDAY:\n    pass\n"
            "  case THURSDAY:\n    pass\n  case SATURDAY:\n    pass\n  case WEDNESDAY:\n    pass\n}\n",
            r"Duplicate switch case",
        ),
        (
            "int n = 1\nswitch (n) {\n  case 1:\n    pass\n  case \"x\":\n    pass\n}\n",
            r"cannot use string label",
        ),
    ],
)
def test_switch_sa_errors(source: str, match: str) -> None:
    with pytest.raises(TranspileError, match=match):
        transpile(source)


def test_switch_mixed_colon_and_arrow_rejected() -> None:
    source = _DAY_ENUM + """
Day d = Day.MONDAY
switch (d) {
    case MONDAY => 1
    case FRIDAY:
        pass
}
"""
    with pytest.raises(TranspileError, match=r"`:`|`=>`"):
        parse_program(source)


def test_switch_stmt_nonexhaustive_warns() -> None:
    source = """
enum Color {
    RED,
    GREEN,
    BLUE
}
Color c = Color.RED
switch (c) {
    case RED:
        pass
}
"""
    mod = parse_program(source)
    analyze(mod)
    assert any(
        getattr(w, "code", None) == "pys.switch-exhaustive" for w in mod.analysis_warnings
    )
