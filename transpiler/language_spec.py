from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Pattern, Match


@dataclass
class SyntaxRule:
    name: str
    pattern: Pattern[str]
    translator: Callable[[Match[str]], str]


class LanguageSpec:
    def __init__(self) -> None:
        self.rules: List[SyntaxRule] = []

    def add(self, name: str, template: str, target: str) -> None:
        regex = self._template_to_regex(template)

        def translator(match: Match[str]) -> str:
            result = target
            for key, value in match.groupdict().items():
                replacement = value.strip()
                if key == "expr":
                    replacement = _translate_string_literal(replacement)
                result = result.replace(f"{{{key}}}", replacement)
            return result

        self.rules.append(SyntaxRule(name, regex, translator))

    def add_regex(self, name: str, pattern: str, translator: Callable[[Match[str]], str]) -> None:
        full_pattern = re.compile(f"^{pattern}$")
        self.rules.append(SyntaxRule(name, full_pattern, translator))

    def translate_line(self, line: str) -> str:
        normalized = line.strip()
        for rule in self.rules:
            match = rule.pattern.fullmatch(normalized)
            if match:
                return rule.translator(match)
        return normalized

    @staticmethod
    def _template_to_regex(template: str) -> Pattern[str]:
        escaped = ""
        cursor = 0
        for match in re.finditer(r"\{([A-Za-z_]\w*)\}", template):
            escaped += re.escape(template[cursor:match.start()])
            escaped += f"(?P<{match.group(1)}>.+?)"
            cursor = match.end()
        escaped += re.escape(template[cursor:])
        return re.compile(f"^{escaped}$")


def _normalize_bool_expr(expr: str) -> str:
    expr = expr.strip()
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"(?<![=!<>])!(?![=])", "not ", expr)
    return expr


def _strip_type_annotation(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    # Strip a leading type annotation for each comma-separated parameter.
    parts = [p.strip() for p in text.split(",")]
    stripped_parts: list[str] = []
    for part in parts:
        stripped = re.sub(r"^(int|float|char|string|bool)\s+", "", part)
        stripped_parts.append(stripped)
    return ", ".join(stripped_parts)


def _strip_optional_parens(value: str) -> str:
    value = value.strip()
    if value.startswith("(") and value.endswith(")") and len(value) >= 2:
        return value[1:-1].strip()
    return value


def _translate_string_literal(value: str) -> str:
    value = _strip_optional_parens(value.strip())
    if value.startswith(("f'", 'f"', "F'", 'F"')):
        return value
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        if "{" in value and "}" in value:
            return f"f{value}"
    return value


def _translate_cast(type_name: str, expr: str) -> str:
    cast_map = {"int": "int", "float": "float", "char": "str", "string": "str", "bool": "bool"}
    rewritten = _rewrite_plus_expr(expr.strip())
    if type_name in cast_map:
        return f"{cast_map[type_name]}({rewritten})"
    # Reference cast (class/interface): runtime value unchanged; static type is the cast type.
    return rewritten


def _translate_array_loop(match: Match[str]) -> str:
    array_name = match.group("array")
    fn_name = match.group("fn")
    # Ensure the loop body is executed for side effects (e.g. print).
    return f"list(map({fn_name}, {array_name}))"


def _split_top_level_plus(expr: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    quote = ""
    i = 0
    while i < len(expr):
        ch = expr[i]
        if in_string:
            current.append(ch)
            if ch == "\\" and i + 1 < len(expr):
                current.append(expr[i + 1])
                i += 2
                continue
            if ch == quote:
                in_string = False
            i += 1
            continue
        if ch in {'"', "'"}:
            in_string = True
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch == "(":
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch == ")":
            depth = max(depth - 1, 0)
            current.append(ch)
            i += 1
            continue
        if ch == "+" and depth == 0:
            if i + 1 < len(expr) and expr[i + 1] == "+":
                current.append("++")
                i += 2
                continue
            parts.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _plus_term_kind(term: str) -> str:
    term = term.strip()
    cast = re.match(r"^\(\s*(?P<type>int|float|char|string|bool|[A-Za-z_]\w*)\s*\)", term)
    if cast:
        t = cast.group("type")
        if t in {"string", "char"}:
            return "string"
        if t in {"int", "float", "bool"}:
            return "number"
        return "unknown"
    if (term.startswith('"') and term.endswith('"')) or (term.startswith("'") and term.endswith("'")):
        return "string"
    if re.fullmatch(r"\d+(?:\.\d+)?", term):
        return "number"
    if term in {"true", "false", "True", "False", "null", "None"}:
        return "number"
    return "unknown"


def _translate_plus_term(term: str) -> str:
    term = term.strip()
    cast = re.fullmatch(r"\(\s*(?P<type>[A-Za-z_]\w*)\s*\)\s*(?P<expr>.+)", term)
    if cast:
        return _translate_cast(cast.group("type"), cast.group("expr"))
    if term.startswith("(") and term.endswith(")"):
        inner = term[1:-1].strip()
        if _split_top_level_plus(inner) != [inner]:
            return f"({_rewrite_plus_expr(inner)})"
    return _translate_string_literal(term)


def _rewrite_plus_expr(expr: str) -> str:
    """Left-associative +: numeric until a string appears, then concatenate with str()."""
    expr = expr.strip()
    if not expr:
        return expr

    parts = _split_top_level_plus(expr)
    if len(parts) <= 1:
        return _translate_plus_term(expr)

    result = _translate_plus_term(parts[0])
    mode = "string" if _plus_term_kind(parts[0]) == "string" else "number"

    for part in parts[1:]:
        kind = _plus_term_kind(part)
        translated = _translate_plus_term(part)
        if mode == "number" and kind != "string":
            result = f"{result} + {translated}"
            continue
        if mode == "number" and kind == "string":
            result = f"str({result}) + {translated}"
            mode = "string"
            continue
        if kind == "string":
            result = f"{result} + {translated}"
        else:
            result = f"{result} + str({translated})"
        mode = "string"
    return result


def _parse_loop_init(init: str) -> tuple[str, str]:
    init = init.strip()
    init = _strip_type_annotation(init)
    match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<value>.+)", init)
    if not match:
        raise ValueError(f"Unsupported loop initialization: {init}")
    return match.group("name"), match.group("value").strip()


def _parse_loop_condition(cond: str) -> tuple[str, str, str]:
    cond = cond.strip()
    match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*(?P<op><=|>=|<|>)\s*(?P<bound>.+)", cond)
    if not match:
        raise ValueError(f"Unsupported loop condition: {cond}")
    return match.group("name"), match.group("op"), match.group("bound").strip()


def _parse_loop_step(step: str) -> tuple[str, int, str]:
    step = step.strip()
    match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*\+\+", step)
    if match:
        return match.group("name"), 1, "1"
    match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*--", step)
    if match:
        return match.group("name"), -1, "-1"
    match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*\+=\s*(?P<value>.+)", step)
    if match:
        return match.group("name"), 1, match.group("value").strip()
    match = re.fullmatch(r"(?P<name>[A-Za-z_]\w*)\s*-\=\s*(?P<value>.+)", step)
    if match:
        return match.group("name"), -1, match.group("value").strip()
    raise ValueError(f"Unsupported loop step: {step}")


def _translate_loop(init: str, cond: str, step: str) -> str:
    var, start = _parse_loop_init(init)
    cond_var, op, bound = _parse_loop_condition(cond)
    step_var, step_sign, step_value = _parse_loop_step(step)

    if var != cond_var or var != step_var:
        raise ValueError("Loop variable must be the same in init, condition, and step.")

    if op == "<":
        stop = bound
    elif op == "<=":
        stop = f"({bound}) + 1"
    elif op == ">":
        stop = bound
    else:  # >=
        stop = f"({bound}) - 1"

    if step_value == "1" and step_sign == 1:
        return f"for {var} in range({start}, {stop}):"
    if step_value == "-1" and step_sign == -1:
        return f"for {var} in range({start}, {stop}, -1):"

    step_expr = step_value if step_sign == 1 else f"-({step_value})"
    return f"for {var} in range({start}, {stop}, {step_expr}):"


def _translate_step(step: str) -> str:
    if step.endswith("++"):
        name = step[:-2].strip()
        return f"{name} += 1"
    if step.endswith("--"):
        name = step[:-2].strip()
        return f"{name} -= 1"
    return step


def _normalize_module_ref(module: str) -> str:
    module = module.strip()
    module = re.sub(r"\.pys$", "", module)
    module = module.replace("\\", "/").replace("/", ".")
    return module


def _translate_import_from(match: Match[str]) -> str:
    return f"from {_normalize_module_ref(match.group('module'))} import {match.group('name')}"


def _translate_import_all_from(match: Match[str]) -> str:
    # Placeholder; Parser rewrites this using real module exports when a source path is known.
    return f"from {_normalize_module_ref(match.group('module'))} import *"


def _translate_import_module(match: Match[str]) -> str:
    # Placeholder; Parser rewrites this to import visible names when a source path is known.
    return f"from {_normalize_module_ref(match.group('module'))} import *"


def _default_value_for_type(type_name: str) -> str:
    defaults = {
        "int": "0",
        "float": "0.0",
        "char": "''",
        "string": "''",
        "bool": "False",
    }
    return defaults.get(type_name, "None")


def _raise_missing_member_access_modifier(match: Match[str]) -> str:
    raise ValueError(
        "Class member declarations require an access modifier: public/private/protected/module."
    )


def _translate_member_decl(match: Match[str]) -> str:
    name = match.group("name")
    expr = match.group("expr")
    if expr is None:
        return f"{name} = {_default_value_for_type(match.group('type'))}"
    return f"{name} = {_rewrite_plus_expr(expr.strip())}"


def _translate_function(match: Match[str]) -> str:
    name = match.group("name")
    args = _strip_type_annotation(match.group("args").strip())
    return f"def {name}({args}):"


def _translate_if(match: Match[str]) -> str:
    return f"if {_normalize_bool_expr(match.group('cond').strip())}:"


def _translate_while(match: Match[str]) -> str:
    return f"while {_normalize_bool_expr(match.group('cond').strip())}:"


def _translate_elif(match: Match[str]) -> str:
    return f"elif {_normalize_bool_expr(match.group('cond').strip())}:"


def _translate_unless(match: Match[str]) -> str:
    return f"if not ({_normalize_bool_expr(match.group('cond').strip())}):"


def _translate_return(match: Match[str]) -> str:
    return f"return {match.group('expr').strip()}"


def _translate_print(match: Match[str]) -> str:
    expr = match.group('expr').strip()
    expr = _strip_optional_parens(expr)
    return f"print({_rewrite_plus_expr(expr)})"


def _translate_const_decl(match: Match[str]) -> str:
    name = match.group("name")
    expr = match.group("expr").strip()
    return f"{name} = {_rewrite_plus_expr(expr)}"


def _translate_assignment(match: Match[str]) -> str:
    name = match.group("name")
    expr = match.group("expr").strip()
    return f"{name} = {_rewrite_plus_expr(expr)}"


LANGUAGE = LanguageSpec()

LANGUAGE.add_regex(
    "visible_const_decl",
    r"(?:global|package|module)\s+const\s+(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    _translate_const_decl,
)
LANGUAGE.add_regex(
    "const_decl",
    r"const\s+(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    _translate_const_decl,
)
LANGUAGE.add_regex(
    "var_decl",
    r"var\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {_rewrite_plus_expr(match.group('expr').strip())}",
)
LANGUAGE.add_regex(
    "typed_decl",
    r"(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {_rewrite_plus_expr(match.group('expr').strip())}",
)
LANGUAGE.add_regex(
    "object_typed_decl",
    r"(?P<type>[A-Za-z_]\w*)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {_rewrite_plus_expr(match.group('expr').strip())}",
)
LANGUAGE.add_regex(
    "typed_array_unsized",
    r"(?P<type>int|float|char|string|bool)\[\]\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {_rewrite_plus_expr(match.group('expr').strip())}",
)
LANGUAGE.add_regex(
    "typed_array",
    r"(?P<type>int|float|char|string|bool)\[(?P<size>\d+)\]\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {_rewrite_plus_expr(match.group('expr').strip())}",
)
LANGUAGE.add_regex(
    "array_loop",
    r"(?P<array>[A-Za-z_]\w*)\s*\.\s*loop\s*\(\s*(?P<fn>[A-Za-z_]\w*)\s*\)",
    _translate_array_loop,
)
LANGUAGE.add_regex(
    "import_all_from",
    r"import\s+all\s+from\s+(?P<module>.+)",
    _translate_import_all_from,
)
LANGUAGE.add_regex(
    "import_from",
    r"import\s+(?P<name>[A-Za-z_]\w*)\s+from\s+(?P<module>.+)",
    _translate_import_from,
)
LANGUAGE.add_regex(
    "import_module",
    r"import\s+(?P<module>.+)",
    _translate_import_module,
)
LANGUAGE.add_regex(
    "visible_function_def",
    r"(?:global|package|module)\s+function(?:\s+(?:(?P<rtype>int|float|char|string)\s+))?\s*(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?::\s*)?",
    _translate_function,
)
LANGUAGE.add_regex(
    "visible_interface_def",
    r"(?:global|package|module)\s+interface\s+(?P<name>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}(ABC):",
)
LANGUAGE.add_regex(
    "visible_class_inherits_implements",
    r"(?:global|package|module)\s+class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<parent>[A-Za-z_]\w*)\s+implements\s+(?P<interfaces>.+)",
    lambda match: (
        f"class {match.group('name')}({match.group('parent')}, "
        + ", ".join(part.strip() for part in match.group("interfaces").split(",") if part.strip())
        + "):"
    ),
)
LANGUAGE.add_regex(
    "visible_class_implements",
    r"(?:global|package|module)\s+class\s+(?P<name>[A-Za-z_]\w*)\s+implements\s+(?P<interfaces>.+)",
    lambda match: (
        f"class {match.group('name')}("
        + ", ".join(part.strip() for part in match.group("interfaces").split(",") if part.strip())
        + "):"
    ),
)
LANGUAGE.add_regex(
    "visible_class_inherits",
    r"(?:global|package|module)\s+class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<super>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}({match.group('super')}):",
)
LANGUAGE.add_regex(
    "visible_class",
    r"(?:global|package|module)\s+class\s+(?P<name>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}:",
)
LANGUAGE.add_regex(
    "loop_general",
    r"loop\s*\(\s*(?P<init>[^,]+?)\s*,\s*(?P<cond>[^,]+?)\s*,\s*(?P<step>[^)]+?)\s*\)",
    lambda match: _translate_loop(match.group("init"), match.group("cond"), match.group("step")),
)
LANGUAGE.add_regex(
    "loop_condition",
    r"loop\s*\(\s*(?P<cond>.+?)\s*\)",
    _translate_while,
)
LANGUAGE.add_regex(
    "unless",
    r"unless\s*\(\s*(?P<cond>.+?)\s*\)",
    _translate_unless,
)
LANGUAGE.add_regex(
    "else_if",
    r"else\s+if\s*\(\s*(?P<cond>.+?)\s*\)",
    _translate_elif,
)
LANGUAGE.add_regex(
    "if",
    r"if\s*\(\s*(?P<cond>.+?)\s*\)",
    _translate_if,
)
LANGUAGE.add("else", "else", "else:")
LANGUAGE.add_regex(
    "interface_def",
    r"interface\s+(?P<name>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}(ABC):",
)
LANGUAGE.add_regex(
    "class_inherits_implements",
    r"class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<parent>[A-Za-z_]\w*)\s+implements\s+(?P<interfaces>.+)",
    lambda match: (
        f"class {match.group('name')}({match.group('parent')}, "
        + ", ".join(part.strip() for part in match.group("interfaces").split(",") if part.strip())
        + "):"
    ),
)
LANGUAGE.add_regex(
    "class_implements",
    r"class\s+(?P<name>[A-Za-z_]\w*)\s+implements\s+(?P<interfaces>.+)",
    lambda match: (
        f"class {match.group('name')}("
        + ", ".join(part.strip() for part in match.group("interfaces").split(",") if part.strip())
        + "):"
    ),
)
LANGUAGE.add_regex(
    "class_inherits",
    r"class\s+(?P<name>[A-Za-z_]\w*)\s+(?:inherits|super)\s+(?P<super>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}({match.group('super')}):",
)
LANGUAGE.add("class", "class {name}", "class {name}:")
LANGUAGE.add_regex(
    "member_decl_missing_modifier",
    r"(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)$",
    _raise_missing_member_access_modifier,
)
LANGUAGE.add_regex(
    "access_member_decl",
    r"(?:private|protected|module|public)\s+(?P<type>int|float|char|string|bool)\s+(?P<name>[A-Za-z_]\w*)(?:\s*=\s*(?P<expr>.+))?",
    _translate_member_decl,
)
LANGUAGE.add_regex(
    "method_def",
    r"(?:public|private|protected|module)\s+(?:(?P<rtype>int|float|char|string|bool)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)",
    _translate_function,
)
LANGUAGE.add_regex(
    "function_def",
    r"function(?:\s+(?:(?P<rtype>int|float|char|string)\s+))?\s*(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?::\s*)?",
    _translate_function,
)
LANGUAGE.add_regex(
    "func_def",
    r"func\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?::\s*)?",
    _translate_function,
)
LANGUAGE.add_regex(
    "return",
    r"return\s+(?P<expr>.+)",
    _translate_return,
)
LANGUAGE.add_regex(
    "print",
    r"print\s+(?P<expr>.+)",
    _translate_print,
)
LANGUAGE.add_regex(
    "cast",
    r"\(\s*(?P<type>[A-Za-z_]\w*)\s*\)\s*(?P<expr>.+)",
    lambda match: _translate_cast(match.group("type"), match.group("expr")),
)
LANGUAGE.add_regex(
    "assignment",
    r"(?P<name>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*(?<![=!<>])=\s*(?P<expr>.+)",
    _translate_assignment,
)
LANGUAGE.add_regex(
    "increment",
    r"(?P<name>[A-Za-z_]\w*)\+\+",
    lambda match: f"{match.group('name')} += 1",
)
LANGUAGE.add_regex(
    "decrement",
    r"(?P<name>[A-Za-z_]\w*)--",
    lambda match: f"{match.group('name')} -= 1",
)
LANGUAGE.add_regex(
    "super_call",
    r"super\s*\((?P<args>.*)\)",
    lambda match: f"super().__init__({match.group('args').strip()})",
)
LANGUAGE.add_regex(
    "super_method",
    r"super\.(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*)\)",
    lambda match: f"super().{match.group('name')}({match.group('args').strip()})",
)
LANGUAGE.add("pass", "pass", "pass")
LANGUAGE.add("break", "break", "break")
LANGUAGE.add("continue", "continue", "continue")


# Backwards compatibility for the original teaching syntax patterns
LANGUAGE.add_regex(
    "if_then",
    r"if\s+(?P<cond>.+?)\s+then:\s*",
    lambda match: f"if {_normalize_bool_expr(match.group('cond').strip())}:"
)
LANGUAGE.add_regex(
    "elif_then",
    r"elif\s+(?P<cond>.+?)\s+then:\s*",
    lambda match: f"elif {_normalize_bool_expr(match.group('cond').strip())}:"
)
LANGUAGE.add_regex(
    "for_do",
    r"for\s+(?P<inner>.+?)\s+in\s+(?P<expr>.+?)\s+do:\s*",
    lambda match: f"for {match.group('inner')} in {match.group('expr')}:"
)
LANGUAGE.add_regex(
    "while_do",
    r"while\s+(?P<cond>.+?)\s+do:\s*",
    lambda match: f"while {match.group('cond').strip()}:"
)
LANGUAGE.add_regex(
    "repeat",
    r"repeat\s+(?P<count>.+?)\s+times:\s*",
    lambda match: f"for _ in range({match.group('count').strip()}):"
)
LANGUAGE.add_regex(
    "print_paren",
    r"print\s*\((?P<expr>.*)\)",
    lambda match: f"print({_rewrite_plus_expr(match.group('expr'))})",
)
LANGUAGE.add_regex(
    "func_def",
    r"func\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*:\s*",
    _translate_function,
)
LANGUAGE.add_regex(
    "var_simple",
    r"var\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    _translate_assignment,
)
LANGUAGE.add_regex(
    "class_simple",
    r"class\s+(?P<name>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}:"
)
