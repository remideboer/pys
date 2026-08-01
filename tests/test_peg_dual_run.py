"""PEG brace engine must match classic RD ASTs (PEP 617-style dual-run)."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.lex import tokenize_with_flags
from transpiler.parse import parse_program_from_tokens


ROOT = Path(__file__).resolve().parent.parent
CORPUS = [
    ROOT / "examples" / "main.pys",
    ROOT / "examples" / "vehicles.pys",
    ROOT / "examples" / "funcs.pys",
    ROOT / "examples" / "gui" / "pokemontcg" / "main.pys",
    ROOT / "examples" / "gui" / "PyQt" / "main.pys",
]


def _dump(module) -> str:
    """Stable structural dump for cross-engine comparison."""
    return repr(module)


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_peg_matches_rd_on_brace_corpus(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    lexed = tokenize_with_flags(source)
    if not lexed.brace_mode and lexed.legacy_indent_keywords:
        pytest.skip("indent-mode file")
    rd = parse_program_from_tokens(lexed, source=source, engine="rd")
    peg = parse_program_from_tokens(lexed, source=source, engine="peg")
    assert _dump(peg) == _dump(rd)


def test_all_brace_goldens_peg_match_rd() -> None:
    golden = ROOT / "tests" / "golden"
    checked = 0
    for path in sorted(golden.rglob("*.pys")):
        source = path.read_text(encoding="utf-8")
        try:
            lexed = tokenize_with_flags(source)
        except Exception:  # noqa: BLE001
            continue
        if not lexed.brace_mode and lexed.legacy_indent_keywords:
            continue
        try:
            rd = parse_program_from_tokens(lexed, source=source, engine="rd")
            peg = parse_program_from_tokens(lexed, source=source, engine="peg")
        except Exception:  # noqa: BLE001 - error fixtures
            continue
        assert _dump(peg) == _dump(rd), path
        checked += 1
    assert checked >= 10
