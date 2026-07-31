"""PYS lexer: source text → tokens with spans (EBNF lexical + keywords)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator


class TokenKind(Enum):
    IDENT = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    CHAR = auto()
    KEYWORD = auto()
    OP = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACK = auto()
    RBRACK = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    SEMI = auto()
    LT = auto()
    GT = auto()
    NEWLINE = auto()
    COMMENT = auto()  # standalone `# ...` line (preserved in emit)
    EOF = auto()


KEYWORDS = frozenset(
    {
        "if",
        "else",
        "unless",
        "loop",
        "while",
        "for",
        "repeat",
        "times",
        "then",
        "do",
        "elif",
        "function",
        "func",
        "return",
        "class",
        "interface",
        "implements",
        "inherits",
        "super",
        "sealed",
        "import",
        "from",
        "all",
        "var",
        "const",
        "fix",
        "print",
        "pass",
        "break",
        "continue",
        "this",
        "and",
        "or",
        "not",
        "public",
        "private",
        "protected",
        "global",
        "package",
        "module",
        "int",
        "float",
        "char",
        "string",
        "bool",
        "list",
        "dict",
        "tuple",
        "set",
        "true",
        "false",
        "null",
        "tasks",
        "task",
        "await",
        "shared",
        "in",
        "as",
    }
)

# Multi-char operators longest-first
_OPS = [
    "++",
    "--",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
    "==",
    "!=",
    "<>",
    "<=",
    ">=",
    "&&",
    "||",
    "->",
]


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int
    index: int


@dataclass
class LexError(ValueError):
    message: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.message} (line {self.line}, column {self.column})"


def tokenize(source: str, *, emit_newlines: bool = False) -> list[Token]:
    """Tokenize PYS source. Block comments are skipped; standalone `#` lines become COMMENT tokens."""
    tokens: list[Token] = []
    i = 0
    line = 1
    col = 1
    n = len(source)
    at_line_start = True

    def peek(k: int = 0) -> str:
        j = i + k
        return source[j] if j < n else ""

    def bump(ch: str) -> None:
        nonlocal i, line, col, at_line_start
        i += 1
        if ch == "\n":
            line += 1
            col = 1
            at_line_start = True
        else:
            col += 1
            if ch not in " \r":
                at_line_start = False

    def add(kind: TokenKind, text: str, start_line: int, start_col: int, start_index: int) -> None:
        tokens.append(Token(kind, text, start_line, start_col, start_index))

    while i < n:
        ch = peek()
        if ch == "\t":
            raise LexError("tabs are not allowed; replace tabs with spaces.", line, col)
        if ch in " \r":
            bump(ch)
            continue
        if ch == "\n":
            if emit_newlines:
                add(TokenKind.NEWLINE, "\n", line, col, i)
            bump(ch)
            continue

        # Comments
        if ch == "#" and peek(1) == "#":
            start_line, start_col = line, col
            bump(ch)
            bump(peek())
            closed = False
            while i < n:
                if peek() == "/" and peek(1) == "#":
                    bump("/")
                    bump("#")
                    closed = True
                    break
                bump(peek())
            if not closed:
                raise LexError("Unterminated multiline comment. Close with /#.", start_line, start_col)
            continue
        if ch == "#":
            # Standalone `# ...` lines are preserved for emit; trailing `#` is skipped.
            standalone = at_line_start
            start_line, start_col, start_i = line, col, i
            chars: list[str] = []
            while i < n and peek() != "\n":
                chars.append(peek())
                bump(peek())
            if standalone:
                add(TokenKind.COMMENT, "".join(chars).strip(), start_line, start_col, start_i)
            continue

        start_line, start_col, start_i = line, col, i

        # Strings / chars
        if ch in {'"', "'"}:
            quote = ch
            bump(ch)
            chars: list[str] = [quote]
            while i < n and peek() != quote:
                if peek() == "\\" and i + 1 < n:
                    chars.append(peek())
                    bump(peek())
                    chars.append(peek())
                    bump(peek())
                    continue
                if peek() == "\n":
                    raise LexError("Unterminated string literal.", start_line, start_col)
                chars.append(peek())
                bump(peek())
            if i >= n:
                raise LexError("Unterminated string literal.", start_line, start_col)
            chars.append(quote)
            bump(quote)
            text = "".join(chars)
            # Single-quoted one char → CHAR (approx); longer stay STRING
            if quote == "'" and len(text) == 3:
                add(TokenKind.CHAR, text, start_line, start_col, start_i)
            else:
                add(TokenKind.STRING, text, start_line, start_col, start_i)
            continue

        # Numbers
        if ch.isdigit():
            text_chars: list[str] = []
            while peek().isdigit():
                text_chars.append(peek())
                bump(peek())
            if peek() == "." and peek(1).isdigit():
                text_chars.append(".")
                bump(".")
                while peek().isdigit():
                    text_chars.append(peek())
                    bump(peek())
                add(TokenKind.FLOAT, "".join(text_chars), start_line, start_col, start_i)
            else:
                add(TokenKind.INT, "".join(text_chars), start_line, start_col, start_i)
            continue

        # Ident / keyword
        if ch.isalpha() or ch == "_":
            text_chars = []
            while peek().isalnum() or peek() == "_":
                text_chars.append(peek())
                bump(peek())
            text = "".join(text_chars)
            kind = TokenKind.KEYWORD if text in KEYWORDS else TokenKind.IDENT
            add(kind, text, start_line, start_col, start_i)
            continue

        # Multi-char ops
        matched = False
        for op in _OPS:
            if source.startswith(op, i):
                for _ in op:
                    bump(peek())
                add(TokenKind.OP, op, start_line, start_col, start_i)
                matched = True
                break
        if matched:
            continue

        singles = {
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            "[": TokenKind.LBRACK,
            "]": TokenKind.RBRACK,
            ",": TokenKind.COMMA,
            ".": TokenKind.DOT,
            ":": TokenKind.COLON,
            ";": TokenKind.SEMI,
            "<": TokenKind.LT,
            ">": TokenKind.GT,
            "+": TokenKind.OP,
            "-": TokenKind.OP,
            "*": TokenKind.OP,
            "/": TokenKind.OP,
            "%": TokenKind.OP,
            "=": TokenKind.OP,
            "!": TokenKind.OP,
        }
        if ch in singles:
            bump(ch)
            add(singles[ch], ch, start_line, start_col, start_i)
            continue

        raise LexError(f"Unexpected character {ch!r}.", line, col)

    add(TokenKind.EOF, "", line, col, i)
    return tokens
