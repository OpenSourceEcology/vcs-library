from __future__ import annotations

import ast


_FORBIDDEN_EXPR_NAMES = {
    ast.Attribute: "attribute",
    ast.Await: "await",
    ast.Call: "call",
    ast.DictComp: "dict comprehension",
    ast.FormattedValue: "f-string",
    ast.GeneratorExp: "generator expression",
    ast.IfExp: "conditional expression",
    ast.JoinedStr: "f-string",
    ast.Lambda: "lambda",
    ast.ListComp: "list comprehension",
    ast.SetComp: "set comprehension",
    ast.Starred: "starred expression",
    ast.Yield: "yield",
    ast.YieldFrom: "yield",
}

_ALLOWED_EXPR_NODES = (
    ast.Add,
    ast.BitAnd,
    ast.BitOr,
    ast.BitXor,
    ast.BinOp,
    ast.Constant,
    ast.Dict,
    ast.Div,
    ast.FloorDiv,
    ast.Invert,
    ast.List,
    ast.Load,
    ast.LShift,
    ast.Mod,
    ast.Mult,
    ast.MatMult,
    ast.Name,
    ast.Pow,
    ast.RShift,
    ast.Set,
    ast.Store,
    ast.Sub,
    ast.Subscript,
    ast.Tuple,
    ast.UAdd,
    ast.USub,
    ast.UnaryOp,
)

_TOP_LEVEL_NAMES = {
    ast.AsyncFor: "async for",
    ast.AsyncFunctionDef: "async function definition",
    ast.AsyncWith: "async with",
    ast.AugAssign: "augmented assignment",
    ast.ClassDef: "class definition",
    ast.Delete: "delete",
    ast.For: "for",
    ast.FunctionDef: "function definition",
    ast.Global: "global",
    ast.If: "if",
    ast.Import: "import",
    ast.ImportFrom: "import",
    ast.Match: "match",
    ast.Nonlocal: "nonlocal",
    ast.Pass: "pass",
    ast.Raise: "raise",
    ast.Return: "return",
    ast.Try: "try",
    ast.While: "while",
    ast.With: "with",
}


def check_schema_source(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        line = exc.lineno or "unknown"
        return [f"syntax error on line {line}: {exc.msg}"]

    violations: list[str] = []
    schema_assignments: list[ast.expr] = []

    for index, statement in enumerate(tree.body):
        if _is_leading_docstring(statement, index):
            continue

        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                violations.extend(_check_expression(target))
                if _is_name(target, "SCHEMA"):
                    schema_assignments.append(statement.value)
            violations.extend(_check_expression(statement.value))
            continue

        if isinstance(statement, ast.AnnAssign):
            violations.extend(_check_expression(statement.target))
            violations.extend(_check_expression(statement.annotation))
            if statement.value is not None:
                violations.extend(_check_expression(statement.value))
            if _is_name(statement.target, "SCHEMA"):
                schema_assignments.append(statement.value)
            continue

        violations.append(
            f"{_top_level_name(statement)} is not allowed at top level on line {_line_number(statement)}"
        )
        if isinstance(statement, ast.Expr):
            violations.extend(_check_expression(statement.value))

    if not schema_assignments:
        violations.append("no SCHEMA assignment found")
    elif len(schema_assignments) > 1:
        violations.append(f"multiple SCHEMA assignments found: {len(schema_assignments)}")

    for value in schema_assignments:
        if not isinstance(value, ast.Dict):
            line = _line_number(value)
            violations.append(f"SCHEMA must be assigned a dict literal on line {line}")

    return violations


def _check_expression(expression: ast.AST | None) -> list[str]:
    if expression is None:
        return []

    violations = []
    for node in ast.walk(expression):
        forbidden_name = _forbidden_expression_name(node)
        if forbidden_name is not None:
            violations.append(f"{forbidden_name} is not allowed on line {_line_number(node)}")
            continue
        if isinstance(node, ast.Subscript) and not isinstance(node.ctx, ast.Load):
            violations.append(f"subscript is not allowed on line {_line_number(node)}")
            continue
        if not isinstance(node, _ALLOWED_EXPR_NODES):
            violations.append(f"{_expression_name(node)} is not allowed on line {_line_number(node)}")
    return violations


def _forbidden_expression_name(node: ast.AST) -> str | None:
    for node_type, name in _FORBIDDEN_EXPR_NAMES.items():
        if isinstance(node, node_type):
            return name
    return None


def _is_leading_docstring(statement: ast.stmt, index: int) -> bool:
    return (
        index == 0
        and isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _is_name(node: ast.AST | None, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _line_number(node: ast.AST | None) -> int | str:
    return getattr(node, "lineno", "unknown")


def _top_level_name(statement: ast.stmt) -> str:
    for node_type, name in _TOP_LEVEL_NAMES.items():
        if isinstance(statement, node_type):
            return name
    if isinstance(statement, ast.Expr):
        return "expression"
    return statement.__class__.__name__


def _expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Slice):
        return "slice"
    return node.__class__.__name__
