"""Small, non-evaluating arithmetic parser for deterministic checks."""
from __future__ import annotations

import ast
import math
import operator

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.BitXor: operator.xor,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_NODES = 64
_MAX_ABS_RESULT = 1e100


def safe_eval_arithmetic(expression: str) -> float:
    """Evaluate finite arithmetic without Python eval; ``^`` keeps legacy XOR semantics."""
    tree = ast.parse(str(expression), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
        raise ValueError("arithmetic expression too large")

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            value = float(node.value)
            if not math.isfinite(value):
                raise ValueError("non-finite number")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return float(_UNARYOPS[type(node.op)](visit(node.operand)))
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left = visit(node.left)
            right = visit(node.right)
            if isinstance(node.op, ast.BitXor):
                if not left.is_integer() or not right.is_integer():
                    raise ValueError("bitwise XOR requires integer operands")
                value = float(_BINOPS[type(node.op)](int(left), int(right)))
            else:
                value = float(_BINOPS[type(node.op)](left, right))
            if not math.isfinite(value) or abs(value) > _MAX_ABS_RESULT:
                raise ValueError("arithmetic result outside safety bound")
            return value
        raise ValueError(f"unsupported arithmetic node: {type(node).__name__}")

    return visit(tree)
