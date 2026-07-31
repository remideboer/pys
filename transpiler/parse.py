"""Token-based recursive-descent parser → AST."""
from __future__ import annotations

from .ast_nodes import (
    ArrayDecl,
    ArrayLiteral,
    AssignStmt,
    AugAssignStmt,
    BinaryOp,
    BlankStmt,
    Block,
    BreakStmt,
    Call,
    Cast,
    ClassDef,
    CommentStmt,
    ContinueStmt,
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
    Literal,
    Member,
    MethodDef,
    Module,
    PassStmt,
    PrintStmt,
    RepeatStmt,
    ReturnStmt,
    Slice,
    Span,
    UnaryOp,
    WhileStmt,
)
from .lex import LexError, Token, TokenKind, tokenize

_TYPES = frozenset({"int", "float", "char", "string", "bool"})
_VIS = frozenset({"global", "package", "module"})


class ParseError(ValueError):
    def __init__(self, message: str, line: int = 1, column: int = 1) -> None:
        self.line = line
        self.column = column
        super().__init__(f"{message} (line {line}, column {column})")


class _Tok:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.i = 0

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


def parse_program(source: str) -> Module:
    try:
        tokens = tokenize(source)
    except LexError as exc:
        raise ParseError(str(exc.message), exc.line, exc.column) from exc

    brace_mode = any(t.kind in {TokenKind.LBRACE, TokenKind.RBRACE} for t in tokens)

    legacy_markers = ("tasks", "task", "await", "shared")
    if any(t.kind == TokenKind.KEYWORD and t.text in legacy_markers for t in tokens):
        return Module(span=Span(1, 1), source=source, body=[], brace_mode=brace_mode, use_legacy=True)

    # Indent-style forms (then/func/repeat/…) — try line-based parse before legacy.
    if any(
        t.kind == TokenKind.KEYWORD and t.text in {"then", "do", "times", "func", "repeat"}
        for t in tokens
    ):
        try:
            body = _parse_indent_program(source)
            return Module(span=Span(1, 1), source=source, body=body, brace_mode=False, use_legacy=False)
        except ParseError:
            return Module(span=Span(1, 1), source=source, body=[], brace_mode=False, use_legacy=True)

    p = _Tok(tokens)
    body: list = []
    try:
        while not p.done():
            body.append(_parse_toplevel(p))
    except ParseError:
        return Module(span=Span(1, 1), source=source, body=[], brace_mode=brace_mode, use_legacy=True)

    return Module(span=Span(1, 1), source=source, body=body, brace_mode=brace_mode, use_legacy=False)


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


def _parse_toplevel(p: _Tok):
    if p.at(TokenKind.BLANK):
        t = p.eat(TokenKind.BLANK)
        return BlankStmt(span=Span(t.line, t.column))
    if p.at(TokenKind.COMMENT):
        t = p.eat(TokenKind.COMMENT)
        return CommentStmt(span=Span(t.line, t.column), text=t.text)
    if p.at_kw("import"):
        return _parse_import(p)
    if p.at_kw(*_VIS):
        vis = p.eat(TokenKind.KEYWORD).text
        if p.at_kw("function"):
            return _parse_function(p, visibility=vis)
        if p.at_kw("sealed"):
            return _parse_class(p, visibility=vis)
        if p.at_kw("class"):
            return _parse_class(p, visibility=vis)
        if p.at_kw("interface"):
            return _parse_interface(p, visibility=vis)
        if p.at_kw("const", "fix") or p.at_kw(*_TYPES) or p.at_kw("var"):
            return _parse_decl(p, visibility=vis)
        raise ParseError("Expected declaration after visibility", p.cur().line, p.cur().column)
    if p.at_kw("function"):
        return _parse_function(p)
    if p.at_kw("sealed"):
        return _parse_class(p)
    if p.at_kw("class"):
        return _parse_class(p)
    if p.at_kw("interface"):
        return _parse_interface(p)
    return _parse_statement(p)


def _parse_import(p: _Tok) -> ImportStmt:
    sp = p.span()
    p.eat_kw("import")
    if p.at_kw("all"):
        p.eat_kw("all")
        p.eat_kw("from")
        mod = _parse_dotted_name(p)
        return ImportStmt(span=sp, kind="all_from", module=mod)
    first = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    if p.at_kw("from"):
        p.eat_kw("from")
        mod = _parse_dotted_name(p)
        return ImportStmt(span=sp, kind="name_from", module=mod, name=first)
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


def _parse_dotted_name(p: _Tok) -> str:
    parts = [p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text]
    while p.at(TokenKind.DOT):
        p.eat(TokenKind.DOT)
        nxt = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if nxt == "pys":
            break
        parts.append(nxt)
    return ".".join(parts)


def _looks_like_typed_name(p: _Tok) -> bool:
    """TYPE name (  — used for optional function return type."""
    t0 = p.cur()
    t1 = p.peek(1)
    t2 = p.peek(2)
    if t0.kind not in {TokenKind.KEYWORD, TokenKind.IDENT}:
        return False
    if t0.text not in _TYPES and t0.kind != TokenKind.IDENT:
        return False
    if t1.kind not in {TokenKind.IDENT, TokenKind.KEYWORD}:
        return False
    return t2.kind == TokenKind.LPAREN


def _parse_function(p: _Tok, visibility: str = "") -> FunctionDef:
    sp = p.span()
    p.eat_kw("function")
    if _looks_like_typed_name(p):
        p.eat(TokenKind.KEYWORD, TokenKind.IDENT)  # return type
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
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
        span=sp,
        name=name,
        params=[n for _, n in params],
        body=body,
        visibility=visibility,
    )


def _parse_param(p: _Tok) -> tuple[str, str]:
    """Return (type_or_empty, name)."""
    type_name = ""
    t0 = p.cur()
    t1 = p.peek(1)
    if t0.text in _TYPES or (
        t0.kind in {TokenKind.IDENT, TokenKind.KEYWORD}
        and t1.kind in {TokenKind.IDENT, TokenKind.KEYWORD}
        and t1.text not in {",", ")"}
        and t1.kind != TokenKind.RPAREN
    ):
        # TYPE name — only consume type if next token looks like a name
        if t1.kind in {TokenKind.IDENT, TokenKind.KEYWORD} and t1.text not in {",", ")"}:
            # Avoid consuming the only name: if next is , or ) after one ident, it's name-only
            t2 = p.peek(2)
            if t2.kind in {TokenKind.COMMA, TokenKind.RPAREN} or t2.text in {",", ")"}:
                type_name = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
            elif t0.text in _TYPES:
                type_name = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    return type_name, name


def _parse_interface(p: _Tok, visibility: str = "") -> InterfaceDef:
    sp = p.span()
    p.eat_kw("interface")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.LBRACE)
    methods: list[str] = []
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        if p.at_kw("public", "private", "protected", "module"):
            p.eat(TokenKind.KEYWORD)
        if p.cur().text in _TYPES and p.peek(1).kind != TokenKind.LPAREN:
            p.eat(TokenKind.KEYWORD, TokenKind.IDENT)
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat(TokenKind.LPAREN)
        if not p.at(TokenKind.RPAREN):
            _parse_param(p)
            while p.at(TokenKind.COMMA):
                p.eat(TokenKind.COMMA)
                _parse_param(p)
        p.eat(TokenKind.RPAREN)
        methods.append(mname)
    p.eat(TokenKind.RBRACE)
    return InterfaceDef(span=sp, name=name, methods=methods, visibility=visibility)


def _parse_class(p: _Tok, visibility: str = "") -> ClassDef:
    sp = p.span()
    sealed = False
    if p.at_kw("sealed"):
        sealed = True
        p.eat_kw("sealed")
    p.eat_kw("class")
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    bases: list[str] = []
    if p.at_kw("inherits", "super"):
        p.eat(TokenKind.KEYWORD)
        bases.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
    if p.at_kw("implements"):
        p.eat_kw("implements")
        bases.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
        while p.at(TokenKind.COMMA):
            p.eat(TokenKind.COMMA)
            bases.append(p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text)
    p.eat(TokenKind.LBRACE)
    fields: list[FieldDecl] = []
    methods: list[MethodDef] = []
    while not p.at(TokenKind.RBRACE):
        if p.at(TokenKind.BLANK):
            p.eat(TokenKind.BLANK)
            continue
        if p.at(TokenKind.COMMENT):
            p.eat(TokenKind.COMMENT)
            continue
        access = "public"
        if p.at_kw("public", "private", "protected", "module"):
            access = p.eat(TokenKind.KEYWORD).text
        # constructor
        if p.cur().text == name and p.peek(1).kind == TokenKind.LPAREN:
            p.eat(TokenKind.IDENT, TokenKind.KEYWORD)
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
                    span=sp,
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
        if p.cur().text in _TYPES or (
            p.cur().kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
            and p.peek(1).kind != TokenKind.LPAREN
            and p.peek(1).text != name
        ):
            # method: [type] name (   OR field: type name
            if p.peek(1).kind == TokenKind.LPAREN:
                pass  # name is current
            else:
                type_name = p.eat(TokenKind.KEYWORD, TokenKind.IDENT).text
        mname = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        if p.at(TokenKind.LPAREN):
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
                    span=sp,
                    access=access,
                    name=mname,
                    params=[n for _, n in params],
                    body=body,
                    return_type=type_name,
                )
            )
        else:
            fields.append(FieldDecl(span=sp, access=access, type_name=type_name, name=mname))
    p.eat(TokenKind.RBRACE)
    return ClassDef(
        span=sp, name=name, bases=bases, fields=fields, methods=methods, visibility=visibility, sealed=sealed
    )


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
    elif p.at_kw(*_TYPES):
        dtype = p.eat(TokenKind.KEYWORD).text
        if p.at(TokenKind.LBRACK):
            p.eat(TokenKind.LBRACK)
            size = None
            if p.at(TokenKind.INT):
                size = int(p.eat(TokenKind.INT).text)
            p.eat(TokenKind.RBRACK)
            name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            p.eat(TokenKind.OP, text="=")
            value = _parse_expression(p)
            return ArrayDecl(span=sp, elem_type=dtype, name=name, size=size, value=value)
    elif p.at(TokenKind.IDENT) and p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD} and p.peek(2).text == "=":
        dtype = p.eat(TokenKind.IDENT).text
    name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
    p.eat(TokenKind.OP, text="=")
    value = _parse_expression(p)
    return AssignStmt(
        span=sp, name=name, value=value, declare_type=dtype, is_const=is_const, is_fix=is_fix
    )


def _parse_statement(p: _Tok):
    sp = p.span()
    if p.at(TokenKind.BLANK):
        t = p.eat(TokenKind.BLANK)
        return BlankStmt(span=Span(t.line, t.column))
    if p.at(TokenKind.COMMENT):
        t = p.eat(TokenKind.COMMENT)
        return CommentStmt(span=Span(t.line, t.column), text=t.text)
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
    if p.at_kw("loop"):
        return _parse_loop(p)
    if p.at_kw("var", "const", "fix", *_TYPES):
        return _parse_decl(p)
    # Typed named decl: Type name =
    if (
        p.at(TokenKind.IDENT)
        and p.peek(1).kind in {TokenKind.IDENT, TokenKind.KEYWORD}
        and p.peek(2).text == "="
    ):
        return _parse_decl(p)
    # this.name = expr
    if p.at_kw("this") and p.peek(1).kind == TokenKind.DOT:
        # Parse as member then optional assign
        left = _parse_expression(p)
        if p.at(TokenKind.OP, text="="):
            p.eat(TokenKind.OP, text="=")
            right = _parse_expression(p)
            if isinstance(left, Member) and isinstance(left.object, Identifier) and left.object.name == "self":
                return AssignStmt(span=sp, name=f"self.{left.name}", value=right)
            return AssignStmt(span=sp, name=_expr_to_lvalue(left), value=right)
        return ExprStmt(span=sp, expr=left)
    # name = / += / ++
    if p.at(TokenKind.IDENT) or (p.at(TokenKind.KEYWORD) and p.cur().text not in {
        "if", "unless", "loop", "print", "return", "pass", "break", "continue", "else",
        "function", "class", "interface", "import",
    }):
        if p.peek(1).text in {"=", "+=", "-=", "*=", "/=", "++", "--"}:
            name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
            op = p.eat(TokenKind.OP).text
            if op in {"++", "--"}:
                return AugAssignStmt(span=sp, name=name, op=op, value=None)
            if op != "=":
                return AugAssignStmt(span=sp, name=name, op=op, value=_parse_expression(p))
            return AssignStmt(span=sp, name=name, value=_parse_expression(p))
    return ExprStmt(span=sp, expr=_parse_expression(p))


def _expr_to_lvalue(expr: Expr) -> str:
    if isinstance(expr, Identifier):
        return expr.name
    if isinstance(expr, Member):
        return f"{_expr_to_lvalue(expr.object)}.{expr.name}"  # type: ignore[arg-type]
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


def _parse_block(p: _Tok) -> Block:
    sp = p.span()
    p.eat(TokenKind.LBRACE)
    stmts = []
    while not p.at(TokenKind.RBRACE):
        stmts.append(_parse_statement(p))
    p.eat(TokenKind.RBRACE)
    return Block(span=sp, statements=stmts)


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
        if p.at_kw(*_TYPES):
            p.eat(TokenKind.KEYWORD)
        var = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat_kw("in")
        it = _parse_expression(p)
        p.eat(TokenKind.RPAREN)
        body = _parse_block(p)
        return ForEachStmt(span=sp, var=var, iterable=it, body=body)

    commas = 0
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
        elif t.text == "," and depth == 0:
            commas += 1
        j += 1

    if commas >= 2:
        if p.at_kw("int", "float"):
            p.eat(TokenKind.KEYWORD)
        var = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        p.eat(TokenKind.OP, text="=")
        start = _parse_expression(p)
        p.eat(TokenKind.COMMA)
        p.eat(TokenKind.IDENT, TokenKind.KEYWORD)  # var in cond
        if p.at(TokenKind.LT, TokenKind.GT) or (p.at(TokenKind.OP) and p.cur().text in {"<=", ">=", "<", ">"}):
            p.eat(p.cur().kind)
        else:
            p.eat(TokenKind.OP)
        stop_expr = _parse_expression(p)
        p.eat(TokenKind.COMMA)
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


def _parse_expression(p: _Tok) -> Expr:
    return _parse_or(p)


def _parse_or(p: _Tok) -> Expr:
    left = _parse_and(p)
    while p.at_kw("or") or p.at(TokenKind.OP, text="||"):
        op = p.eat(TokenKind.KEYWORD, TokenKind.OP).text
        if op == "||":
            op = "or"
        right = _parse_and(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


def _parse_and(p: _Tok) -> Expr:
    left = _parse_not(p)
    while p.at_kw("and") or p.at(TokenKind.OP, text="&&"):
        op = p.eat(TokenKind.KEYWORD, TokenKind.OP).text
        if op == "&&":
            op = "and"
        right = _parse_not(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


def _parse_not(p: _Tok) -> Expr:
    if p.at_kw("not") or p.at(TokenKind.OP, text="!"):
        sp = p.span()
        op = p.eat(TokenKind.KEYWORD, TokenKind.OP).text
        if op == "!":
            op = "not"
        return UnaryOp(span=sp, op=op, operand=_parse_not(p))
    return _parse_cmp(p)


def _parse_cmp(p: _Tok) -> Expr:
    left = _parse_add(p)
    if p.at(TokenKind.LT, TokenKind.GT) or (
        p.at(TokenKind.OP) and p.cur().text in {"==", "!=", "<>", "<=", ">="}
    ):
        op = p.eat(p.cur().kind).text
        if op == "<>":
            op = "!="
        right = _parse_add(p)
        return BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


def _parse_add(p: _Tok) -> Expr:
    left = _parse_mul(p)
    while p.at(TokenKind.OP) and p.cur().text in {"+", "-"}:
        op = p.eat(TokenKind.OP).text
        right = _parse_mul(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


def _parse_mul(p: _Tok) -> Expr:
    left = _parse_unary(p)
    while p.at(TokenKind.OP) and p.cur().text in {"*", "/", "%"}:
        op = p.eat(TokenKind.OP).text
        right = _parse_unary(p)
        left = BinaryOp(span=left.span, op=op, left=left, right=right)
    return left


def _parse_unary(p: _Tok) -> Expr:
    if p.at(TokenKind.OP) and p.cur().text in {"+", "-"}:
        sp = p.span()
        op = p.eat(TokenKind.OP).text
        return UnaryOp(span=sp, op=op, operand=_parse_unary(p))
    return _parse_cast_postfix(p)


def _parse_cast_postfix(p: _Tok) -> Expr:
    if p.at(TokenKind.LPAREN) and p.peek(1).text in _TYPES and p.peek(2).kind == TokenKind.RPAREN:
        sp = p.span()
        p.eat(TokenKind.LPAREN)
        tn = p.eat(TokenKind.KEYWORD).text
        p.eat(TokenKind.RPAREN)
        return Cast(span=sp, type_name=tn, expr=_parse_cast_postfix(p))
    return _parse_postfix(p)


def _parse_postfix(p: _Tok) -> Expr:
    expr = _parse_primary(p)
    while True:
        if p.at(TokenKind.LPAREN):
            sp = expr.span
            p.eat(TokenKind.LPAREN)
            args: list[Expr] = []
            if not p.at(TokenKind.RPAREN):
                args.append(_parse_expression(p))
                while p.at(TokenKind.COMMA):
                    p.eat(TokenKind.COMMA)
                    args.append(_parse_expression(p))
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
        else:
            break
    return expr


def _parse_primary(p: _Tok) -> Expr:
    sp = p.span()
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
                elems.append(_parse_expression(p))
        p.eat(TokenKind.RBRACK)
        return ArrayLiteral(span=sp, elements=elems)
    if p.at(TokenKind.LPAREN):
        p.eat(TokenKind.LPAREN)
        e = _parse_expression(p)
        p.eat(TokenKind.RPAREN)
        return e
    if p.at(TokenKind.IDENT) or p.at(TokenKind.KEYWORD):
        name = p.eat(TokenKind.IDENT, TokenKind.KEYWORD).text
        return Identifier(span=sp, name=name)
    raise ParseError(f"Unexpected token {p.cur().text!r}", p.cur().line, p.cur().column)
