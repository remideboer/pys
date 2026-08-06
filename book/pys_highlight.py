"""Lightweight PYS highlighter — emits <span class="tok-*"> for CSS themes.

Token set aligned with pys-language/syntaxes/pys.tmLanguage.json (keywords,
types, modifiers, builtins, comments, strings + interpolation, numbers).
"""

from __future__ import annotations

import html
import re

# Modifiers / storage
MODIFIERS = frozenset(
    {
        "public",
        "private",
        "protected",
        "module",
        "global",
        "package",
        "const",
        "fix",
        "sealed",
        "abstract",
        "shared",
        "atomic",
        "var",
    }
)

# Control / declarations
KEYWORDS = frozenset(
    {
        "if",
        "else",
        "elseif",
        "while",
        "for",
        "loop",
        "func",
        "function",
        "class",
        "struct",
        "data",
        "entity",
        "identity",
        "lambda",
        "enum",
        "interface",
        "trait",
        "implements",
        "inherits",
        "uses",
        "requires",
        "return",
        "repeat",
        "times",
        "import",
        "from",
        "all",
        "break",
        "continue",
        "pass",
        "unless",
        "switch",
        "case",
        "default",
        "not",
        "and",
        "or",
        "xor",
        "shift",
        "left",
        "right",
        "this",
        "super",
        "tasks",
        "task",
        "await",
        "propagate",
        "nullable",
        "in",
        "as",
        "new",
    }
)

TYPES = frozenset(
    {
        "int",
        "float",
        "char",
        "bool",
        "string",
        "str",
        "void",
        "list",
        "dict",
        "tuple",
        "set",
        "byte",
        "nibble",
        "int16",
        "int32",
        "int64",
        "dword",
        "result",
        "nullable",
    }
)

CONSTANTS = frozenset({"true", "false", "null"})
BUILTINS = frozenset(
    {
        "print",
        "len",
        "range",
        "str",
        "int",
        "float",
        "bool",
        "ok",
        "err",
        "parseFloat",
        "parseInt",
        "input",
    }
)

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER = re.compile(
    r"(?:0[bB][01]+(?:_[01]+)*|0[xX][0-9A-Fa-f]+(?:_[0-9A-Fa-f]+)*|\d+\.\d+|\d+(?:_\d+)*)"
)
_OP = re.compile(
    r"(?:\+\+|--|<<<|>>>|<<|>>|=>|\*\*|//|<=|>=|==|!=|<>|[+\-*/%!=<>&|^~])"
)


def _span(kind: str, text: str) -> str:
    return f'<span class="tok-{kind}">{html.escape(text)}</span>'


def highlight_pys(source: str) -> str:
    """Return HTML fragment (no wrapping <pre>) for a PYS source string."""
    out: list[str] = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        # Block comment ## ... /#
        if source.startswith("##", i):
            end = source.find("/#", i + 2)
            if end < 0:
                out.append(_span("comment", source[i:]))
                break
            out.append(_span("comment", source[i : end + 2]))
            i = end + 2
            continue

        # Line comment # (but not #s{ typed interp or # alone starting interp)
        if ch == "#":
            # typed interpolation starts as #s{ #i{ etc — handled inside strings
            # bare # comment to EOL when not followed by letter+{
            rest = source[i + 1 : i + 3]
            if len(source) > i + 2 and source[i + 1] in "sficbo" and source[i + 2] == "{":
                # stray typed interp outside string — still highlight
                j = i + 3
                depth = 1
                while j < n and depth:
                    if source[j] == "{":
                        depth += 1
                    elif source[j] == "}":
                        depth -= 1
                    j += 1
                out.append(_span("interp", source[i:j]))
                i = j
                continue
            end = source.find("\n", i)
            if end < 0:
                out.append(_span("comment", source[i:]))
                break
            out.append(_span("comment", source[i:end]))
            i = end
            continue

        # Strings
        if ch in "\"'":
            quote = ch
            j = i + 1
            parts: list[str] = [_span("string", quote)]
            while j < n:
                c = source[j]
                if c == "\\" and j + 1 < n:
                    parts.append(_span("string", source[j : j + 2]))
                    j += 2
                    continue
                if c == quote:
                    parts.append(_span("string", quote))
                    j += 1
                    break
                # plain {expr} or #t{expr} interpolation
                if c == "#" and j + 2 < n and source[j + 1] in "sficbo" and source[j + 2] == "{":
                    k = j + 3
                    depth = 1
                    while k < n and depth:
                        if source[k] == "{":
                            depth += 1
                        elif source[k] == "}":
                            depth -= 1
                        k += 1
                    parts.append(_span("interp", source[j:k]))
                    j = k
                    continue
                if c == "{":
                    k = j + 1
                    depth = 1
                    while k < n and depth:
                        if source[k] == "{":
                            depth += 1
                        elif source[k] == "}":
                            depth -= 1
                        k += 1
                    parts.append(_span("interp", source[j:k]))
                    j = k
                    continue
                # accumulate plain string chars
                start = j
                while j < n:
                    c2 = source[j]
                    if c2 == "\\" or c2 == quote or c2 == "{" or (
                        c2 == "#"
                        and j + 2 < n
                        and source[j + 1] in "sficbo"
                        and source[j + 2] == "{"
                    ):
                        break
                    j += 1
                if j > start:
                    parts.append(_span("string", source[start:j]))
            out.extend(parts)
            i = j
            continue

        # Char literal 'x'
        # (already handled as quote above for single quote — OK for book)

        # Whitespace
        if ch.isspace():
            out.append(html.escape(ch))
            i += 1
            continue

        # Numbers
        m = _NUMBER.match(source, i)
        if m:
            out.append(_span("number", m.group(0)))
            i = m.end()
            continue

        # Identifiers / keywords
        m = _IDENT.match(source, i)
        if m:
            word = m.group(0)
            if word in MODIFIERS:
                out.append(_span("mod", word))
            elif word in KEYWORDS:
                out.append(_span("kw", word))
            elif word in TYPES:
                out.append(_span("type", word))
            elif word in CONSTANTS:
                out.append(_span("const", word))
            elif word in BUILTINS:
                out.append(_span("builtin", word))
            elif word[:1].isupper():
                out.append(_span("typename", word))
            else:
                out.append(_span("ident", word))
            i = m.end()
            continue

        # Operators
        m = _OP.match(source, i)
        if m:
            out.append(_span("op", m.group(0)))
            i = m.end()
            continue

        out.append(html.escape(ch))
        i += 1

    return "".join(out)


_CODE_BLOCK = re.compile(
    r'(<pre><code class="language-pys">)(.*?)(</code></pre>)',
    re.DOTALL,
)


def highlight_html_document(doc: str) -> str:
    """Replace language-pys fenced blocks inside an HTML document."""

    def repl(match: re.Match[str]) -> str:
        prefix, body, suffix = match.groups()
        source = html.unescape(body)
        # Drop a single trailing newline often added by markdown
        if source.endswith("\n"):
            source = source[:-1]
        highlighted = highlight_pys(source)
        return f'{prefix}{highlighted}{suffix}'

    return _CODE_BLOCK.sub(repl, doc)
