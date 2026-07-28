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


def _translate_string_literal(value: str) -> str:
    value = value.strip()
    if value.startswith(("f'", 'f"', "F'", 'F"')):
        return value
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        if "{" in value and "}" in value:
            return f"f{value}"
    return value


def _translate_cast(type_name: str, expr: str) -> str:
    cast_map = {"int": "int", "float": "float", "char": "str", "string": "str"}
    return f"{cast_map[type_name]}({_translate_string_literal(expr.strip())})"


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


def _translate_import_from(match: Match[str]) -> str:
    module = match.group("module").strip()
    module = re.sub(r"\.pys$", "", module)
    return f"from {module} import {match.group('name')}"


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
    return f"{name} = {_translate_string_literal(expr.strip())}"


def _translate_function(match: Match[str]) -> str:
    name = match.group("name")
    args = _strip_type_annotation(match.group("args").strip())
    return f"def {name}({args}):"


def _translate_if(match: Match[str]) -> str:
    return f"if {_normalize_bool_expr(match.group('cond').strip())}:"


def _translate_elif(match: Match[str]) -> str:
    return f"elif {_normalize_bool_expr(match.group('cond').strip())}:"


def _translate_unless(match: Match[str]) -> str:
    return f"if not ({_normalize_bool_expr(match.group('cond').strip())}):"


def _translate_return(match: Match[str]) -> str:
    return f"return {match.group('expr').strip()}"


def _translate_print(match: Match[str]) -> str:
    expr = match.group('expr').strip()
    return f"print({_translate_string_literal(expr)})"


def _translate_assignment(match: Match[str]) -> str:
    name = match.group('name')
    expr = match.group('expr').strip()
    return f"{name} = {_translate_string_literal(expr)}"


LANGUAGE = LanguageSpec()

LANGUAGE.add("let_decl", "let {name} = {expr}", "{name} = {expr}")
LANGUAGE.add_regex(
    "typed_decl",
    r"(?P<type>int|float|char|string)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {match.group('expr').strip()}"
)
LANGUAGE.add_regex(
    "object_typed_decl",
    r"(?P<type>[A-Za-z_]\w*)\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {match.group('expr').strip()}"
)
LANGUAGE.add_regex(
    "typed_array",
    r"(?P<type>int|float|char|string)\[(?P<size>\d+)\]\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    lambda match: f"{match.group('name')} = {match.group('expr').strip()}"
)
LANGUAGE.add_regex(
    "import_from",
    r"import\s+(?P<name>[A-Za-z_]\w*)\s+from\s+(?P<module>.+)",
    _translate_import_from,
)
LANGUAGE.add_regex(
    "import",
    r"import\s+(?P<module>.+)",
    lambda match: f"import {match.group('module').strip()}",
)
LANGUAGE.add_regex(
    "loop_general",
    r"loop\s*\(\s*(?P<init>[^,]+?)\s*,\s*(?P<cond>[^,]+?)\s*,\s*(?P<step>[^)]+?)\s*\)",
    lambda match: _translate_loop(match.group("init"), match.group("cond"), match.group("step")),
)
LANGUAGE.add_regex(
    "loop_condition",
    r"loop\s*\(\s*(?P<cond>.+?)\s*\)",
    _translate_if,
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
    "class_super",
    r"class\s+(?P<name>[A-Za-z_]\w*)\s+super\s+(?P<super>[A-Za-z_]\w*)",
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
    r"(?:public|private|protected|module)\s*(?:(?P<rtype>int|float|char|string)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)",
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
    r"\(\s*(?P<type>int|float|char|string)\s*\)\s*(?P<expr>.+)",
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
    lambda match: f"print({match.group('expr')})",
)
LANGUAGE.add_regex(
    "func_def",
    r"func\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*:\s*",
    _translate_function,
)
LANGUAGE.add_regex(
    "let_simple",
    r"let\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+)",
    _translate_assignment,
)
LANGUAGE.add_regex(
    "class_simple",
    r"class\s+(?P<name>[A-Za-z_]\w*)",
    lambda match: f"class {match.group('name')}:"
)
