"""Token-based recursive-descent parser → AST."""
from __future__ import annotations

from .ast_nodes import (
    ArrayAlloc,
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AtomicDecl,
    AugAssignStmt,
    AwaitExpr,
    BinaryOp,
    BlankStmt,
    Block,
    BraceLiteral,
    BreakStmt,
    Call,
    Cast,
    ClassDef,
    CommentStmt,
    DataDef,
    DictLiteral,
    EnumDef,
    EnumMember,
    StructDef,
    StructField,
    EntityDef,
    ContinueStmt,
    SwitchCase,
    SwitchExpr,
    SwitchStmt,
    Expr,
    ExprStmt,
    FieldDecl,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    Identifier,
    IfStmt,
    ImportStmt,
    Index,
    InterfaceDef,
    InterpolatedString,
    KeywordArg,
    LambdaExpr,
    Literal,
    Member,
    MethodDef,
    Module,
    PassStmt,
    PrintStmt,
    PropagateExpr,
    RepeatStmt,
    ResultCtor,
    ResultPattern,
    ReturnStmt,
    SharedDecl,
    Slice,
    Span,
    TaskDef,
    TasksBlock,
    TraitDef,
    TraitRequire,
    TraitUse,
    TupleLiteral,
    UnaryOp,
    WhileStmt,
)
from .lex import LexError, Token, TokenKind, TokenizeResult, tokenize, tokenize_with_flags

_TYPES = frozenset(
    {
        "int",
        "float",
        "char",
        "string",
        "bool",
        "void",
        "byte",
        "nibble",
        "int16",
        "int32",
        "int64",
        "dword",
    }
)
_ATOMIC_PRIMITIVES = frozenset(
    {"int", "int16", "int32", "int64", "dword", "bool"}
)
_VIS = frozenset({"global", "package", "module"})
_ROTATE_DEFERRED = (
    "Bitwise rotate (`<<<` / `>>>`) is not implemented yet — use `<<` / `>>` for shifts."
)


class ParseError(ValueError):
    def __init__(
        self,
        message: str,
        line: int = 1,
        column: int = 1,
        *,
        code: str | None = None,
        tips: list[str] | None = None,
        suggested_fix: str | None = None,
    ) -> None:
        self.message = message
        self.line = line
        self.column = column
        self.code = code
        self.tips = tips or []
        self.suggested_fix = suggested_fix
        super().__init__(f"{message} (line {line}, column {column})")


class FatalParseError(ParseError):
    """Semantic fault discovered while parsing; do not fall back to legacy."""


# Member-kind phases for enforced ordering (CER / requirements/enforced_ordering.md).
# Higher number = later section. Seeing an earlier kind after a later one is an error.
_PHASE_STRUCT_FIX = 0
_PHASE_STRUCT_FIELD = 1
_PHASE_TRAIT_REQUIRES = 0
_PHASE_TRAIT_METHOD = 1
_PHASE_CLASS_CONST = 0
_PHASE_CLASS_FIX = 1
_PHASE_CLASS_FIELD = 2
_PHASE_CLASS_CTOR = 3
_PHASE_CLASS_METHOD = 4
_PHASE_ENTITY_IDENTITY = 0
_PHASE_ENTITY_FIX = 1
_PHASE_ENTITY_FIELD = 2
_PHASE_ENTITY_CTOR = 3
_PHASE_ENTITY_METHOD = 4

_MSG_IMPORT_AFTER = (
    "Import statement found after other code. All imports must appear at the top "
    "of the file, before any declaration or statement, so a reader sees the file's "
    "full dependency surface before its content."
)
_MSG_METHOD_BEFORE_FIELDS = (
    "Method '{name}' found before the fields/constructor section. PYS requires "
    "class members in the order: const fields, fix fields, fields, constructors, "
    "methods — this fixed order lets a reader find any member category without "
    "scanning the whole class."
)
_MSG_FIELD_AFTER_CTOR = (
    "Field '{name}' found after a constructor. Fields must be declared before any "
    "constructor, so a reader sees the full state shape before the code that "
    "initializes it."
)
_MSG_CONST_AFTER_FIELDS = (
    "Constant '{name}' found after non-const fields. Constants must appear first, "
    "since they represent fixed, class-wide facts rather than per-instance state."
)
_MSG_FIX_AFTER_MUTABLE = (
    "Fix field '{name}' found after mutable fields. Fix fields must appear before "
    "mutable fields, so immutable state is visible before per-instance mutable state."
)
_MSG_TRAIT_METHOD_BEFORE_REQUIRES = (
    "Method '{name}' found before trait {trait}'s 'requires' section. Declare "
    "everything the trait depends on its host for before defining methods that "
    "rely on it, so the dependency is visible first."
)
_MSG_ENTITY_BEFORE_IDENTITY = (
    "Field '{name}' found before identity field '{identity}'. An entity's identity "
    "field(s) must be declared first, since they are the single most important "
    "structural fact about the entity — its key."
)


def _require_member_phase(
    p: "_Tok",
    phase: list[int],
    kind: int,
    *,
    message: str,
    code: str,
    tips: list[str] | None = None,
) -> None:
    """Advance ordered body phase, or raise FatalParseError if ``kind`` is too early."""
    if kind < phase[0]:
        raise FatalParseError(
            message,
            p.cur().line,
            p.cur().column,
            code=code,
            tips=tips or [
                "PYS enforces member kind order so readers find each category "
                "without scanning the whole body."
            ],
        )
    phase[0] = kind


_PACKRAT_FAIL = object()


def _packrat(rule_id: str):
    """Memoize a production at (rule_id, position) when ``_Tok.memo`` is enabled."""

    def decorator(fn):
        def wrapped(p: _Tok):
            memo = p.memo
            if memo is None:
                return fn(p)
            key = (rule_id, p.i)
            cached = memo.get(key)
            if cached is not None:
                marker, payload = cached
                if marker is _PACKRAT_FAIL:
                    raise payload
                result, end, end_gt = payload
                p.i = end
                p._pending_gt = end_gt
                return result
            start = p.i
            start_gt = p._pending_gt
            try:
                result = fn(p)
            except ParseError as exc:
                memo[key] = (_PACKRAT_FAIL, exc)
                p.i = start
                p._pending_gt = start_gt
                raise
            memo[key] = (None, (result, p.i, p._pending_gt))
            return result

        return wrapped

    return decorator


class _Tok:
    def __init__(self, tokens: list[Token], *, packrat: bool = False) -> None:
        self.tokens = tokens
        self.i = 0
        self.task_serial = 0
        # Extra `>` closers pending after splitting a `>>` / `>>>` shift token
        # inside generic type arguments (`list<tuple<int, string>>`).
        self._pending_gt = 0
        # Packrat / PEG memo (PEP 617): per-parse only when enabled.
        self.memo: dict | None = {} if packrat else None

    def cur(self) -> Token:
        return self.tokens[self.i]

    def peek(self, k: int = 0) -> Token:
        j = self.i + k
        if j >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[j]

    def done(self) -> bool:
        return self.cur().kind == TokenKind.EOF

    def at(self, *kinds: TokenKind, text: str | None = None) -> bool:
        t = self.cur()
        if t.kind == TokenKind.EOF:
            return TokenKind.EOF in kinds
        if kinds and t.kind not in kinds:
            return False
        if text is not None and t.text != text:
            return False
        return True

    def at_kw(self, *words: str) -> bool:
        t = self.cur()
        return t.kind == TokenKind.KEYWORD and t.text in words

    def at_gt(self) -> bool:
        if self._pending_gt > 0:
            return True
        t = self.cur()
        if t.kind == TokenKind.GT:
            return True
        return t.kind == TokenKind.OP and t.text in {">>", ">>>"}

    def eat_gt(self) -> Token:
        """Consume one generic closer `>`, splitting `>>` / `>>>` if needed."""
        if self._pending_gt > 0:
            self._pending_gt -= 1
            t = self.cur()
            return Token(TokenKind.GT, ">", t.line, t.column, t.index)
        t = self.cur()
        if t.kind == TokenKind.GT:
            self.i += 1
            return t
        if t.kind == TokenKind.OP and t.text == ">>":
            self.i += 1
            self._pending_gt = 1
            return Token(TokenKind.GT, ">", t.line, t.column, t.index)
        if t.kind == TokenKind.OP and t.text == ">>>":
            self.i += 1
            self._pending_gt = 2
            return Token(TokenKind.GT, ">", t.line, t.column, t.index)
        raise ParseError(f"Expected '>', got {t.kind.name} {t.text!r}", t.line, t.column)

    def eat(self, *kinds: TokenKind, text: str | None = None) -> Token:
        t = self.cur()
        if kinds and t.kind not in kinds:
            raise ParseError(f"Expected {kinds}, got {t.kind.name} {t.text!r}", t.line, t.column)
        if text is not None and t.text != text:
            raise ParseError(f"Expected {text!r}, got {t.text!r}", t.line, t.column)
        self.i += 1
        return t

    def eat_kw(self, *words: str) -> Token:
        t = self.cur()
        if t.kind != TokenKind.KEYWORD or t.text not in words:
            raise ParseError(f"Expected keyword {words}, got {t.text!r}", t.line, t.column)
        self.i += 1
        return t

    def span(self) -> Span:
        t = self.cur()
        return Span(t.line, t.column)

    def token_span(self, t: Token | None = None) -> Span:
        """Span covering one token (start + end column)."""
        tok = t if t is not None else self.cur()
        end_col = tok.column + max(len(tok.text), 1)
        return Span(tok.line, tok.column, tok.line, end_col)

    def close_span(self, start: Span, end_tok: Token | None = None) -> Span:
        """Extend ``start`` through ``end_tok`` (default: previous token)."""
        tok = end_tok if end_tok is not None else self.tokens[max(self.i - 1, 0)]
        end_col = tok.column + max(len(tok.text), 1)
        return Span(start.line, start.column, tok.line, end_col)


def _gt_close_count(t: Token) -> int:
    """How many generic `>` this token closes (0 if not a closer)."""
    if t.kind == TokenKind.GT:
        return 1
    if t.kind == TokenKind.OP and t.text == ">>":
        return 2
    if t.kind == TokenKind.OP and t.text == ">>>":
        return 3
    return 0


def parse_program(source: str) -> Module:
    try:
        lexed = tokenize_with_flags(source)
    except LexError as exc:
        from .transpiler import TranspileError

        raise TranspileError(str(exc.message), exc.line, exc.column, "") from exc
    return parse_program_from_tokens(lexed, source=source)


def parse_program_from_tokens(
    tokens: list[Token] | TokenizeResult,
    *,
    source: str = "",
    engine: str = "auto",
) -> Module:
    """Parse from an existing token list (lex once; benches / PEG dual-run).

    ``engine``: ``\"rd\"`` classic recursive descent, ``\"peg\"`` packrat brace
    parser, ``\"auto\"`` uses the default brace engine (PEG when enabled).
    """
    if isinstance(tokens, TokenizeResult):
        lexed = tokens
        token_list = lexed.tokens
        brace_mode = lexed.brace_mode
        legacy_indent = lexed.legacy_indent_keywords
    else:
        token_list = tokens
        brace_mode = any(t.kind in {TokenKind.LBRACE, TokenKind.RBRACE} for t in token_list)
        legacy_indent = any(
            t.kind == TokenKind.KEYWORD and t.text in {"then", "do", "times", "func", "repeat"}
            for t in token_list
        )

    # Indent-style forms (then/func/repeat/…) — only when there are no braces.
    # (`times` is also a common parameter name in brace mode.)
    if not brace_mode and legacy_indent:
        try:
            body = _parse_indent_program(source)
            return Module(span=Span(1, 1), source=source, body=body, brace_mode=False)
        except ParseError as exc:
            from .transpiler import TranspileError

            raise TranspileError(str(exc), exc.line, exc.column, "") from exc

    # PEG = same productions with packrat memo (PEP 617); RD = memo off.
    use_peg = engine == "peg" or (engine == "auto" and _BRACE_ENGINE == "peg")
    if use_peg:
        from . import peg as peg_mod

        return peg_mod.parse_brace_module(
            token_list, source=source, brace_mode=brace_mode
        )

    return _parse_brace_module_rd(
        token_list, source=source, brace_mode=brace_mode, packrat=False
    )


# Default stays RD: packrat adds memo overhead and this grammar rarely backtracks
# enough to win (measured in CER-003). Use engine=\"peg\" / set_brace_engine for dual-run.
_BRACE_ENGINE = "rd"


def set_brace_engine(engine: str) -> None:
    """Test helper: ``\"rd\"`` or ``\"peg\"``."""
    global _BRACE_ENGINE
    if engine not in {"rd", "peg"}:
        raise ValueError(f"unsupported brace engine {engine!r}")
    _BRACE_ENGINE = engine


def _finish_stmt_terminator(p: _Tok) -> tuple[int, bool]:
    """After a statement: end line of last token, and whether an optional `;` followed."""
    end_line = p.tokens[max(p.i - 1, 0)].line
    had_semi = False
    if p.at(TokenKind.SEMI):
        p.eat(TokenKind.SEMI)
        had_semi = True
    return end_line, had_semi


def _check_same_line_boundary(
    p: _Tok,
    *,
    prev_end_line: int | None,
    had_semi: bool,
) -> None:
    """Require `;` when the next non-noise token shares the previous statement's line."""
    if prev_end_line is None or p.done():
        return
    if p.cur().line == prev_end_line and not had_semi:
        raise FatalParseError(
            "Two statements on the same line must be separated by ';'.",
            p.cur().line,
            p.cur().column,
            code="pys.same-line-statements",
            tips=[
                "Insert ';' between them, or put each statement on its own line.",
            ],
        )


def _parse_brace_module_rd(
    tokens: list[Token],
    *,
    source: str,
    brace_mode: bool,
    packrat: bool = False,
) -> Module:
    p = _Tok(tokens, packrat=packrat)
    body: list = []
    seen_non_import = False
    prev_end_line: int | None = None
    had_semi = False
    try:
        while not p.done():
            if p.at(TokenKind.BLANK):
                t = p.eat(TokenKind.BLANK)
                body.append(BlankStmt(span=Span(t.line, t.column)))
                continue
            if p.at(TokenKind.COMMENT):
                t = p.eat(TokenKind.COMMENT)
                body.append(CommentStmt(span=Span(t.line, t.column), text=t.text))
                continue
            _check_same_line_boundary(p, prev_end_line=prev_end_line, had_semi=had_semi)
            if p.at_kw("import", "from"):
                if seen_non_import:
                    raise FatalParseError(
                        _MSG_IMPORT_AFTER,
                        p.cur().line,
                        p.cur().column,
                        code="pys.order-import",
                        tips=[
                            "Move every `import` / `import … from …` to the top of the file, "
                            "before declarations and statements."
                        ],
                    )
                body.append(_parse_toplevel(p))
                prev_end_line, had_semi = _finish_stmt_terminator(p)
                continue
            seen_non_import = True
            body.append(_parse_toplevel(p))
            prev_end_line, had_semi = _finish_stmt_terminator(p)
    except FatalParseError as exc:
        from .transpiler import TranspileError

        raise TranspileError(
            exc.message,
            exc.line,
            exc.column,
            "",
            code=exc.code,
            tips=exc.tips,
            suggested_fix=getattr(exc, "suggested_fix", None),
        ) from exc
    except ParseError as exc:
        from .transpiler import TranspileError

        raise TranspileError(
            str(exc),
            exc.line,
            exc.column,
            "",
            code=getattr(exc, "code", None),
            tips=getattr(exc, "tips", None),
            suggested_fix=getattr(exc, "suggested_fix", None),
        ) from exc

    return Module(span=Span(1, 1), source=source, body=body, brace_mode=brace_mode)


def _expr_from_text(text: str) -> Expr:
    p = _Tok(tokenize(text))
    expr = _parse_expression(p)
    if not p.done():
        raise ParseError(f"Unexpected token {p.cur().text!r}", p.cur().line, p.cur().column)
    return expr


def _parse_indent_program(source: str) -> list:
    """Minimal indent-mode parser for then/func/repeat goldens."""
    entries: list[tuple[int, str, int]] = []
    for line_no, raw in enumerate(source.splitlines(), start=1):
        if not raw.strip():
            continue
        stripped = raw.lstrip(" ")
        if stripped.startswith("##") or stripped.startswith("#"):
            continue
        indent = len(raw) - len(stripped)
        entries.append((indent, stripped.rstrip(), line_no))

    class IP:
        def __init__(self) -> None:
            self.i = 0

        def cur(self) -> tuple[int, str, int]:
            return entries[self.i]

        def done(self) -> bool:
            return self.i >= len(entries)

        def parse_block(self, parent_indent: int) -> Block:
            stmts: list = []
            while not self.done():
                ind, _, _ = self.cur()
                if ind <= parent_indent:
                    break
                stmts.append(self.parse_stmt())
            return Block(statements=stmts)

        def parse_stmt(self):
            ind, text, line_no = self.cur()
            sp = Span(line_no, ind + 1)
            self.i += 1

            if text.startswith("func ") and text.endswith(":"):
                header = text[len("func ") : -1].strip()
                name, _, rest = header.partition("(")
                if not rest.endswith(")"):
                    raise ParseError("Malformed func header", line_no, ind + 1)
                args = rest[:-1].strip()
                params = [p.strip() for p in args.split(",") if p.strip()] if args else []
                # strip types from params if present
                clean: list[str] = []
                for p in params:
                    parts = p.split()
                    clean.append(parts[-1])
                body = self.parse_block(ind)
                return FunctionDef(span=sp, name=name.strip(), params=clean, body=body)

            if text.startswith("repeat ") and text.endswith("times:"):
                mid = text[len("repeat ") : -len("times:")].strip()
                if mid.endswith(" "):
                    mid = mid.strip()
                # `repeat 3 times:` → mid is `3`
                count = _expr_from_text(mid)
                body = self.parse_block(ind)
                return RepeatStmt(span=sp, count=count, body=body)

            if text.startswith("if ") and " then:" in text:
                cond_text = text[len("if ") : text.rindex(" then:")].strip()
                cond = _expr_from_text(cond_text)
                then_body = self.parse_block(ind)
                else_body = None
                if not self.done():
                    eind, etext, _ = self.cur()
                    if eind == ind and etext in {"else:", "else"}:
                        self.i += 1
                        else_body = self.parse_block(ind)
                return IfStmt(span=sp, cond=cond, then_body=then_body, else_body=else_body)

            if text == "else:" or text == "else":
                raise ParseError("Unexpected else", line_no, ind + 1)

            if text.startswith("print(") or text.startswith("print "):
                # Reuse token statement parse
                p = _Tok(tokenize(text))
                return _parse_print(p)

            # typed decl or assignment or call
            p = _Tok(tokenize(text))
            try:
                return _parse_statement(p)
            except ParseError as exc:
                raise ParseError(str(exc), line_no, ind + 1) from exc

    ip = IP()
    body: list = []
    while not ip.done():
        body.append(ip.parse_stmt())
    return body


@_packrat("toplevel")
def _parse_toplevel(p: _Tok):
    if p.at(TokenKind.BLANK):
        t = p.eat(TokenKind.BLANK)
        return BlankStmt(span=Span(t.line, t.column))
    if p.at(TokenKind.COMMENT):
        t = p.eat(TokenKind.COMMENT)
        return CommentStmt(span=Span(t.line, t.column), text=t.text)
    if p.at_kw("from"):
        return _parse_from_import(p)
    if p.at_kw("import"):
        return _parse_import(p)
    if p.at_kw(*_VIS):
        vis = p.eat(TokenKind.KEYWORD).text
        if p.at_kw("function"):
            return _parse_function(p, visibility=vis)
        if p.at_kw("sealed", "abstract"):
            return _parse_class(p, visibility=vis)
        if p.at_kw("class"):
            return _parse_class(p, visibility=vis)
        if p.at_kw("fix") and p.peek(1).kind == TokenKind.KEYWORD and p.peek(1).text == "struct":
            return _parse_struct(p, visibility=vis, type_fix=True)
        if p.at_kw("struct"):
            return _parse_struct(p, visibility=vis)
        if p.at_kw("data"):
            return _parse_data(p, visibility=vis)
        if p.at_kw("entity"):
            return _parse_entity(p, visibility=vis)
        if p.at_kw("enum"):
            return _parse_enum(p, visibility=vis)
        if p.at_kw("interface"):
            return _parse_interface(p, visibility=vis)
        if p.at_kw("trait"):
            return _parse_trait(p, visibility=vis)
        if p.at_kw("const", "fix") or p.at_kw(*_TYPES) or p.at_kw("var"):
            return _parse_decl(p, visibility=vis)
        raise ParseError("Expected declaration after visibility", p.cur().line, p.cur().column)
    if p.at_kw("function"):
        return _parse_function(p)
    if p.at_kw("sealed", "abstract"):
        return _parse_class(p)
    if p.at_kw("class"):
        return _parse_class(p)
    if p.at_kw("fix") and p.peek(1).kind == TokenKind.KEYWORD and p.peek(1).text == "struct":
        return _parse_struct(p, type_fix=True)
    if p.at_kw("struct"):
        return _parse_struct(p)
    if p.at_kw("data"):
        return _parse_data(p)
    if p.at_kw("entity"):
        return _parse_entity(p)
    if p.at_kw("enum"):
        return _parse_enum(p)
    if p.at_kw("interface"):
        return _parse_interface(p)
    if p.at_kw("trait"):
        return _parse_trait(p)
    if p.at_kw("shared"):
        return _parse_shared(p)
    if p.at_kw("atomic"):
        return _parse_atomic(p)
    if p.at_kw("tasks"):
        return _parse_tasks(p)
    if p.at_kw("task"):
        raise ParseError(
            "`task` must appear inside a `tasks` block.",
            p.cur().line,
            p.cur().column,
        )
    return _parse_statement(p)


def _parse_shared(p: _Tok) -> SharedDecl:
    sp = p.span()
    p.eat_kw("shared")
    if p.at_kw("atomic"):
        raise FatalParseError(
            "`shared atomic` is redundant — write `atomic <type> name = …` "
            "(`atomic` already implies shared for capture).",
            p.cur().line,
            p.cur().column,
            code="pys.atomic-redundant",
            tips=["Drop `shared` and use `atomic int counter = 0`."],
        )
    dtype = ""
    if (
        p.at_kw(*_TYPES)
        or p.at_kw(
            "nullable",
            "result",
            "lambda",
            "list",
            "dict",
            "tuple",
            "set",
        )
        or p.at(TokenKind.IDENT)
    ):
        dtype = _parse_type_name(p)
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.OP, text="=")
    value = _parse_expression(p)
    return SharedDecl(span=sp, name=name, value=value, declare_type=dtype)


def _parse_atomic(p: _Tok) -> AtomicDecl:
    sp = p.span()
    p.eat_kw("atomic")
    if p.at_kw("shared"):
        raise FatalParseError(
            "`atomic shared` is redundant — write `atomic <type> name = …` "
            "(`atomic` already implies shared for capture).",
            p.cur().line,
            p.cur().column,
            code="pys.atomic-redundant",
            tips=["Drop `shared` and use `atomic int counter = 0`."],
        )
    if p.at_kw("nullable"):
        raise FatalParseError(
            "`atomic nullable<T>` is not allowed; nullable state has no "
            "atomic operation contract.",
            p.cur().line,
            p.cur().column,
            code="pys.nullable-atomic",
            tips=["Use a shared nullable value and copy a synchronized snapshot to a local."],
        )
    if not (p.at_kw(*_TYPES) or p.at(TokenKind.IDENT)):
        raise FatalParseError(
            "`atomic` requires a primitive type "
            "(int, int16, int32, int64, dword, or bool).",
            p.cur().line,
            p.cur().column,
            code="pys.atomic-type",
            tips=["Example: `atomic int counter = 0`."],
        )
    dtype = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
    if dtype not in _ATOMIC_PRIMITIVES:
        raise FatalParseError(
            f"`atomic {dtype}` is not allowed — only int-like widths and bool "
            f"(float/string are excluded).",
            sp.line,
            sp.column,
            code="pys.atomic-type",
            tips=[
                "Use `atomic int …` (or int16/int32/int64/dword/bool).",
                "For float accumulators, use an explicit compareAndSet loop.",
            ],
        )
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.OP, text="=")
    value = _parse_expression(p)
    return AtomicDecl(span=sp, name=name, value=value, declare_type=dtype)


def _parse_tasks(p: _Tok) -> TasksBlock:
    sp = p.span()
    p.eat_kw("tasks")
    group_id = p.task_serial
    p.task_serial += 1
    p.eat(TokenKind.LBRACE)
    tasks: list[TaskDef] = []
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        tasks.append(_parse_task(p))
    p.eat(TokenKind.RBRACE)
    return TasksBlock(span=sp, group_id=group_id, tasks=tasks)


def _parse_task(p: _Tok) -> TaskDef:
    sp = p.span()
    p.eat_kw("task")
    name = ""
    params: list[str] = []
    is_template = False
    if not p.at(TokenKind.LBRACE):
        name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if p.at(TokenKind.LPAREN):
            is_template = True
            p.eat(TokenKind.LPAREN)
            if not p.at(TokenKind.RPAREN):
                params.append(_parse_param(p)[1])
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    params.append(_parse_param(p)[1])
            p.eat(TokenKind.RPAREN)
    if not name:
        name = f"_anon_{p.task_serial}"
        p.task_serial += 1
    body = _parse_block(p)
    return TaskDef(span=sp, name=name, params=params, is_template=is_template, body=body)


def _parse_import(p: _Tok) -> ImportStmt:
    sp = p.span()
    p.eat_kw("import")
    if p.at_kw("all"):
        p.eat_kw("all")
        p.eat_kw("from")
        mod = _parse_dotted_name(p)
        return ImportStmt(span=sp, kind="all_from", module=mod)
    first = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    # `import A, B from module` — `from` is the keyword introducing the module.
    if p.at(TokenKind.COMMA):
        names = [first]
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            if p.at_kw("from"):
                raise ParseError(
                    "Expected imported name after `,` (hint: `from` is a keyword).",
                    p.cur().line,
                    p.cur().column,
                )
            names.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        p.eat_kw("from")
        mod = _parse_dotted_name(p)
        return ImportStmt(span=sp, kind="name_from", module=mod, name=names[0], names=names)
    if p.at_kw("from"):
        # PYS `import Name from module` vs adjacent Python-style `from module import Name`
        # (newlines are not statement separators in the token stream). Prefer PYS when the
        # look-ahead is `from mod import Name from …` (back-to-back name_from imports).
        if (
            p.peek(2).kind == TokenKind.KEYWORD
            and p.peek(2).text == "import"
            and not _peek_pys_name_from_then_from(p)
        ):
            return ImportStmt(span=sp, kind="module", module=first)
        p.eat_kw("from")
        mod = _parse_dotted_name(p)
        return ImportStmt(span=sp, kind="name_from", module=mod, name=first, names=[first])
    mod = first
    while p.at(TokenKind.DOT):
        p.eat(TokenKind.DOT)
        part = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if part == "pys":
            break
        mod += "." + part
    if p.at_kw("as"):
        p.eat_kw("as")
        alias = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        return ImportStmt(span=sp, kind="as", module=mod, alias=alias)
    return ImportStmt(span=sp, kind="module", module=mod)


def _peek_pys_name_from_then_from(p: _Tok) -> bool:
    """True when at ``from`` the stream is ``from mod import name[,…] from`` (PYS)."""
    i = 0
    t0 = p.peek(i)
    if not (t0.kind == TokenKind.KEYWORD and t0.text == "from"):
        return False
    i += 1
    # Skip a simple dotted module ref (path prefixes are rare in this ambiguity).
    t = p.peek(i)
    if t.kind not in {TokenKind.IDENT, TokenKind.KEYWORD}:
        return False
    i += 1
    while p.peek(i).kind == TokenKind.DOT:
        i += 1
        t = p.peek(i)
        if t.kind not in {TokenKind.IDENT, TokenKind.KEYWORD}:
            return False
        i += 1
        if t.text == "pys":
            break
    t = p.peek(i)
    if not (t.kind == TokenKind.KEYWORD and t.text == "import"):
        return False
    i += 1
    t = p.peek(i)
    if t.kind not in {TokenKind.IDENT, TokenKind.KEYWORD}:
        return False
    i += 1
    while p.peek(i).kind == TokenKind.COMMA:
        i += 1
        t = p.peek(i)
        if t.kind not in {TokenKind.IDENT, TokenKind.KEYWORD}:
            return False
        i += 1
    t = p.peek(i)
    return t.kind == TokenKind.KEYWORD and t.text == "from"


def _parse_from_import(p: _Tok) -> ImportStmt:
    """Python-style `from module import name[, name…]` (used by some examples)."""
    sp = p.span()
    p.eat_kw("from")
    mod = _parse_dotted_name(p)
    p.eat_kw("import")
    if p.at(TokenKind.OP, text="*") or p.at_kw("all"):
        if p.at(TokenKind.OP, text="*"):
            p.eat(TokenKind.OP, text="*")
        else:
            p.eat_kw("all")
        return ImportStmt(span=sp, kind="all_from", module=mod)
    names = [p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text]
    while p.at(TokenKind.COMMA):
        p.eat(TokenKind.COMMA)
        names.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
    return ImportStmt(span=sp, kind="name_from", module=mod, name=names[0], names=names)


def _parse_dotted_name(p: _Tok) -> str:
    """Parse a module ref: ``math``, ``a.b``, ``funcs.pys``, ``../pkg/funcs.pys``."""
    parts: list[str] = []
    # Leading ``../`` or ``./`` path prefixes.
    while True:
        if p.at(TokenKind.DOT) and p.peek(1).kind == TokenKind.DOT:
            p.eat(TokenKind.DOT)
            p.eat(TokenKind.DOT)
            parts.append("..")
            if p.at(TokenKind.OP, text="/"):
                p.eat(TokenKind.OP, text="/")
                parts.append("/")
            continue
        if (
            p.at(TokenKind.DOT)
            and p.peek(1).kind == TokenKind.OP
            and p.peek(1).text == "/"
        ):
            p.eat(TokenKind.DOT)
            p.eat(TokenKind.OP, text="/")
            parts.append("./")
            continue
        break

    parts.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
    while True:
        if p.at(TokenKind.OP, text="/"):
            p.eat(TokenKind.OP, text="/")
            parts.append("/")
            parts.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
            continue
        if p.at(TokenKind.DOT):
            p.eat(TokenKind.DOT)
            nxt = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            if nxt == "pys":
                parts.append(".pys")
                break
            parts.append(".")
            parts.append(nxt)
            continue
        break
    return "".join(parts)


def _looks_like_typed_name(p: _Tok) -> bool:
    """TYPE name (  — used for optional function return type."""
    t0 = p.cur()
    if t0.kind not in {TokenKind.KEYWORD, TokenKind.IDENT}:
        return False
    if t0.text in {
        "function", "class", "interface", "import", "from", "if", "unless", "loop",
        "return", "pass", "break", "continue", "else", "tasks", "task", "shared",
    }:
        return False
    if p.peek(1).kind == TokenKind.LPAREN:
        return False
    if p.peek(1).kind == TokenKind.LT:
        depth = 0
        k = 1
        while True:
            t = p.peek(k)
            if t.kind == TokenKind.EOF:
                return False
            if t.kind == TokenKind.LT:
                depth += 1
            else:
                closes = _gt_close_count(t)
                if closes:
                    depth -= closes
                    if depth == 0:
                        return (
                            p.peek(k + 1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
                            and p.peek(k + 2).kind == TokenKind.LPAREN
                        )
                    if depth < 0:
                        return False
            k += 1
    if p.peek(1).kind not in {TokenKind.IDENT, TokenKind.KEYWORD}:
        return False
    return p.peek(2).kind == TokenKind.LPAREN


def _parse_type_name(p: _Tok) -> str:
    """Parse `Type` or `Type<Arg, Nested<T>>` type references."""
    base_tok = p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
    base = base_tok.text
    if not p.at(TokenKind.LT):
        if base == "nullable":
            raise FatalParseError(
                "`nullable<T>` requires exactly one underlying type.",
                base_tok.line,
                base_tok.column,
                code="pys.nullable-arity",
                tips=["Write `nullable<Type>`."],
            )
        return base
    p.eat(TokenKind.LT)
    if base == "lambda":
        return _parse_lambda_type_args(p, base_tok)
    args = [_parse_type_name(p)]
    while p.at(TokenKind.COMMA):
        p.eat(TokenKind.COMMA)
        args.append(_parse_type_name(p))
    p.eat_gt()
    if base == "result" and len(args) != 2:
        raise FatalParseError(
            "`result<T, E>` requires exactly two type arguments: "
            "the success type T and error type E.",
            base_tok.line,
            base_tok.column,
            code="pys.result-arity",
            tips=["Write `result<SuccessType, ErrorType>`."],
        )
    if base == "result" and args[1] == "void":
        raise FatalParseError(
            "`result<T, E>` requires a concrete error type; E cannot be `void`.",
            base_tok.line,
            base_tok.column,
            code="pys.result-error-type",
            tips=["Choose an error value type such as `string` or an enum."],
        )
    if base == "nullable" and len(args) != 1:
        raise FatalParseError(
            "`nullable<T>` requires exactly one underlying type.",
            base_tok.line,
            base_tok.column,
            code="pys.nullable-arity",
            tips=["Write `nullable<Type>`."],
        )
    if base == "nullable" and args[0] == "void":
        raise FatalParseError(
            "`nullable<void>` is invalid because void is not a runtime value.",
            base_tok.line,
            base_tok.column,
            code="pys.nullable-void",
            tips=["Choose the concrete value type that may be absent."],
        )
    if base == "nullable" and args[0].startswith("nullable<"):
        raise FatalParseError(
            f"`{args[0]}` is already nullable; nested nullable types add no state.",
            base_tok.line,
            base_tok.column,
            code="pys.nullable-nested",
            tips=[f"Use `{args[0]}` directly."],
        )
    return f"{base}<{', '.join(args)}>"


def _parse_lambda_type_args(p: _Tok, base_tok: Token) -> str:
    """Parse inside `lambda<…>` after `<` was eaten.

    Forms: sugar `lambda<R>`, explicit zero-param `lambda<-> R>`,
    and `lambda<P… -> R>`. Old comma-only multi-arg forms are rejected.
    """
    if p.at(TokenKind.OP, text="->"):
        p.eat(TokenKind.OP, text="->")
        ret = _parse_type_name(p)
        p.eat_gt()
        return f"lambda<-> {ret}>"

    params = [_parse_type_name(p)]
    while p.at(TokenKind.COMMA):
        p.eat(TokenKind.COMMA)
        params.append(_parse_type_name(p))

    if p.at(TokenKind.OP, text="->"):
        p.eat(TokenKind.OP, text="->")
        ret = _parse_type_name(p)
        p.eat_gt()
        return f"lambda<{', '.join(params)} -> {ret}>"

    if len(params) == 1 and p.at_gt():
        p.eat_gt()
        return f"lambda<{params[0]}>"

    raise FatalParseError(
        "Lambda types separate parameters from the return type with `->`.",
        base_tok.line,
        base_tok.column,
        code="pys.lambda-type-arrow",
        tips=[
            "Write `lambda<int -> bool>` or `lambda<int, int -> int>`.",
            "Zero parameters: sugar `lambda<int>` or explicit `lambda<-> int>`.",
        ],
    )


def _at_generic_typed_decl(p: _Tok) -> bool:
    """Type `<` … `>` name `=` — generic typed declaration."""
    if not (p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD)):
        return False
    if p.cur().text in {
        "if", "unless", "loop", "print", "return", "pass", "break", "continue", "else",
        "function", "class", "interface", "import", "shared", "tasks", "task",
        "const", "fix", "var",
    }:
        return False
    if p.peek(1).kind != TokenKind.LT:
        return False
    depth = 0
    k = 1
    while True:
        t = p.peek(k)
        if t.kind == TokenKind.EOF:
            return False
        if t.kind == TokenKind.LT:
            depth += 1
        else:
            closes = _gt_close_count(t)
            if closes:
                depth -= closes
                if depth == 0:
                    return (
                        p.peek(k + 1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
                        and p.peek(k + 2).kind == TokenKind.OP
                        and p.peek(k + 2).text == "="
                    )
                if depth < 0:
                    return False
        k += 1


def _parse_function(p: _Tok, visibility: str = "") -> FunctionDef:
    sp = p.span()
    p.eat_kw("function")
    rtype = ""
    if _looks_like_typed_name(p):
        rtype = _parse_type_name(p)
    name_tok = p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
    name = name_tok.text
    p.eat(TokenKind.LPAREN)
    params: list[tuple[str, str]] = []
    if not p.at(TokenKind.RPAREN):
        params.append(_parse_param(p))
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            params.append(_parse_param(p))
    p.eat(TokenKind.RPAREN)
    body = _parse_block(p)
    return FunctionDef(
        span=p.close_span(sp),
        name=name,
        params=[n for _, n in params],
        param_types=[t for t, _ in params],
        body=body,
        visibility=visibility,
        return_type=rtype,
        name_span=p.token_span(name_tok),
    )


def _parse_param(p: _Tok) -> tuple[str, str]:
    """Return (type_or_empty, name)."""
    type_name = ""
    t0 = p.cur()
    t1 = p.peek(1)
    if t0.kind in {TokenKind.IDENT, TokenKind.KEYWORD} and t0.text not in {",", ")"}:
        if t1.kind == TokenKind.LT:
            type_name = _parse_type_name(p)
        elif t1.kind == TokenKind.LBRACK:
            type_name = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
            p.eat(TokenKind.LBRACK)
            p.eat(TokenKind.RBRACK)
            type_name += "[]"
        elif (
            t1.kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and t1.text not in {",", ")"}
            and p.peek(2).kind in {TokenKind.COMMA, TokenKind.RPAREN}
        ):
            # TYPE name ,/)  — typed param
            type_name = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
        elif t0.text in _TYPES and t1.kind in {TokenKind.IDENT, TokenKind.KEYWORD}:
            type_name = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    return type_name, name


def _parse_interface(p: _Tok, visibility: str = "") -> InterfaceDef:
    sp = p.span()
    p.eat_kw("interface")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.LBRACE)
    methods: list[str] = []
    method_arities: dict[str, int] = {}
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        if p.at_kw("public", "private", "protected", "module"):
            mod = p.cur().text
            raise FatalParseError(
                f"Interface methods are always public and abstract — "
                f"omit `{mod}` on the method signature.",
                p.cur().line,
                p.cur().column,
                code="pys.interface-access",
                tips=[
                    "Write `name(...)` or `int name(...)` inside the interface "
                    "(no access modifier)."
                ],
            )
        if p.cur().text in _TYPES and p.peek(1).kind != TokenKind.LPAREN:
            p.eat(TokenKind.KEYWORD, TokenKind.IDENT)
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat(TokenKind.LPAREN)
        arity = 0
        if not p.at(TokenKind.RPAREN):
            _parse_param(p)
            arity = 1
            while p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                _parse_param(p)
                arity += 1
        p.eat(TokenKind.RPAREN)
        if p.at(TokenKind.LBRACE):
            raise FatalParseError(
                f"Interface method '{mname}' is abstract and cannot have a body.",
                p.cur().line,
                p.cur().column,
            )
        methods.append(mname)
        method_arities[mname] = arity
    p.eat(TokenKind.RBRACE)
    return InterfaceDef(
        span=sp, name=name, methods=methods, method_arities=method_arities, visibility=visibility
    )


def _parse_struct(
    p: _Tok, visibility: str = "", *, type_fix: bool = False
) -> StructDef:
    """Parse ``[fix] struct Name [<T,U>] { fields }`` (no inherits/methods)."""
    sp = p.span()
    if type_fix:
        p.eat_kw("fix")
    p.eat_kw("struct")
    if p.at_kw("sealed", "inherits", "super", "implements"):
        bad = p.cur().text
        raise FatalParseError(
            f"Structs cannot use `{bad}` — they are identity-free value types "
            f"without inheritance or interfaces.",
            p.cur().line,
            p.cur().column,
        )
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    type_params: list[str] = []
    if p.at(TokenKind.LT):
        p.eat(TokenKind.LT)
        type_params.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            type_params.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        p.eat_gt()
    if p.at_kw("sealed", "inherits", "super", "implements"):
        bad = p.cur().text
        raise FatalParseError(
            f"Structs cannot use `{bad}` — they are identity-free value types "
            f"without inheritance or interfaces.",
            p.cur().line,
            p.cur().column,
        )
    p.eat(TokenKind.LBRACE)
    fields: list[StructField] = []
    phase = [_PHASE_STRUCT_FIX]
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        field_sp = p.span()
        # Fields are always public; type visibility is on the struct_decl.
        if p.at_kw("public", "private", "protected", "module"):
            raise FatalParseError(
                "Struct fields are always public — omit field access modifiers. "
                "Use `global` / `package` / `module` on the struct declaration "
                "to control who can import the type.",
                p.cur().line,
                p.cur().column,
            )
        if p.at_kw("function", "func", "class", "interface", "struct", "enum", "tasks"):
            bad = p.cur().text
            raise FatalParseError(
                f"Structs cannot contain `{bad}` — only fields are allowed "
                f"(identity-free value types have no methods or nested types).",
                p.cur().line,
                p.cur().column,
            )
        is_fix = False
        if p.at_kw("fix"):
            is_fix = True
            p.eat_kw("fix")
        type_name = _parse_type_name(p)
        fname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if is_fix:
            _require_member_phase(
                p,
                phase,
                _PHASE_STRUCT_FIX,
                message=_MSG_FIX_AFTER_MUTABLE.format(name=fname),
                code="pys.order-fix-after-mutable",
            )
        else:
            _require_member_phase(
                p,
                phase,
                _PHASE_STRUCT_FIELD,
                message=_MSG_FIX_AFTER_MUTABLE.format(name=fname),
                code="pys.order-fix-after-mutable",
            )
        default = None
        if p.at(TokenKind.OP, text="="):
            p.eat(TokenKind.OP, text="=")
            default = _parse_expression(p)
        fields.append(
            StructField(
                span=field_sp,
                access="public",
                type_name=type_name,
                name=fname,
                is_fix=is_fix,
                default=default,
            )
        )
    p.eat(TokenKind.RBRACE)
    return StructDef(
        span=sp,
        name=name,
        fields=fields,
        visibility=visibility,
        type_params=type_params,
        type_fix=type_fix,
    )


def _parse_data(p: _Tok, visibility: str = "") -> DataDef:
    """Parse ``[top_visibility] data Name { fields }`` (immutable value object)."""
    sp = p.span()
    p.eat_kw("data")
    if p.at_kw("inherits", "super", "uses", "implements", "sealed", "identity"):
        bad = p.cur().text
        raise FatalParseError(
            f"`data` types cannot use `{bad}` — they are immutable value objects "
            f"with fields only (no inheritance, traits, or identity).",
            p.cur().line,
            p.cur().column,
        )
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    if p.at_kw("inherits", "super", "uses", "implements", "sealed", "identity"):
        bad = p.cur().text
        raise FatalParseError(
            f"`data` types cannot use `{bad}` — they are immutable value objects "
            f"with fields only (no inheritance, traits, or identity).",
            p.cur().line,
            p.cur().column,
        )
    p.eat(TokenKind.LBRACE)
    fields: list[StructField] = []
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        field_sp = p.span()
        if p.at_kw("public", "private", "protected", "module"):
            raise FatalParseError(
                "`data` fields are always public and implicitly `fix` — "
                "omit field access modifiers.",
                p.cur().line,
                p.cur().column,
            )
        if p.at_kw("fix"):
            raise FatalParseError(
                "`data` fields are implicitly `fix` — omit the `fix` keyword.",
                p.cur().line,
                p.cur().column,
            )
        if p.at_kw("function", "func", "class", "interface", "struct", "enum", "tasks"):
            bad = p.cur().text
            raise FatalParseError(
                f"`data` types cannot contain `{bad}` — only fields are allowed.",
                p.cur().line,
                p.cur().column,
            )
        type_name = _parse_type_name(p)
        fname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        default = None
        if p.at(TokenKind.OP, text="="):
            p.eat(TokenKind.OP, text="=")
            default = _parse_expression(p)
        fields.append(
            StructField(
                span=field_sp,
                access="public",
                type_name=type_name,
                name=fname,
                is_fix=True,
                default=default,
            )
        )
    p.eat(TokenKind.RBRACE)
    return DataDef(span=sp, name=name, fields=fields, visibility=visibility)


def _parse_entity(p: _Tok, visibility: str = "") -> EntityDef:
    """Parse ``entity Name [inherits P] [identity(...)] { members }``."""
    sp = p.span()
    p.eat_kw("entity")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    parent = ""
    if p.at_kw("inherits", "super"):
        p.eat(TokenKind.KEYWORD)
        parent = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    if p.at_kw("uses"):
        raise FatalParseError(
            "`entity` cannot use `uses` — traits are not allowed on entities "
            "(keep pure identity-keyed data + methods).",
            p.cur().line,
            p.cur().column,
        )
    if p.at_kw("implements"):
        raise FatalParseError(
            "`entity` cannot use `implements` — use `class` when you need interfaces.",
            p.cur().line,
            p.cur().column,
        )
    identity: list[str] = []
    if p.at_kw("identity"):
        p.eat_kw("identity")
        p.eat(TokenKind.LPAREN)
        identity.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            identity.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        p.eat(TokenKind.RPAREN)
    if p.at_kw("uses"):
        raise FatalParseError(
            "`entity` cannot use `uses` — traits are not allowed on entities.",
            p.cur().line,
            p.cur().column,
        )
    if p.at_kw("implements"):
        raise FatalParseError(
            "`entity` cannot use `implements`.",
            p.cur().line,
            p.cur().column,
        )
    p.eat(TokenKind.LBRACE)
    fields: list[FieldDecl] = []
    methods: list[MethodDef] = []
    identity_set = set(identity)
    phase = [_PHASE_ENTITY_IDENTITY]
    pending_identity = set(identity)
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        access = ""
        member_sp = p.span()
        if p.at_kw("public", "private", "protected", "module"):
            access = p.eat(TokenKind.KEYWORD).text
        if p.at_kw("function"):
            raise FatalParseError(
                "Entity methods must not use `function`. Use an access modifier: "
                "`public name(args)`.",
                p.cur().line,
                p.cur().column,
            )
        # constructor
        if p.cur().text == name and p.peek(1).kind == TokenKind.LPAREN:
            if not access:
                raise FatalParseError(
                    "Entity members require an access modifier "
                    f"(e.g. `public {name}(...)`).",
                    p.cur().line,
                    p.cur().column,
                )
            p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
            _require_member_phase(
                p,
                phase,
                _PHASE_ENTITY_CTOR,
                message=_MSG_METHOD_BEFORE_FIELDS.format(name=name),
                code="pys.order-entity-ctor",
            )
            p.eat(TokenKind.LPAREN)
            params: list[tuple[str, str]] = []
            if not p.at(TokenKind.RPAREN):
                params.append(_parse_param(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    params.append(_parse_param(p))
            p.eat(TokenKind.RPAREN)
            body = _parse_block(p)
            methods.append(
                MethodDef(
                    span=member_sp,
                    access=access,
                    name="__init__",
                    params=[n for _, n in params],
                    param_types=[t for t, _ in params],
                    body=body,
                    is_constructor=True,
                )
            )
            continue
        is_fix = False
        if p.at_kw("fix"):
            is_fix = True
            p.eat_kw("fix")
        type_name = ""
        if p.cur().text in _TYPES or p.at_kw("void") or (
            p.cur().kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and (
                p.peek(1).kind == TokenKind.LBRACK
                or p.peek(1).kind == TokenKind.LT
                or (
                    p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
                    and p.peek(1).kind != TokenKind.LPAREN
                    and p.peek(1).text != name
                )
            )
        ):
            if p.peek(1).kind == TokenKind.LPAREN:
                pass
            else:
                type_name = _parse_type_name(p)
                if p.at(TokenKind.LBRACK):
                    p.eat(TokenKind.LBRACK)
                    p.eat(TokenKind.RBRACK)
                    type_name += "[]"
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if p.at(TokenKind.LPAREN):
            if not access:
                raise FatalParseError(
                    "Entity methods require an access modifier "
                    f"(e.g. `public {mname}(...)`).",
                    member_sp.line,
                    member_sp.column,
                )
            if is_fix:
                raise FatalParseError(
                    "`fix` applies to fields, not methods.",
                    member_sp.line,
                    member_sp.column,
                )
            _require_member_phase(
                p,
                phase,
                _PHASE_ENTITY_METHOD,
                message=_MSG_METHOD_BEFORE_FIELDS.format(name=mname),
                code="pys.order-entity-method",
            )
            p.eat(TokenKind.LPAREN)
            params = []
            if not p.at(TokenKind.RPAREN):
                params.append(_parse_param(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    params.append(_parse_param(p))
            p.eat(TokenKind.RPAREN)
            body = _parse_block(p)
            methods.append(
                MethodDef(
                    span=member_sp,
                    access=access,
                    name=mname,
                    params=[n for _, n in params],
                    param_types=[t for t, _ in params],
                    body=body,
                    return_type=type_name,
                )
            )
        else:
            if not access:
                raise FatalParseError(
                    "Entity fields require an access modifier "
                    f"(e.g. `private fix int {mname}`).",
                    member_sp.line,
                    member_sp.column,
                )
            if not type_name:
                raise FatalParseError(
                    f"Entity field '{mname}' requires a type.",
                    member_sp.line,
                    member_sp.column,
                )
            is_identity = mname in identity_set
            if is_identity:
                _require_member_phase(
                    p,
                    phase,
                    _PHASE_ENTITY_IDENTITY,
                    message=_MSG_ENTITY_BEFORE_IDENTITY.format(
                        name=mname,
                        identity=next(iter(pending_identity), mname),
                    ),
                    code="pys.order-entity-identity",
                )
                pending_identity.discard(mname)
            elif is_fix:
                # Non-identity fix after identity section (or when no identity keys left).
                if pending_identity and phase[0] <= _PHASE_ENTITY_IDENTITY:
                    raise FatalParseError(
                        _MSG_ENTITY_BEFORE_IDENTITY.format(
                            name=mname,
                            identity=next(iter(pending_identity)),
                        ),
                        p.cur().line,
                        p.cur().column,
                        code="pys.order-entity-identity",
                        tips=[
                            "Declare every identity(...) field first, then other fix fields."
                        ],
                    )
                _require_member_phase(
                    p,
                    phase,
                    _PHASE_ENTITY_FIX,
                    message=_MSG_FIELD_AFTER_CTOR.format(name=mname),
                    code="pys.order-entity-fix",
                )
            else:
                if pending_identity and phase[0] <= _PHASE_ENTITY_IDENTITY:
                    raise FatalParseError(
                        _MSG_ENTITY_BEFORE_IDENTITY.format(
                            name=mname,
                            identity=next(iter(pending_identity)),
                        ),
                        p.cur().line,
                        p.cur().column,
                        code="pys.order-entity-identity",
                        tips=[
                            "Declare every identity(...) field first, then other fields."
                        ],
                    )
                _require_member_phase(
                    p,
                    phase,
                    _PHASE_ENTITY_FIELD,
                    message=_MSG_FIELD_AFTER_CTOR.format(name=mname),
                    code="pys.order-entity-field",
                )
            default = None
            if p.at(TokenKind.OP, text="="):
                p.eat(TokenKind.OP, text="=")
                default = _parse_expression(p)
            fields.append(
                FieldDecl(
                    span=member_sp,
                    access=access,
                    type_name=type_name,
                    name=mname,
                    is_fix=is_fix,
                    default=default,
                )
            )
    p.eat(TokenKind.RBRACE)
    return EntityDef(
        span=sp,
        name=name,
        parent=parent,
        identity=identity,
        fields=fields,
        methods=methods,
        visibility=visibility,
    )


def _parse_enum(p: _Tok, visibility: str = "") -> EnumDef:
    """Parse ``[top_visibility] enum Name { MEMBER , … [,] }`` (comma-delimited)."""
    sp = p.span()
    p.eat_kw("enum")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.LBRACE)
    members: list[EnumMember] = []
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        mem_sp = p.span()
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        value: Expr | None = None
        if p.at(TokenKind.OP, text="="):
            p.eat(TokenKind.OP, text="=")
            lit = p.cur()
            if lit.kind == TokenKind.INT:
                p.eat(TokenKind.INT)
                value = Literal(span=Span(lit.line, lit.column), kind="int", text=lit.text)
            elif lit.kind == TokenKind.STRING:
                p.eat(TokenKind.STRING)
                value = Literal(span=Span(lit.line, lit.column), kind="string", text=lit.text)
            else:
                raise FatalParseError(
                    "Enum member value must be an integer or string literal.",
                    lit.line,
                    lit.column,
                )
        members.append(EnumMember(span=mem_sp, name=mname, value=value))
        while p.at(TokenKind.BLANK) or p.at(TokenKind.COMMENT):
            p.eat(p.cur().kind)
        if p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            continue
        if p.at(TokenKind.RBRACE):
            break
        raise FatalParseError(
            "Enum members must be separated by ','.",
            p.cur().line,
            p.cur().column,
            code="pys.enum-member-comma",
            tips=[
                "Write `enum Name { A, B, C }` (optional trailing comma allowed).",
                "Juxtaposed members without commas are no longer valid.",
            ],
        )
    p.eat(TokenKind.RBRACE)
    if not members:
        raise FatalParseError(
            f"Enum '{name}' cannot be empty — declare at least one member.",
            sp.line,
            sp.column,
        )
    return EnumDef(span=sp, name=name, members=members, visibility=visibility)


def _parse_trait_use(p: _Tok) -> TraitUse:
    """Parse ``TraitName`` or ``TraitName(req: host, …)`` in a ``uses`` clause."""
    sp = p.span()
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    remaps: list[tuple[str, str]] = []
    if p.at(TokenKind.LPAREN):
        p.eat(TokenKind.LPAREN)
        if p.at(TokenKind.RPAREN):
            raise FatalParseError(
                f"Empty remapping list on `uses {name}()` — omit the parentheses "
                f"or write `uses {name}(requirement: hostMember)`.",
                p.cur().line,
                p.cur().column,
                code="pys.trait-remap",
                tips=[
                    f"Write `uses {name}` with no parentheses when names match, "
                    f"or map each requirement: `uses {name}(reqName: hostName)`.",
                ],
            )
        while True:
            left = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            if not p.at(TokenKind.COLON):
                raise FatalParseError(
                    "Trait remapping entries use `requirement: hostMember` "
                    f"(found `{left}` without `:`).",
                    p.cur().line,
                    p.cur().column,
                    code="pys.trait-remap",
                    tips=[f"Write `{left}: hostFieldOrMethod`."],
                )
            p.eat(TokenKind.COLON)
            right = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            remaps.append((left, right))
            if p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                if p.at(TokenKind.RPAREN):
                    break
                continue
            break
        p.eat(TokenKind.RPAREN)
    return TraitUse(span=sp, name=name, remaps=remaps)


def _parse_class(p: _Tok, visibility: str = "") -> ClassDef:
    sp = p.span()
    sealed = False
    abstract = False
    if p.at_kw("sealed"):
        sealed = True
        p.eat_kw("sealed")
        if p.at_kw("abstract"):
            raise FatalParseError(
                "`sealed` and `abstract` are mutually exclusive on the same class.",
                p.cur().line,
                p.cur().column,
            )
    elif p.at_kw("abstract"):
        abstract = True
        p.eat_kw("abstract")
        if p.at_kw("sealed"):
            raise FatalParseError(
                "`sealed` and `abstract` are mutually exclusive on the same class.",
                p.cur().line,
                p.cur().column,
            )
    p.eat_kw("class")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    if p.at(TokenKind.LT):
        # Generic class params are accepted and discarded for Python emit.
        p.eat(TokenKind.LT)
        p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
        p.eat_gt()
    bases: list[str] = []
    parent = ""
    uses: list[TraitUse] = []
    if p.at_kw("inherits", "super"):
        p.eat(TokenKind.KEYWORD)
        parent = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        bases.append(parent)
    if p.at_kw("uses"):
        p.eat_kw("uses")
        uses.append(_parse_trait_use(p))
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            uses.append(_parse_trait_use(p))
    if p.at_kw("implements"):
        p.eat_kw("implements")
        bases.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            bases.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
    p.eat(TokenKind.LBRACE)
    fields: list[FieldDecl] = []
    methods: list[MethodDef] = []
    phase = [_PHASE_CLASS_CONST]
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        access = ""
        member_sp = p.span()
        if p.at_kw("public", "private", "protected", "module"):
            access = p.eat(TokenKind.KEYWORD).text
            member_sp = Span(member_sp.line, member_sp.column)
        if p.at_kw("function"):
            raise FatalParseError(
                "Class methods must not use `function`. Use an access modifier: `public name(args)`.",
                p.cur().line,
                p.cur().column,
            )
        if p.at_kw("method") or (p.at(TokenKind.IDENT) and p.cur().text == "method"):
            raise FatalParseError(
                "Remove `method`; use an access modifier and optional return type: "
                "`public name(args)` or `public string name(args)`.",
                p.cur().line,
                p.cur().column,
            )
        # const field: access const primitive name = expr
        if p.at_kw("const"):
            if not access:
                raise FatalParseError(
                    "Class fields require an access modifier "
                    "(e.g. `public const int MAX = 10`).",
                    p.cur().line,
                    p.cur().column,
                )
            p.eat_kw("const")
            type_name = _parse_type_name(p)
            fname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            _require_member_phase(
                p,
                phase,
                _PHASE_CLASS_CONST,
                message=_MSG_CONST_AFTER_FIELDS.format(name=fname),
                code="pys.order-const-field",
            )
            p.eat(TokenKind.OP, text="=")
            default = _parse_expression(p)
            fields.append(
                FieldDecl(
                    span=member_sp,
                    access=access,
                    type_name=type_name,
                    name=fname,
                    is_const=True,
                    default=default,
                )
            )
            continue
        # fix field: access fix type name [= expr]
        if p.at_kw("fix"):
            if not access:
                raise FatalParseError(
                    "Class fields require an access modifier "
                    "(e.g. `private fix int id`).",
                    p.cur().line,
                    p.cur().column,
                )
            p.eat_kw("fix")
            type_name = _parse_type_name(p)
            if p.at(TokenKind.LBRACK):
                p.eat(TokenKind.LBRACK)
                p.eat(TokenKind.RBRACK)
                type_name += "[]"
            fname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            _require_member_phase(
                p,
                phase,
                _PHASE_CLASS_FIX,
                message=(
                    _MSG_FIX_AFTER_MUTABLE.format(name=fname)
                    if phase[0] == _PHASE_CLASS_FIELD
                    else _MSG_FIELD_AFTER_CTOR.format(name=fname)
                ),
                code="pys.order-fix-field",
            )
            default = None
            if p.at(TokenKind.OP, text="="):
                p.eat(TokenKind.OP, text="=")
                default = _parse_expression(p)
            fields.append(
                FieldDecl(
                    span=member_sp,
                    access=access,
                    type_name=type_name,
                    name=fname,
                    is_fix=True,
                    default=default,
                )
            )
            continue
        # Abstract method: access abstract ReturnType name(params) — no body.
        if p.at_kw("abstract"):
            p.eat_kw("abstract")
            if not access:
                raise FatalParseError(
                    "Abstract methods require an access modifier "
                    "(e.g. `public abstract string get(int index)`).",
                    p.cur().line,
                    p.cur().column,
                )
            ret = _parse_type_name(p)
            if p.at(TokenKind.LBRACK):
                p.eat(TokenKind.LBRACK)
                p.eat(TokenKind.RBRACK)
                ret += "[]"
            mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            _require_member_phase(
                p,
                phase,
                _PHASE_CLASS_METHOD,
                message=_MSG_METHOD_BEFORE_FIELDS.format(name=mname),
                code="pys.order-method",
            )
            p.eat(TokenKind.LPAREN)
            params: list[tuple[str, str]] = []
            if not p.at(TokenKind.RPAREN):
                params.append(_parse_param(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    params.append(_parse_param(p))
            p.eat(TokenKind.RPAREN)
            if p.at(TokenKind.LBRACE):
                raise FatalParseError(
                    f"Abstract method '{mname}' cannot have a body.",
                    p.cur().line,
                    p.cur().column,
                )
            methods.append(
                MethodDef(
                    span=member_sp,
                    access=access,
                    name=mname,
                    params=[n for _, n in params],
                    param_types=[t for t, _ in params],
                    body=None,
                    is_abstract=True,
                    return_type=ret,
                )
            )
            continue
        # constructor
        if p.cur().text == name and p.peek(1).kind == TokenKind.LPAREN:
            p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
            _require_member_phase(
                p,
                phase,
                _PHASE_CLASS_CTOR,
                message=_MSG_METHOD_BEFORE_FIELDS.format(name=name),
                code="pys.order-ctor",
            )
            p.eat(TokenKind.LPAREN)
            params = []
            if not p.at(TokenKind.RPAREN):
                params.append(_parse_param(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    params.append(_parse_param(p))
            p.eat(TokenKind.RPAREN)
            body = _parse_block(p)
            methods.append(
                MethodDef(
                    span=member_sp,
                    access=access,
                    name="__init__",
                    params=[n for _, n in params],
                    param_types=[t for t, _ in params],
                    body=body,
                    is_constructor=True,
                )
            )
            continue
        type_name = ""
        if p.cur().text in _TYPES or p.at_kw("void") or (
            p.cur().kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and (
                p.peek(1).kind == TokenKind.LBRACK
                or p.peek(1).kind == TokenKind.LT
                or (
                    p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
                    and p.peek(1).kind != TokenKind.LPAREN
                    and p.peek(1).text != name
                )
            )
        ):
            # method: [type] name (   OR field: type name / type[] name / type<...> name
            if p.peek(1).kind == TokenKind.LPAREN:
                pass  # name is current
            else:
                type_name = _parse_type_name(p)
                if p.at(TokenKind.LBRACK):
                    p.eat(TokenKind.LBRACK)
                    p.eat(TokenKind.RBRACK)
                    type_name += "[]"
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if p.at(TokenKind.LPAREN):
            _require_member_phase(
                p,
                phase,
                _PHASE_CLASS_METHOD,
                message=_MSG_METHOD_BEFORE_FIELDS.format(name=mname),
                code="pys.order-method",
            )
            p.eat(TokenKind.LPAREN)
            params = []
            if not p.at(TokenKind.RPAREN):
                params.append(_parse_param(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    params.append(_parse_param(p))
            p.eat(TokenKind.RPAREN)
            body = _parse_block(p)
            methods.append(
                MethodDef(
                    span=member_sp,
                    access=access,
                    name=mname,
                    params=[n for _, n in params],
                    param_types=[t for t, _ in params],
                    body=body,
                    return_type=type_name,
                )
            )
        else:
            _require_member_phase(
                p,
                phase,
                _PHASE_CLASS_FIELD,
                message=_MSG_FIELD_AFTER_CTOR.format(name=mname),
                code="pys.order-field-after-ctor",
            )
            default = None
            if p.at(TokenKind.OP, text="="):
                p.eat(TokenKind.OP, text="=")
                default = _parse_expression(p)
            fields.append(
                FieldDecl(
                    span=member_sp,
                    access=access,
                    type_name=type_name,
                    name=mname,
                    default=default,
                )
            )
    p.eat(TokenKind.RBRACE)
    return ClassDef(
        span=sp,
        name=name,
        bases=bases,
        parent=parent,
        uses=uses,
        fields=fields,
        methods=methods,
        visibility=visibility,
        sealed=sealed,
        abstract=abstract,
    )


def _parse_trait(p: _Tok, visibility: str = "") -> TraitDef:
    """Parse ``trait Name { requires … | method bodies }`` (always-public members)."""
    sp = p.span()
    p.eat_kw("trait")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.LBRACE)
    requires: list[TraitRequire] = []
    methods: list[MethodDef] = []
    phase = [_PHASE_TRAIT_REQUIRES]
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        member_sp = p.span()
        if p.at_kw("public", "private", "protected", "module"):
            raise FatalParseError(
                "Trait members are always public — omit access modifiers.",
                p.cur().line,
                p.cur().column,
            )
        if p.at_kw("requires"):
            p.eat_kw("requires")
            req_type = _parse_type_name(p)
            req_name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            _require_member_phase(
                p,
                phase,
                _PHASE_TRAIT_REQUIRES,
                message=_MSG_TRAIT_METHOD_BEFORE_REQUIRES.format(
                    name=req_name, trait=name
                ),
                code="pys.order-trait-requires",
            )
            if p.at(TokenKind.LPAREN):
                p.eat(TokenKind.LPAREN)
                params: list[tuple[str, str]] = []
                if not p.at(TokenKind.RPAREN):
                    params.append(_parse_param(p))
                    while p.at(TokenKind.COMMA):
                        p.eat(TokenKind.COMMA)
                        params.append(_parse_param(p))
                p.eat(TokenKind.RPAREN)
                if p.at(TokenKind.LBRACE):
                    raise FatalParseError(
                        f"Trait `requires` method '{req_name}' cannot have a body "
                        f"— the host class must supply it.",
                        p.cur().line,
                        p.cur().column,
                    )
                requires.append(
                    TraitRequire(
                        span=member_sp,
                        kind="method",
                        type_name=req_type,
                        name=req_name,
                        params=[n for _, n in params],
                        param_types=[t for t, _ in params],
                    )
                )
            else:
                requires.append(
                    TraitRequire(
                        span=member_sp,
                        kind="field",
                        type_name=req_type,
                        name=req_name,
                    )
                )
            continue
        # Trait method: [return_type] name ( params ) block
        type_name = ""
        if p.cur().text in _TYPES or (
            p.cur().kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and p.peek(1).kind != TokenKind.LPAREN
        ):
            if p.peek(1).kind != TokenKind.LPAREN:
                type_name = _parse_type_name(p)
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if not p.at(TokenKind.LPAREN):
            raise FatalParseError(
                "Traits cannot declare fields — use `requires Type name` for host state, "
                "or a method with a body.",
                p.cur().line,
                p.cur().column,
            )
        _require_member_phase(
            p,
            phase,
            _PHASE_TRAIT_METHOD,
            message=_MSG_TRAIT_METHOD_BEFORE_REQUIRES.format(name=mname, trait=name),
            code="pys.order-trait-requires",
        )
        p.eat(TokenKind.LPAREN)
        params = []
        if not p.at(TokenKind.RPAREN):
            params.append(_parse_param(p))
            while p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                params.append(_parse_param(p))
        p.eat(TokenKind.RPAREN)
        if not p.at(TokenKind.LBRACE):
            raise FatalParseError(
                f"Trait method '{mname}' must have a body "
                f"(use `requires` for host-supplied methods).",
                p.cur().line,
                p.cur().column,
            )
        body = _parse_block(p)
        methods.append(
            MethodDef(
                span=member_sp,
                access="public",
                name=mname,
                params=[n for _, n in params],
                param_types=[t for t, _ in params],
                body=body,
                return_type=type_name,
            )
        )
    p.eat(TokenKind.RBRACE)
    if not requires and not methods:
        raise FatalParseError(
            f"Trait '{name}' cannot be empty — add `requires` and/or methods.",
            sp.line,
            sp.column,
        )
    return TraitDef(
        span=sp,
        name=name,
        requires=requires,
        methods=methods,
        visibility=visibility,
    )


_ARRAY_ELEM_TYPES = frozenset(
    {
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
    }
)


def _parse_array_dims(p: _Tok) -> list[int | None]:
    """Parse one or more ``[]`` / ``[n]`` dimension suffixes."""
    dims: list[int | None] = []
    while p.at(TokenKind.LBRACK):
        p.eat(TokenKind.LBRACK)
        size: int | None = None
        if p.at(TokenKind.INT):
            size = int(p.eat(TokenKind.INT).text)
        p.eat(TokenKind.RBRACK)
        dims.append(size)
    return dims


def _parse_array_alloc(p: _Tok) -> ArrayAlloc:
    sp = p.span()
    elem = p.eat(TokenKind.KEYWORD).text
    dims = _parse_array_dims(p)
    if not dims:
        raise ParseError("Array allocation requires at least one [] dimension", sp.line, sp.column)
    return ArrayAlloc(span=sp, elem_type=elem, dims=dims)


def _parse_decl(p: _Tok, visibility: str = "") -> AssignStmt | ArrayDecl:
    sp = p.span()
    is_const = is_fix = False
    if p.at_kw("const"):
        is_const = True
        p.eat_kw("const")
    elif p.at_kw("fix"):
        is_fix = True
        p.eat_kw("fix")
    dtype: str | None = None
    if p.at_kw("var"):
        p.eat_kw("var")
        dtype = "var"
    elif p.at_kw(*_TYPES) and p.peek(1).kind == TokenKind.LBRACK:
        dtype = p.eat(TokenKind.KEYWORD).text
        dims = _parse_array_dims(p)
        if any(d is not None for d in dims):
            # Sizes belong on allocation expressions (`int[3][]`, `int[2][3]`),
            # not on the declared type — length comes from the initializer.
            sized = "".join("[]" if d is None else f"[{d}]" for d in dims)
            unsized = "[]" * len(dims)
            raise FatalParseError(
                f"Sized array type `{dtype}{sized}` is not valid on a declaration. "
                f"Write `{dtype}{unsized} name = …` and let the initializer set the length "
                f"(use `{dtype}[n]…` only on the right-hand side to allocate).",
                p.cur().line,
                p.cur().column,
            )
        name_tok = p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
        name = name_tok.text
        p.eat(TokenKind.OP, text="=")
        value = _parse_expression(p)
        return ArrayDecl(
            span=sp,
            elem_type=dtype,
            name=name,
            size=None,
            dims=dims,
            value=value,
            name_span=p.token_span(name_tok),
        )
    elif p.at_kw(*_TYPES):
        dtype = p.eat(TokenKind.KEYWORD).text
    elif (p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD)) and (
        (p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD} and p.peek(2).text == "=")
        or _at_generic_typed_decl(p)
    ):
        dtype = _parse_type_name(p)
    name_tok = p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
    name = name_tok.text
    p.eat(TokenKind.OP, text="=")
    value = _parse_expression(p)
    return AssignStmt(
        span=sp,
        name=name,
        value=value,
        declare_type=dtype,
        is_const=is_const,
        is_fix=is_fix,
        visibility=visibility,
        name_span=p.token_span(name_tok),
    )


@_packrat("statement")
def _parse_statement(p: _Tok):
    sp = p.span()
    if p.at(TokenKind.BLANK):
        t = p.eat(TokenKind.BLANK)
        return BlankStmt(span=Span(t.line, t.column))
    if p.at(TokenKind.COMMENT):
        t = p.eat(TokenKind.COMMENT)
        return CommentStmt(span=Span(t.line, t.column), text=t.text)
    # SA-8: `new Type(...)` is not part of PYS; constructors are `Type(...)`.
    if (p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD)) and p.cur().text == "new":
        raise FatalParseError(
            "Unexpected `new`. Construct values with `TypeName(...)` "
            "(structs and classes have no `new` keyword).",
            p.cur().line,
            p.cur().column,
        )
    if p.at_kw("print"):
        return _parse_print(p)
    if p.at_kw("return"):
        p.eat_kw("return")
        if p.done() or p.at(TokenKind.RBRACE):
            return ReturnStmt(span=sp, value=None)
        if p.at_kw(
            "if", "unless", "loop", "print", "return", "pass", "break", "continue",
            "var", "const", "fix", *_TYPES, *_VIS, "function", "class", "else",
        ):
            return ReturnStmt(span=sp, value=None)
        return ReturnStmt(span=sp, value=_parse_expression(p))
    if p.at_kw("pass"):
        p.eat_kw("pass")
        return PassStmt(span=sp)
    if p.at_kw("break"):
        p.eat_kw("break")
        return BreakStmt(span=sp)
    if p.at_kw("continue"):
        p.eat_kw("continue")
        return ContinueStmt(span=sp)
    if p.at_kw("if"):
        return _parse_if(p)
    if p.at_kw("unless"):
        return _parse_unless(p)
    if p.at_kw("switch"):
        return _parse_switch_stmt(p)
    if p.at_kw("loop"):
        return _parse_loop(p)
    if p.at_kw("tasks"):
        return _parse_tasks(p)
    if p.at_kw("task"):
        raise ParseError(
            "`task` must appear inside a `tasks` block.",
            p.cur().line,
            p.cur().column,
        )
    if p.at_kw("shared"):
        return _parse_shared(p)
    if p.at_kw("atomic"):
        return _parse_atomic(p)
    if p.at_kw("var", "const", "fix", *_TYPES):
        return _parse_decl(p)
    # Typed named decl: Type name =  / Type<...> name =
    if (
        (p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD))
        and p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
        and p.peek(2).text == "="
        and not p.at_kw(
            "if", "unless", "loop", "print", "return", "pass", "break", "continue", "else",
            "function", "class", "struct", "enum", "interface", "import", "shared", "tasks", "task",
            "switch", "case", "default",
        )
    ) or _at_generic_typed_decl(p):
        return _parse_decl(p)
    # this.name = expr / name.member = expr
    if (p.at_kw("this") or p.at(TokenKind.IDENT)) and p.peek(1).kind == TokenKind.DOT:
        left = _parse_expression(p)
        if p.at(TokenKind.OP, text="="):
            p.eat(TokenKind.OP, text="=")
            right = _parse_expression(p)
            return AssignStmt(span=sp, name=_expr_to_lvalue(left), value=right)
        return ExprStmt(span=sp, expr=left)
    # name = / += / ++
    if p.at(TokenKind.IDENT) or (p.at(TokenKind.KEYWORD) and p.cur().text not in {
        "if", "unless", "loop", "print", "return", "pass", "break", "continue", "else",
        "function", "class", "interface", "import",
    }):
        if p.peek(1).text in {"=", "+=", "-=", "*=", "/=", "%=", "++", "--"}:
            name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            op = p.eat(TokenKind.OP).text
            if op in {"++", "--"}:
                return AugAssignStmt(span=sp, name=name, op=op, value=None)
            if op != "=":
                return AugAssignStmt(span=sp, name=name, op=op, value=_parse_expression(p))
            return AssignStmt(span=sp, name=name, value=_parse_expression(p))
    left = _parse_expression(p)
    if p.at(TokenKind.OP) and p.cur().text in {"=", "+=", "-=", "*=", "/=", "%="}:
        op = p.eat(TokenKind.OP).text
        right = _parse_expression(p)
        lval = _expr_to_lvalue(left)
        if op == "=":
            return AssignStmt(span=sp, name=lval, value=right)
        return AugAssignStmt(span=sp, name=lval, op=op, value=right)
    return ExprStmt(span=sp, expr=left)


def _expr_to_source(expr: Expr) -> str:
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, Literal):
        return expr.text
    if isinstance(expr, Member):
        return f"{_expr_to_source(expr.object)}.{expr.name}"  # type: ignore[arg-type]
    if isinstance(expr, Index):
        return f"{_expr_to_source(expr.object)}[{_expr_to_source(expr.index)}]"  # type: ignore[arg-type]
    if isinstance(expr, Call):
        args = ", ".join(_expr_to_source(a) for a in expr.args)
        return f"{_expr_to_source(expr.callee)}({args})"  # type: ignore[arg-type]
    return "<?>"


def _expr_to_lvalue(expr: Expr) -> str:
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, Member):
        return f"{_expr_to_lvalue(expr.object)}.{expr.name}"  # type: ignore[arg-type]
    if isinstance(expr, Index):
        return f"{_expr_to_lvalue(expr.object)}[{_expr_to_source(expr.index)}]"  # type: ignore[arg-type]
    return "<?>"


def _parse_print(p: _Tok) -> PrintStmt:
    sp = p.span()
    p.eat_kw("print")
    if p.at(TokenKind.LPAREN):
        p.eat(TokenKind.LPAREN)
        value = _parse_expression(p)
        p.eat(TokenKind.RPAREN)
    else:
        value = _parse_expression(p)
    return PrintStmt(span=sp, value=value)


@_packrat("block")
def _parse_block(p: _Tok) -> Block:
    sp = p.span()
    p.eat(TokenKind.LBRACE)
    stmts = []
    prev_end_line: int | None = None
    had_semi = False
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK) or p.at(TokenKind.COMMENT):
            stmts.append(_parse_statement(p))
            continue
        _check_same_line_boundary(p, prev_end_line=prev_end_line, had_semi=had_semi)
        stmts.append(_parse_statement(p))
        prev_end_line, had_semi = _finish_stmt_terminator(p)
    end = p.eat(TokenKind.RBRACE)
    return Block(span=p.close_span(sp, end), statements=stmts)


def _parse_if(p: _Tok) -> IfStmt:
    sp = p.span()
    p.eat_kw("if")
    negated = False
    if p.at_kw("not"):
        p.eat_kw("not")
        negated = True
    p.eat(TokenKind.LPAREN)
    cond = _parse_expression(p)
    p.eat(TokenKind.RPAREN)
    then_body = _parse_block(p)
    else_body = None
    if p.at_kw("else"):
        p.eat_kw("else")
        if p.at_kw("if"):
            else_body = Block(statements=[_parse_if(p)])
        else:
            else_body = _parse_block(p)
    return IfStmt(span=sp, cond=cond, then_body=then_body, else_body=else_body, negated=negated)


def _parse_unless(p: _Tok) -> IfStmt:
    sp = p.span()
    p.eat_kw("unless")
    p.eat(TokenKind.LPAREN)
    cond = _parse_expression(p)
    p.eat(TokenKind.RPAREN)
    body = _parse_block(p)
    return IfStmt(span=sp, cond=cond, then_body=body, else_body=None, negated=True)


def _skip_switch_noise(p: _Tok) -> None:
    while p.at(TokenKind.BLANK) or p.at(TokenKind.COMMENT):
        p.eat(p.cur().kind)


def _parse_switch_stmt_body(p: _Tok, arm_sp: Span) -> tuple[Block, bool, bool]:
    """Parse statement-arm body: explicit ``{ }`` block or bare statement sequence.

    Returns ``(body, fallthrough, brace_scoped)``.
    """
    if p.at(TokenKind.LBRACE):
        body = _parse_block(p)
        fallthrough = False
        stmts = list(body.statements)
        if stmts and isinstance(stmts[-1], ContinueStmt):
            fallthrough = True
            stmts = stmts[:-1]
            body = Block(span=body.span, statements=stmts)
        return body, fallthrough, True

    body_stmts: list = []
    prev_end_line: int | None = None
    had_semi = False
    while not p.at(TokenKind.RBRACE) and not p.at_kw("case", "default"):
        _skip_switch_noise(p)
        if p.at(TokenKind.RBRACE) or p.at_kw("case", "default"):
            break
        _check_same_line_boundary(p, prev_end_line=prev_end_line, had_semi=had_semi)
        body_stmts.append(_parse_statement(p))
        prev_end_line, had_semi = _finish_stmt_terminator(p)
    fallthrough = False
    if body_stmts and isinstance(body_stmts[-1], ContinueStmt):
        fallthrough = True
        body_stmts = body_stmts[:-1]
    return Block(span=arm_sp, statements=body_stmts), fallthrough, False


def _reject_legacy_err_ctor(p: _Tok, *, pattern: bool) -> None:
    """Reject former ``err(...)`` spelling; tip callers toward ``error(...)``."""
    tok = p.cur()
    if tok.kind != TokenKind.IDENT or tok.text != "err":
        return
    if p.peek(1).kind != TokenKind.LPAREN:
        return
    if pattern:
        raise FatalParseError(
            "`err` is not a result pattern; use `error`.",
            tok.line,
            tok.column,
            code="pys.result-err-renamed",
            tips=["Write `case error(message)` instead of `case err(...)`."],
            suggested_fix="error",
        )
    raise FatalParseError(
        "`err` is not a result constructor; use `error`.",
        tok.line,
        tok.column,
        code="pys.result-err-renamed",
        tips=["Write `error(payload)` instead of `err(...)`."],
        suggested_fix="error",
    )


def _parse_case_label(p: _Tok) -> Expr:
    """Parse a case label: literal, bare name, or ``Enum.MEMBER``."""
    sp = p.span()
    _reject_legacy_err_ctor(p, pattern=True)
    if p.at_kw("ok", "error") and p.peek(1).kind == TokenKind.LPAREN:
        kind = p.eat(TokenKind.KEYWORD).text
        p.eat(TokenKind.LPAREN)
        binding = ""
        binding_span: Span | None = None
        if not p.at(TokenKind.RPAREN):
            token = p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
            binding = token.text
            binding_span = p.token_span(token)
        elif kind == "error":
            raise FatalParseError(
                "`error` switch patterns require an error binding.",
                sp.line,
                sp.column,
                code="pys.result-pattern",
                tips=["Write `case error(message)`."],
            )
        p.eat(TokenKind.RPAREN)
        return ResultPattern(
            span=sp,
            kind=kind,
            binding=binding,
            binding_span=binding_span,
        )
    if p.at(TokenKind.INT):
        return Literal(span=sp, kind="int", text=p.eat(TokenKind.INT).text)
    if p.at(TokenKind.STRING):
        return Literal(span=sp, kind="string", text=p.eat(TokenKind.STRING).text)
    if p.at(TokenKind.CHAR):
        return Literal(span=sp, kind="char", text=p.eat(TokenKind.CHAR).text)
    if p.at_kw("true", "false"):
        return Literal(span=sp, kind="bool", text=p.eat(TokenKind.KEYWORD).text)
    if p.at_kw("null"):
        p.eat_kw("null")
        return Literal(span=sp, kind="null", text="null")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    if p.at(TokenKind.DOT):
        p.eat(TokenKind.DOT)
        member = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        return Member(
            span=sp,
            object=Identifier(span=sp, name=name),
            name=member,
        )
    return Identifier(span=sp, name=name)


def _switch_form_is_expr(p: _Tok) -> bool:
    """True if the switch body uses ``=>`` arms (expression form)."""
    saved = p.i
    saved_gt = p._pending_gt
    try:
        _skip_switch_noise(p)
        if p.at(TokenKind.RBRACE):
            return False
        if p.at_kw("default"):
            p.eat_kw("default")
            return p.at(TokenKind.OP, text="=>")
        if not p.at_kw("case"):
            return False
        p.eat_kw("case")
        _parse_case_label(p)
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            _parse_case_label(p)
        return p.at(TokenKind.OP, text="=>")
    finally:
        p.i = saved
        p._pending_gt = saved_gt


def _parse_switch_common(p: _Tok) -> tuple[Span, Expr, list[SwitchCase], bool]:
    """Parse ``switch (subject) { arms }``. Returns (span, subject, cases, is_expr)."""
    sp = p.span()
    p.eat_kw("switch")
    p.eat(TokenKind.LPAREN)
    subject = _parse_expression(p)
    p.eat(TokenKind.RPAREN)
    p.eat(TokenKind.LBRACE)
    is_expr = _switch_form_is_expr(p)
    cases: list[SwitchCase] = []
    while not p.at(TokenKind.RBRACE):
        _skip_switch_noise(p)
        if p.at(TokenKind.RBRACE):
            break
        arm_sp = p.span()
        if p.at_kw("default"):
            p.eat_kw("default")
            if is_expr:
                if not p.at(TokenKind.OP, text="=>"):
                    raise FatalParseError(
                        "Switch expression arms use `=>` (found statement-style `:`).",
                        p.cur().line,
                        p.cur().column,
                    )
                p.eat(TokenKind.OP, text="=>")
                value = _parse_expression(p)
                cases.append(
                    SwitchCase(span=arm_sp, is_default=True, value=value)
                )
            else:
                if p.at(TokenKind.OP, text="=>"):
                    raise FatalParseError(
                        "Switch statement arms use `:` (found expression-style `=>`).",
                        p.cur().line,
                        p.cur().column,
                    )
                p.eat(TokenKind.COLON)
                body, fallthrough, brace_scoped = _parse_switch_stmt_body(p, arm_sp)
                cases.append(
                    SwitchCase(
                        span=arm_sp,
                        is_default=True,
                        body=body,
                        fallthrough=fallthrough,
                        brace_scoped=brace_scoped,
                    )
                )
            continue
        if not p.at_kw("case"):
            raise ParseError(
                "Expected `case` or `default` in switch.",
                p.cur().line,
                p.cur().column,
            )
        p.eat_kw("case")
        labels = [_parse_case_label(p)]
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            labels.append(_parse_case_label(p))
        if is_expr:
            if p.at(TokenKind.COLON):
                raise FatalParseError(
                    "Switch expression arms use `=>` (found statement-style `:`).",
                    p.cur().line,
                    p.cur().column,
                )
            p.eat(TokenKind.OP, text="=>")
            value = _parse_expression(p)
            cases.append(SwitchCase(span=arm_sp, labels=labels, value=value))
        else:
            if p.at(TokenKind.OP, text="=>"):
                raise FatalParseError(
                    "Switch statement arms use `:` (found expression-style `=>`).",
                    p.cur().line,
                    p.cur().column,
                )
            p.eat(TokenKind.COLON)
            body, fallthrough, brace_scoped = _parse_switch_stmt_body(p, arm_sp)
            cases.append(
                SwitchCase(
                    span=arm_sp,
                    labels=labels,
                    body=body,
                    fallthrough=fallthrough,
                    brace_scoped=brace_scoped,
                )
            )
    p.eat(TokenKind.RBRACE)
    if not cases:
        raise FatalParseError(
            "Switch must have at least one `case` or `default` arm.",
            sp.line,
            sp.column,
        )
    return sp, subject, cases, is_expr


def _parse_switch_stmt(p: _Tok) -> SwitchStmt | ExprStmt:
    """Parse a switch used as a statement (or reject expression-only misuse)."""
    sp, subject, cases, is_expr = _parse_switch_common(p)
    if is_expr:
        # Bare switch-expression as a statement is allowed as ExprStmt.
        return ExprStmt(
            span=sp,
            expr=SwitchExpr(span=sp, subject=subject, cases=cases),
        )
    return SwitchStmt(span=sp, subject=subject, cases=cases)


def _parse_switch_expr(p: _Tok) -> SwitchExpr:
    sp, subject, cases, is_expr = _parse_switch_common(p)
    if not is_expr:
        raise FatalParseError(
            "Switch expression requires `=>` arms "
            "(statement form with `:` cannot be used as a value).",
            sp.line,
            sp.column,
        )
    return SwitchExpr(span=sp, subject=subject, cases=cases)


def _parse_loop(p: _Tok):
    sp = p.span()
    p.eat_kw("loop")
    p.eat(TokenKind.LPAREN)

    has_in = False
    depth = 0
    j = p.i
    while j < len(p.tokens) and p.tokens[j].kind != TokenKind.EOF:
        t = p.tokens[j]
        if t.kind == TokenKind.LPAREN:
            depth += 1
        elif t.kind == TokenKind.RPAREN:
            if depth == 0:
                break
            depth -= 1
        elif t.kind == TokenKind.KEYWORD and t.text == "in" and depth == 0:
            has_in = True
            break
        j += 1

    if has_in:
        var_type = ""
        # Optional element type: `int x in`, `tuple x in`, `list<int> x in`
        if (p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD)) and not p.at_kw("in"):
            if p.peek(1).kind == TokenKind.LT or (
                p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
                and p.peek(2).kind == TokenKind.KEYWORD
                and p.peek(2).text == "in"
            ):
                var_type = _parse_type_name(p)
            elif p.at_kw(*_TYPES):
                var_type = p.eat(TokenKind.KEYWORD).text
                # Multi-dim element binders: `int[] row in grid`, `int[][] plane in cubes`
                if p.at(TokenKind.LBRACK):
                    dims = _parse_array_dims(p)
                    if any(d is not None for d in dims):
                        sized = "".join("[]" if d is None else f"[{d}]" for d in dims)
                        unsized = "[]" * len(dims)
                        raise FatalParseError(
                            f"Sized array type `{var_type}{sized}` is not valid as a loop binder. "
                            f"Write `loop ({var_type}{unsized} name in …)`.",
                            p.cur().line,
                            p.cur().column,
                        )
                    var_type = var_type + ("[]" * len(dims))
        var = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat_kw("in")
        it = _parse_expression(p)
        p.eat(TokenKind.RPAREN)
        body = _parse_block(p)
        return ForEachStmt(span=sp, var=var, var_type=var_type, iterable=it, body=body)

    commas = 0
    semis = 0
    depth = 0
    j = p.i
    while j < len(p.tokens):
        t = p.tokens[j]
        if t.kind == TokenKind.LPAREN:
            depth += 1
        elif t.kind == TokenKind.RPAREN:
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and t.kind == TokenKind.SEMI:
            semis += 1
        elif depth == 0 and t.text == ",":
            commas += 1
        j += 1

    if commas >= 2 and semis < 2:
        raise FatalParseError(
            "C-style `loop` headers use ';' between init, condition, and step "
            "(comma separators are no longer valid).",
            p.cur().line,
            p.cur().column,
            code="pys.c-for-semi",
            tips=[
                "Write `loop (int i = 0; i < n; i++) { … }`.",
            ],
        )

    if semis >= 2:
        if p.at_kw("int", "float"):
            p.eat(TokenKind.KEYWORD)
        var = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat(TokenKind.OP, text="=")
        start = _parse_expression(p)
        p.eat(TokenKind.SEMI)
        p.eat(TokenKind.IDENT, TokenKind.KEYWORD)  # var in cond
        if p.at(TokenKind.LT, TokenKind.GT) or (p.at(TokenKind.OP) and p.cur().text in {"<=", ">=", "<", ">"}):
            p.eat(p.cur().kind)
        else:
            p.eat(TokenKind.OP)
        stop_expr = _parse_expression(p)
        p.eat(TokenKind.SEMI)
        p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
        if p.at(TokenKind.OP) and p.cur().text in {"++", "--"}:
            p.eat(TokenKind.OP)
        else:
            p.eat(TokenKind.OP)
            _parse_expression(p)
        p.eat(TokenKind.RPAREN)
        body = _parse_block(p)
        return ForRangeStmt(span=sp, var=var, start=start, stop=stop_expr, body=body)

    cond = _parse_expression(p)
    p.eat(TokenKind.RPAREN)
    body = _parse_block(p)
    return WhileStmt(span=sp, cond=cond, body=body)


@_packrat("expression")
def _parse_expression(p: _Tok) -> Expr:
    # Lambda forms bind tighter than being an operand of `+` etc.: they are
    # recognized at the start of an expression (call args, bindings, …).
    if _at_lambda_expr(p):
        return _parse_lambda_expr(p)
    return _parse_or(p)


def _at_lambda_expr(p: _Tok) -> bool:
    # n => …
    if (
        p.cur().kind in {TokenKind.IDENT, TokenKind.KEYWORD}
        and p.cur().text
        not in {
            "if",
            "unless",
            "loop",
            "print",
            "return",
            "pass",
            "break",
            "continue",
            "else",
            "function",
            "class",
            "switch",
            "case",
            "default",
            "not",
            "await",
            "shared",
            "tasks",
            "task",
            "true",
            "false",
            "null",
            "this",
            "super",
        }
        and p.peek(1).kind == TokenKind.OP
        and p.peek(1).text == "=>"
    ):
        return True
    # ( … ) => …
    if p.at(TokenKind.LPAREN):
        return _paren_group_followed_by_arrow(p)
    return False


def _paren_group_followed_by_arrow(p: _Tok) -> bool:
    if not p.at(TokenKind.LPAREN):
        return False
    depth = 0
    k = 0
    while True:
        t = p.peek(k)
        if t.kind == TokenKind.EOF:
            return False
        if t.kind == TokenKind.LPAREN:
            depth += 1
        elif t.kind == TokenKind.RPAREN:
            depth -= 1
            if depth == 0:
                nxt = p.peek(k + 1)
                return nxt.kind == TokenKind.OP and nxt.text == "=>"
            if depth < 0:
                return False
        k += 1


def _parse_lambda_body(p: _Tok) -> Expr | Block:
    if p.at(TokenKind.LBRACE):
        return _parse_block(p)
    return _parse_expression(p)


def _parse_lambda_expr(p: _Tok) -> LambdaExpr:
    sp = p.span()
    params: list[str] = []
    param_types: list[str] = []
    if p.at(TokenKind.LPAREN):
        p.eat(TokenKind.LPAREN)
        if not p.at(TokenKind.RPAREN):
            t, n = _parse_param(p)
            params.append(n)
            param_types.append(t)
            while p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                t, n = _parse_param(p)
                params.append(n)
                param_types.append(t)
        p.eat(TokenKind.RPAREN)
    else:
        name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        params.append(name)
        param_types.append("")
    p.eat(TokenKind.OP, text="=>")
    body = _parse_lambda_body(p)
    return LambdaExpr(span=sp, params=params, param_types=param_types, body=body)


@_packrat("or")
def _parse_or(p: _Tok) -> Expr:
    left = _parse_and(p)
    while p.at_kw("or") or p.at(TokenKind.OP, text="||"):
        op = p.eat(TokenKind.KEYWORD, TokenKind.OP).text
        if op == "||":
            op = "or"
        right = _parse_and(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


@_packrat("and")
def _parse_and(p: _Tok) -> Expr:
    left = _parse_not(p)
    while p.at_kw("and") or p.at(TokenKind.OP, text="&&"):
        op = p.eat(TokenKind.KEYWORD, TokenKind.OP).text
        if op == "&&":
            op = "and"
        right = _parse_not(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


@_packrat("not")
def _parse_not(p: _Tok) -> Expr:
    if p.at_kw("not") or p.at(TokenKind.OP, text="!"):
        sp = p.span()
        op = p.eat(TokenKind.KEYWORD, TokenKind.OP).text
        if op == "!":
            op = "not"
        return UnaryOp(span=sp, op=op, operand=_parse_not(p))
    return _parse_cmp(p)


@_packrat("cmp")
def _parse_cmp(p: _Tok) -> Expr:
    left = _parse_bit_or(p)
    if p.at_kw("in"):
        p.eat_kw("in")
        right = _parse_bit_or(p)
        return BinaryOp(span=left.span, op="in", left=left, right=right)
    if p.at(TokenKind.LT, TokenKind.GT) or (
        p.at(TokenKind.OP) and p.cur().text in {"==", "!=", "<>", "<=", ">="}
    ):
        op = p.eat(p.cur().kind).text
        if op == "<>":
            op = "!="
        right = _parse_bit_or(p)
        return BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


def _reject_rotate(p: _Tok) -> None:
    if p.at(TokenKind.OP) and p.cur().text in {"<<<", ">>>"}:
        raise FatalParseError(_ROTATE_DEFERRED, p.cur().line, p.cur().column)


@_packrat("bit_or")
def _parse_bit_or(p: _Tok) -> Expr:
    left = _parse_bit_xor(p)
    while p.at(TokenKind.OP, text="|"):
        p.eat(TokenKind.OP, text="|")
        right = _parse_bit_xor(p)
        left = BinaryOp(span=left.span, op="|", left=left, right=right)
    return left


@_packrat("bit_xor")
def _parse_bit_xor(p: _Tok) -> Expr:
    left = _parse_bit_and(p)
    while p.at_kw("xor") or p.at(TokenKind.OP, text="^"):
        if p.at_kw("xor"):
            p.eat_kw("xor")
            op = "^"
        else:
            p.eat(TokenKind.OP, text="^")
            op = "^"
        right = _parse_bit_and(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


@_packrat("bit_and")
def _parse_bit_and(p: _Tok) -> Expr:
    left = _parse_shift(p)
    while p.at(TokenKind.OP, text="&"):
        p.eat(TokenKind.OP, text="&")
        right = _parse_shift(p)
        left = BinaryOp(span=left.span, op="&", left=left, right=right)
    return left


def _at_shift_word(p: _Tok) -> bool:
    if not p.at_kw("shift"):
        return False
    nxt = p.peek(1)
    return nxt.kind in {TokenKind.IDENT, TokenKind.KEYWORD} and nxt.text in {"left", "right"}


@_packrat("shift")
def _parse_shift(p: _Tok) -> Expr:
    left = _parse_add(p)
    while True:
        _reject_rotate(p)
        if p.at(TokenKind.OP) and p.cur().text in {"<<", ">>"}:
            op = p.eat(TokenKind.OP).text
            right = _parse_add(p)
            left = BinaryOp(span=left.span, op=op, left=left, right=right)
            continue
        if _at_shift_word(p):
            p.eat_kw("shift")
            direction = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            op = "<<" if direction == "left" else ">>"
            right = _parse_add(p)
            left = BinaryOp(span=left.span, op=op, left=left, right=right)
            continue
        break
    return left


@_packrat("add")
def _parse_add(p: _Tok) -> Expr:
    left = _parse_mul(p)
    while p.at(TokenKind.OP) and p.cur().text in {"+", "-"}:
        op = p.eat(TokenKind.OP).text
        right = _parse_mul(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


@_packrat("mul")
def _parse_mul(p: _Tok) -> Expr:
    left = _parse_power(p)
    while p.at(TokenKind.OP) and p.cur().text in {"*", "/", "%", "//"}:
        op = p.eat(TokenKind.OP).text
        right = _parse_power(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


@_packrat("power")
def _parse_power(p: _Tok) -> Expr:
    left = _parse_unary(p)
    if p.at(TokenKind.OP, text="**"):
        p.eat(TokenKind.OP, text="**")
        right = _parse_power(p)  # right-associative
        return BinaryOp(span=left.span, op="**", left=left, right=right)
    return left


@_packrat("unary")
def _parse_unary(p: _Tok) -> Expr:
    if p.at_kw("await"):
        sp = p.span()
        p.eat_kw("await")
        return AwaitExpr(span=sp, target=_parse_cast_postfix(p))
    if p.at(TokenKind.OP) and p.cur().text in {"+", "-", "~"}:
        sp = p.span()
        op = p.eat(TokenKind.OP).text
        return UnaryOp(span=sp, op=op, operand=_parse_unary(p))
    return _parse_cast_postfix(p)


@_packrat("cast_postfix")
def _parse_cast_postfix(p: _Tok) -> Expr:
    # (int) x  or  (Truck) c  — type name then ')' then operand
    if (
        p.at(TokenKind.LPAREN)
        and p.peek(1).kind in {TokenKind.KEYWORD, TokenKind.IDENT}
        and p.peek(2).kind == TokenKind.RPAREN
    ):
        type_tok = p.peek(1)
        # Avoid treating `(name)` grouping of a bare name as a cast when not followed
        # by a cast operand — still OK: `(Truck) c` has operand; `(x)` alone is primary.
        # Heuristic: keyword types always cast; IDENT cast if next after ')' looks like expr start.
        after = p.peek(3)
        looks_like_operand = after.kind in {
            TokenKind.IDENT,
            TokenKind.KEYWORD,
            TokenKind.INT,
            TokenKind.FLOAT,
            TokenKind.STRING,
            TokenKind.CHAR,
            TokenKind.LPAREN,
            TokenKind.LBRACK,
        } or (after.kind == TokenKind.OP and after.text in {"+", "-", "!"})
        if type_tok.text in _TYPES or (type_tok.kind == TokenKind.IDENT and looks_like_operand):
            sp = p.span()
            p.eat(TokenKind.LPAREN)
            tn = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
            p.eat(TokenKind.RPAREN)
            return Cast(span=sp, type_name=tn, expr=_parse_cast_postfix(p))
    return _parse_postfix(p)


def _parse_call_arg(p: _Tok) -> Expr:
    if (
        p.cur().kind in {TokenKind.IDENT, TokenKind.KEYWORD}
        and p.peek(1).kind == TokenKind.OP
        and p.peek(1).text == "="
    ):
        sp = p.span()
        name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat(TokenKind.OP, text="=")
        return KeywordArg(span=sp, name=name, value=_parse_expression(p))
    return _parse_expression(p)


@_packrat("postfix")
def _parse_postfix(p: _Tok) -> Expr:
    expr = _parse_primary(p)
    # Generic constructor sugar: Type<Args>(...) — drop type args for Python emit.
    if isinstance(expr, Identifier) and p.at(TokenKind.LT):
        saved = p.i
        saved_gt = p._pending_gt
        try:
            p.eat(TokenKind.LT)
            _parse_type_name(p)
            while p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                _parse_type_name(p)
            p.eat_gt()
            if not p.at(TokenKind.LPAREN):
                raise ParseError("not a constructor", p.cur().line, p.cur().column)
        except ParseError:
            p.i = saved
            p._pending_gt = saved_gt
    while True:
        if p.at(TokenKind.LPAREN):
            sp = expr.span
            p.eat(TokenKind.LPAREN)
            args: list[Expr] = []
            if not p.at(TokenKind.RPAREN):
                args.append(_parse_call_arg(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    args.append(_parse_call_arg(p))
            p.eat(TokenKind.RPAREN)
            expr = Call(span=sp, callee=expr, args=args)
        elif p.at(TokenKind.DOT):
            p.eat(TokenKind.DOT)
            name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            expr = Member(span=expr.span, object=expr, name=name)
        elif p.at(TokenKind.LBRACK):
            p.eat(TokenKind.LBRACK)
            start: Expr | None
            if p.at(TokenKind.COLON):
                start = None
            else:
                start = _parse_expression(p)
            if p.at(TokenKind.COLON):
                p.eat(TokenKind.COLON)
                stop = None
                if not p.at(TokenKind.COLON) and not p.at(TokenKind.RBRACK):
                    stop = _parse_expression(p)
                step = None
                if p.at(TokenKind.COLON):
                    p.eat(TokenKind.COLON)
                    if not p.at(TokenKind.RBRACK):
                        step = _parse_expression(p)
                p.eat(TokenKind.RBRACK)
                expr = Slice(span=expr.span, object=expr, start=start, stop=stop, step=step)
            else:
                p.eat(TokenKind.RBRACK)
                expr = Index(span=expr.span, object=expr, index=start)
        elif p.at_kw("propagate"):
            p.eat_kw("propagate")
            expr = PropagateExpr(span=expr.span, operand=expr)
        else:
            break
    return expr


@_packrat("primary")
def _parse_primary(p: _Tok) -> Expr:
    sp = p.span()
    if p.at_kw("switch"):
        return _parse_switch_expr(p)
    if p.at(TokenKind.INT):
        return Literal(span=sp, kind="int", text=p.eat(TokenKind.INT).text)
    if p.at(TokenKind.FLOAT):
        return Literal(span=sp, kind="float", text=p.eat(TokenKind.FLOAT).text)
    if p.at(TokenKind.STRING):
        raw = p.eat(TokenKind.STRING).text
        inner = raw[1:-1] if len(raw) >= 2 else raw
        if "{" in inner or "#s{" in inner or "#i{" in inner or r"\#" in inner:
            return InterpolatedString(span=sp, raw=raw)
        return Literal(span=sp, kind="string", text=raw)
    if p.at(TokenKind.CHAR):
        return Literal(span=sp, kind="char", text=p.eat(TokenKind.CHAR).text)
    if p.at_kw("true", "false"):
        return Literal(span=sp, kind="bool", text=p.eat(TokenKind.KEYWORD).text)
    if p.at_kw("null"):
        p.eat_kw("null")
        return Literal(span=sp, kind="null", text="null")
    _reject_legacy_err_ctor(p, pattern=False)
    if p.at_kw("ok", "error"):
        kind = p.eat(TokenKind.KEYWORD).text
        p.eat(TokenKind.LPAREN)
        value: Expr | None = None
        if not p.at(TokenKind.RPAREN):
            value = _parse_expression(p)
        elif kind == "error":
            raise FatalParseError(
                "`error` requires an error value.",
                sp.line,
                sp.column,
                code="pys.result-error-value",
                tips=["Write `error(payload)`."],
            )
        p.eat(TokenKind.RPAREN)
        return ResultCtor(span=sp, kind=kind, value=value)
    if p.at_kw("this"):
        p.eat_kw("this")
        return Identifier(span=sp, name="self")
    if p.at(TokenKind.LBRACK):
        p.eat(TokenKind.LBRACK)
        elems: list[Expr] = []
        if not p.at(TokenKind.RBRACK):
            elems.append(_parse_expression(p))
            while p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                if p.at(TokenKind.RBRACK):
                    break
                elems.append(_parse_expression(p))
        p.eat(TokenKind.RBRACK)
        return ArrayLiteral(span=sp, elements=elems)
    if p.at(TokenKind.LBRACE):
        return _parse_brace_literal(p, sp)
    if p.at(TokenKind.LPAREN):
        return _parse_paren_primary(p, sp)
    if p.at_kw(*_ARRAY_ELEM_TYPES) and p.peek(1).kind == TokenKind.LBRACK:
        return _parse_array_alloc(p)
    if p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD):
        if p.cur().text == "new":
            raise FatalParseError(
                "Unexpected `new`. Construct values with `TypeName(...)` "
                "(structs and classes have no `new` keyword).",
                p.cur().line,
                p.cur().column,
            )
        name_tok = p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
        return Identifier(span=p.token_span(name_tok), name=name_tok.text)
    raise ParseError(f"Unexpected token {p.cur().text!r}", p.cur().line, p.cur().column)


def _parse_brace_literal(p: _Tok, sp: Span) -> Expr:
    """Parse `{…}` as DictLiteral (keyed) or BraceLiteral (unkeyed / empty)."""
    p.eat(TokenKind.LBRACE)
    if p.at(TokenKind.RBRACE):
        p.eat(TokenKind.RBRACE)
        return BraceLiteral(span=sp, elements=[])
    first = _parse_expression(p)
    if p.at(TokenKind.COLON):
        p.eat(TokenKind.COLON)
        first_val = _parse_expression(p)
        entries: list[tuple[Expr, Expr]] = [(first, first_val)]
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            if p.at(TokenKind.RBRACE):
                break
            key = _parse_expression(p)
            if not p.at(TokenKind.COLON):
                raise FatalParseError(
                    "Dict literal entries must all be `key: value`. "
                    "Do not mix bare elements with keyed pairs.",
                    p.cur().line,
                    p.cur().column,
                )
            p.eat(TokenKind.COLON)
            val = _parse_expression(p)
            entries.append((key, val))
        p.eat(TokenKind.RBRACE)
        return DictLiteral(span=sp, entries=entries)
    elems: list[Expr] = [first]
    while p.at(TokenKind.COMMA):
        p.eat(TokenKind.COMMA)
        if p.at(TokenKind.RBRACE):
            break
        el = _parse_expression(p)
        if p.at(TokenKind.COLON):
            raise FatalParseError(
                "Dict literal entries must all be `key: value`. "
                "Do not mix bare elements with keyed pairs.",
                p.cur().line,
                p.cur().column,
            )
        elems.append(el)
    p.eat(TokenKind.RBRACE)
    return BraceLiteral(span=sp, elements=elems)


def _parse_paren_primary(p: _Tok, sp: Span) -> Expr:
    """Parse `(…)` as grouping or TupleLiteral."""
    p.eat(TokenKind.LPAREN)
    if p.at(TokenKind.RPAREN):
        p.eat(TokenKind.RPAREN)
        return TupleLiteral(span=sp, elements=[])
    first = _parse_expression(p)
    if p.at(TokenKind.COMMA):
        elems: list[Expr] = [first]
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            if p.at(TokenKind.RPAREN):
                break
            elems.append(_parse_expression(p))
        p.eat(TokenKind.RPAREN)
        return TupleLiteral(span=sp, elements=elems)
    p.eat(TokenKind.RPAREN)
    return first
