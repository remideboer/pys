"""Call-site argument binding: all-positional or all-named (never mixed)."""

from __future__ import annotations

from typing import Iterable, Literal, Sequence

from .ast_nodes import Expr, KeywordArg


CallArgMode = Literal["empty", "positional", "named"]


def _error(
    message: str,
    line: int = 1,
    column: int = 1,
    code_line: str = "",
    *,
    code: str | None = None,
    tips: list[str] | None = None,
) -> None:
    from .transpiler import TranspileError

    raise TranspileError(
        message,
        line,
        column,
        code_line,
        code=code,
        tips=tips,
    )


def _span_of(node: Expr | None, fallback_line: int = 1, fallback_col: int = 1) -> tuple[int, int]:
    if node is not None and node.span is not None:
        return node.span.line, node.span.column
    return fallback_line, fallback_col


def classify_call_args(
    args: Sequence[Expr],
    *,
    label: str = "call",
    line: int = 1,
    column: int = 1,
) -> CallArgMode:
    """Return the call style, or raise if positional and named are mixed."""
    if not args:
        return "empty"
    has_pos = any(not isinstance(a, KeywordArg) for a in args)
    has_named = any(isinstance(a, KeywordArg) for a in args)
    if has_pos and has_named:
        if not isinstance(args[0], KeywordArg):
            bad = next(a for a in args if isinstance(a, KeywordArg))
        else:
            bad = next(a for a in args if not isinstance(a, KeywordArg))
        bl, bc = _span_of(bad, line, column)
        _error(
            f"Cannot mix positional and named arguments in {label}. "
            f"Use only positional or only named arguments.",
            bl,
            bc,
            "argument",
            code="pys.call-arg-mix",
            tips=[
                "Write either `f(a, b)` or `f(x=a, y=b)` — not both in one call.",
            ],
        )
    return "named" if has_named else "positional"


def bind_call_arguments(
    args: Sequence[Expr],
    *,
    param_names: Sequence[str],
    defaults: Iterable[str] = (),
    label: str = "call",
    line: int = 1,
    column: int = 1,
) -> list[tuple[str, Expr | None]]:
    """Bind call args to parameter names in declaration order.

    - All positional or all named (mix rejected via ``classify_call_args``).
    - Named: names must match parameters; duplicates / unknowns rejected.
    - Missing parameters allowed only when listed in ``defaults``.
    """
    defaults_set = set(defaults)
    mode = classify_call_args(args, label=label, line=line, column=column)
    names = list(param_names)

    if mode == "empty":
        missing = [n for n in names if n not in defaults_set]
        if missing:
            _error(
                f"{label} missing argument(s): {', '.join(missing)}.",
                line,
                column,
                label,
                code="pys.call-arg-missing",
            )
        return [(n, None) for n in names]

    if mode == "positional":
        if len(args) > len(names):
            _error(
                f"{label} expects at most {len(names)} argument(s), got {len(args)}.",
                line,
                column,
                label,
                code="pys.call-arg-arity",
            )
        bound: list[tuple[str, Expr | None]] = []
        for i, name in enumerate(names):
            if i < len(args):
                bound.append((name, args[i]))
            elif name in defaults_set:
                bound.append((name, None))
            else:
                _error(
                    f"{label} missing argument(s): {name}.",
                    line,
                    column,
                    label,
                    code="pys.call-arg-missing",
                )
        return bound

    # named
    seen: dict[str, Expr] = {}
    for arg in args:
        assert isinstance(arg, KeywordArg)
        al, ac = _span_of(arg, line, column)
        if arg.name in seen:
            _error(
                f"Duplicate named argument '{arg.name}' in {label}.",
                al,
                ac,
                arg.name,
                code="pys.call-arg-duplicate",
            )
        if arg.name not in names:
            _error(
                f"Unknown named argument '{arg.name}' in {label}.",
                al,
                ac,
                arg.name,
                code="pys.call-arg-unknown",
                tips=[f"Expected parameter name(s): {', '.join(names) or '(none)'}."],
            )
        seen[arg.name] = arg.value

    missing = [n for n in names if n not in seen and n not in defaults_set]
    if missing:
        _error(
            f"{label} missing argument(s): {', '.join(missing)}.",
            line,
            column,
            label,
            code="pys.call-arg-missing",
        )
    return [(n, seen.get(n)) for n in names]


def pick_overload(
    overloads: Sequence[tuple[list[str], list[str]]],
    args: Sequence[Expr],
    *,
    label: str,
    line: int = 1,
    column: int = 1,
) -> tuple[list[str], list[str]]:
    """Choose a unique (param_names, param_types) overload for the call style."""
    mode = classify_call_args(args, label=label, line=line, column=column)
    if mode == "empty":
        matches = [o for o in overloads if len(o[0]) == 0]
    elif mode == "positional":
        matches = [o for o in overloads if len(o[0]) == len(args)]
    else:
        keys = {a.name for a in args if isinstance(a, KeywordArg)}
        matches = [o for o in overloads if set(o[0]) == keys]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        _error(
            f"No matching {label} for this argument list.",
            line,
            column,
            label,
            code="pys.call-arg-overload",
        )
    _error(
        f"Ambiguous {label} for this argument list.",
        line,
        column,
        label,
        code="pys.call-arg-overload",
    )
    raise AssertionError("unreachable")
