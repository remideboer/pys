"""Lexer unit tests."""
from __future__ import annotations

import pytest

from transpiler.lex import LexError, TokenKind, tokenize


def test_tokenize_literals_and_keywords() -> None:
    toks = tokenize('print(42)\nint x = 1\n')
    kinds = [t.kind for t in toks if t.kind != TokenKind.EOF]
    assert TokenKind.KEYWORD in kinds
    assert TokenKind.INT in kinds
    assert any(t.text == "print" for t in toks)


def test_from_is_keyword() -> None:
    toks = tokenize("import A, B from mod.pys\n")
    from_toks = [t for t in toks if t.text == "from"]
    assert len(from_toks) == 1
    assert from_toks[0].kind == TokenKind.KEYWORD
    assert all(t.kind == TokenKind.IDENT for t in toks if t.text in {"A", "B"})


def test_tokenize_rejects_tabs() -> None:
    with pytest.raises(LexError, match="tabs"):
        tokenize("\tprint(1)\n")


def test_tokenize_skips_block_comment() -> None:
    toks = tokenize("## hide /#\nprint(1)\n")
    assert any(t.text == "print" for t in toks)
    assert not any("hide" in t.text for t in toks)


def test_tokenize_preserves_standalone_line_comment() -> None:
    toks = tokenize("# keep me\nprint(1)\n")
    comments = [t for t in toks if t.kind == TokenKind.COMMENT]
    assert len(comments) == 1
    assert comments[0].text == "# keep me"


def test_tokenize_skips_trailing_comment() -> None:
    toks = tokenize("print(1) # trail\n")
    assert not any(t.kind == TokenKind.COMMENT for t in toks)
    assert any(t.text == "print" for t in toks)


def test_tokenize_blank_after_rbrace_only() -> None:
    toks = tokenize("loop (x < 1) {\n    print(x)\n}\n\nif (true) {\n    print(1)\n}\n")
    blanks = [t for t in toks if t.kind == TokenKind.BLANK]
    assert len(blanks) == 1
    # blank after non-brace line is collapsed
    toks2 = tokenize("print(1)\n\nprint(2)\n")
    assert not any(t.kind == TokenKind.BLANK for t in toks2)


def test_all_golden_sources_lex() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parent / "golden"
    for pys in sorted(root.rglob("*.pys")):
        tokenize(pys.read_text(encoding="utf-8"))
