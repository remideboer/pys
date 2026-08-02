"""PYS lexer: source text → tokens with spans (EBNF lexical + keywords)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


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
    BLANK = auto()  # blank line preserved after `}` (legacy preprocess rule)
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
        "struct",
        "enum",
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
        "xor",
        "shift",
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
        "byte",
        "nibble",
        "int16",
        "int32",
        "int64",
        "dword",
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

# Indent-mode markers used when the file has no braces.
_LEGACY_INDENT_KEYWORDS = frozenset({"then", "do", "times", "func", "repeat"})

# Multi-char operators longest-first
_OPS = (
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
    "<<<",  # deferred rotate — lexed then rejected in parse
    ">>>",
    "<<",
    ">>",
    "<=",
    ">=",
    "**",
    "//",
    "&&",
    "||",
    "->",
)

# First character → ops starting with that char, longest first (_OPS is already ordered).
_OPS_BY_FIRST: dict[str, tuple[str, ...]] = {}
for _op in _OPS:
    _OPS_BY_FIRST.setdefault(_op[0], [])
    _OPS_BY_FIRST[_op[0]].append(_op)
_OPS_BY_FIRST = {k: tuple(v) for k, v in _OPS_BY_FIRST.items()}

_SINGLES: dict[str, TokenKind] = {
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
    "&": TokenKind.OP,
    "|": TokenKind.OP,
    "^": TokenKind.OP,
    "~": TokenKind.OP,
}

_SKIP_AFTER_RBRACE = frozenset({TokenKind.BLANK, TokenKind.COMMENT, TokenKind.NEWLINE})


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int
    index: int


@dataclass(frozen=True)
class TokenizeResult:
    """Tokens plus mode flags gathered during the single lex pass."""

    tokens: list[Token]
    brace_mode: bool
    legacy_indent_keywords: bool


@dataclass
class LexError(ValueError):
    message: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.message} (line {self.line}, column {self.column})"


def tokenize(source: str, *, emit_newlines: bool = False) -> list[Token]:
    """Tokenize PYS source. Block comments are skipped; standalone `#` lines become COMMENT tokens."""
    return tokenize_with_flags(source, emit_newlines=emit_newlines).tokens


def tokenize_with_flags(source: str, *, emit_newlines: bool = False) -> TokenizeResult:
    """Tokenize and report brace / legacy-indent cues without a second token scan."""
    tokens: list[Token] = []
    i = 0
    line = 1
    col = 1
    n = len(source)
    at_line_start = True
    after_rbrace = False
    brace_mode = False
    legacy_indent_keywords = False

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
        nonlocal after_rbrace, brace_mode, legacy_indent_keywords
        tokens.append(Token(kind, text, start_line, start_col, start_index))
        if kind in {TokenKind.LBRACE, TokenKind.RBRACE}:
            brace_mode = True
        if kind == TokenKind.KEYWORD and text in _LEGACY_INDENT_KEYWORDS:
            legacy_indent_keywords = True
        if kind == TokenKind.RBRACE:
            after_rbrace = True
        elif kind not in _SKIP_AFTER_RBRACE:
            after_rbrace = False

    def skip_collapsed_blanks() -> None:
        """Consume empty lines; emit BLANK only when armed after `}` (legacy rule)."""
        nonlocal after_rbrace
        while True:
            k = 0
            while True:
                ch = peek(k)
                if not ch or ch not in " \r":
                    break
                k += 1
            if peek(k) != "\n":
                return
            if after_rbrace:
                add(TokenKind.BLANK, "", line, col, i)
                after_rbrace = False
            for _ in range(k):
                bump(source[i])
            bump("\n")

    while i < n:
        ch = source[i]
        if ch == "\t":
            raise LexError("tabs are not allowed; replace tabs with spaces.", line, col)
        if ch in " \r":
            bump(ch)
            continue
        if ch == "\n":
            if emit_newlines:
                add(TokenKind.NEWLINE, "\n", line, col, i)
            bump(ch)
            skip_collapsed_blanks()
            continue

        # Comments
        if ch == "#" and peek(1) == "#":
            start_line, start_col = line, col
            bump(ch)
            bump(source[i] if i < n else "")
            closed = False
            while i < n:
                if source[i] == "/" and peek(1) == "#":
                    bump("/")
                    bump("#")
                    closed = True
                    break
                bump(source[i])
            if not closed:
                raise LexError("Unterminated multiline comment. Close with /#.", start_line, start_col)
            continue
        if ch == "#":
            # Standalone `# ...` lines are preserved for emit; trailing `#` is skipped.
            standalone = at_line_start
            start_line, start_col, start_i = line, col, i
            chars: list[str] = []
            while i < n and source[i] != "\n":
                chars.append(source[i])
                bump(source[i])
            if standalone:
                add(TokenKind.COMMENT, "".join(chars).strip(), start_line, start_col, start_i)
            continue

        start_line, start_col, start_i = line, col, i

        # Strings / chars
        if ch in {'"', "'"}:
            quote = ch
            bump(ch)
            chars = [quote]
            while i < n and source[i] != quote:
                if source[i] == "\\" and i + 1 < n:
                    chars.append(source[i])
                    bump(source[i])
                    chars.append(source[i])
                    bump(source[i])
                    continue
                if source[i] == "\n":
                    raise LexError("Unterminated string literal.", start_line, start_col)
                chars.append(source[i])
                bump(source[i])
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

        # Numbers: decimal / 0b… / 0x… with optional `_` separators
        if ch.isdigit():
            text_chars: list[str] = []
            # Binary / hexadecimal (must have at least one digit after prefix)
            if ch == "0" and i + 1 < n and source[i + 1] in "bBxX":
                text_chars.append("0")
                bump("0")
                prefix = source[i]
                text_chars.append(prefix)
                bump(prefix)
                base = 2 if prefix in "bB" else 16

                def _is_digit(c: str) -> bool:
                    if base == 2:
                        return c in "01"
                    return c.isdigit() or ("a" <= c.lower() <= "f")

                if i >= n or not _is_digit(source[i]):
                    raise LexError(
                        f"Invalid {'binary' if base == 2 else 'hexadecimal'} literal "
                        f"(expected digits after 0{prefix}).",
                        start_line,
                        start_col,
                    )
                while i < n:
                    if source[i] == "_":
                        if i + 1 >= n or not _is_digit(source[i + 1]):
                            raise LexError(
                                "Invalid numeric literal (misplaced `_`).",
                                line,
                                col,
                            )
                        text_chars.append("_")
                        bump("_")
                        continue
                    if not _is_digit(source[i]):
                        break
                    text_chars.append(source[i])
                    bump(source[i])
                add(TokenKind.INT, "".join(text_chars), start_line, start_col, start_i)
                continue

            # Decimal (optional `_` between digits) or float
            while i < n:
                if source[i] == "_":
                    if i + 1 >= n or not source[i + 1].isdigit():
                        raise LexError(
                            "Invalid numeric literal (misplaced `_`).",
                            line,
                            col,
                        )
                    text_chars.append("_")
                    bump("_")
                    continue
                if not source[i].isdigit():
                    break
                text_chars.append(source[i])
                bump(source[i])
            if i < n and source[i] == "." and peek(1).isdigit():
                text_chars.append(".")
                bump(".")
                while i < n and source[i].isdigit():
                    text_chars.append(source[i])
                    bump(source[i])
                add(TokenKind.FLOAT, "".join(text_chars), start_line, start_col, start_i)
            else:
                add(TokenKind.INT, "".join(text_chars), start_line, start_col, start_i)
            continue

        # Ident / keyword
        if ch.isalpha() or ch == "_":
            text_chars = []
            while i < n and (source[i].isalnum() or source[i] == "_"):
                text_chars.append(source[i])
                bump(source[i])
            text = "".join(text_chars)
            kind = TokenKind.KEYWORD if text in KEYWORDS else TokenKind.IDENT
            add(kind, text, start_line, start_col, start_i)
            continue

        # Multi-char ops (longest match among those sharing the first character)
        ops = _OPS_BY_FIRST.get(ch)
        if ops is not None:
            matched = False
            for op in ops:
                if source.startswith(op, i):
                    for _ in op:
                        bump(source[i])
                    add(TokenKind.OP, op, start_line, start_col, start_i)
                    matched = True
                    break
            if matched:
                continue

        kind = _SINGLES.get(ch)
        if kind is not None:
            bump(ch)
            add(kind, ch, start_line, start_col, start_i)
            continue

        raise LexError(f"Unexpected character {ch!r}.", line, col)

    add(TokenKind.EOF, "", line, col, i)
    return TokenizeResult(
        tokens=tokens,
        brace_mode=brace_mode,
        legacy_indent_keywords=legacy_indent_keywords,
    )
