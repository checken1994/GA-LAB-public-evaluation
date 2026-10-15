"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V14 — Deterministic Math Evaluator (NO LLM).

Tại sao tồn tại:
    LLM không đáng tin cậy cho phép tính sơ đẳng — có thể nói 2+2=5.
    Module này tính toán trực tiếp bằng Python AST, đảm bảo:
      - Cộng/trừ/nhân/chia (int + float)
      - Phép modulo %, lũy thừa **, chia nguyên //
      - Parentheses
      - Hàm: sqrt, abs, gcd, lcm, factorial (!), log, ln, sin, cos, tan, exp
      - Hằng số: pi, e, tau
      - So sánh: ==, !=, <, >, <=, >=
      - Phần trăm: "X% of Y" → X/100*Y

Sử dụng:
    from scp.core.math_evaluator import evaluate_expression, extract_math_expression, verify_math

    result = evaluate_expression("2 + 3 * 4")        # → 14
    result = evaluate_expression("sqrt(144)")        # → 12.0
    result = evaluate_expression("(1+2)**3")         # → 27
    result = evaluate_expression("10!")              # → 3628800

    # Verify một câu hỏi AI
    verdict = verify_math("Tính 2+3", "5")           # → ("PASS", 5.0, "AI=5, real=5.0")
    verdict = verify_math("Tính 2+3", "6")           # → ("FAIL", 5.0, "AI=6, real=5.0")

An toàn:
    Chỉ chấp nhận: số, +, -, *, /, //, %, **, (, ), dấu chấm/phẩy,
    và các hàm trong whitelist. Không cho phép:
      - Names không trong whitelist (no import, no attribute access)
      - Subscript / Lambda / ListComp / Call tới object bất kỳ
"""

import ast
import logging
import math
import operator
import re
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# WHITELIST — Tập hợp hàm/hằng số được phép
# ============================================================

# Binary operators được phép (không bao gồm MatMult, LShift, RShift, BitOr, BitAnd, BitXor)
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Unary operators
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Compare operators
_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

# Functions được phép gọi (toán học thuần)
_FUNCS = {
    'sqrt': math.sqrt,
    'abs': abs,
    'fabs': math.fabs,
    'ceil': math.ceil,
    'floor': math.floor,
    'round': round,
    'gcd': math.gcd,
    'lcm': getattr(math, 'lcm', lambda a, b: abs(a * b) // math.gcd(a, b) if a and b else 0),
    'log': math.log10,  # [V104.20 #1 ROLLBACK] ln was wrong — log() in math context = log10
    'log10': math.log10,
    'log2': math.log2,
    'ln': math.log,
    'exp': math.exp,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sinh': math.sinh,
    'cosh': math.cosh,
    'tanh': math.tanh,
    'factorial': math.factorial,
    'isqrt': getattr(math, 'isqrt', lambda x: int(math.sqrt(x))),
    'pow': pow,
    'max': max,
    'min': min,
}

# Constants
_CONSTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
    # [V104.17 #5] 'inf' and 'nan' removed — cause unpredictable comparisons
}

# ============================================================
# AST EVALUATOR — Đệ quy an toàn
# ============================================================

class MathEvalError(Exception):
    """Lỗi khi evaluate expression."""
    pass


def _eval_node(node: ast.AST) -> Any:
    """Đệ quy đánh giá AST node."""
    # Number literal (int, float)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise MathEvalError(f"Constant type not allowed: {type(node.value).__name__}")

    # Binary op: a + b
    if isinstance(node, ast.BinOp):
        op_func = _BIN_OPS.get(type(node.op))
        if not op_func:
            raise MathEvalError(f"Binary operator not allowed: {type(node.op).__name__}")
        # [V104.21 #5] Power limit — was: unlimited → 2**999999 hang
        if isinstance(node.op, ast.Pow):
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            # Cap exponent at 1000, base at 1e308
            if isinstance(right, (int, float)) and abs(right) > 1000:
                raise MathEvalError(f"Power exponent too large: {right} > 1000")
            if isinstance(left, (int, float)) and abs(left) > 1e308:
                raise MathEvalError(f"Power base too large: {left} > 1e308")
            return op_func(left, right)
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return op_func(left, right)

    # Unary op: -a, +a
    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if not op_func:
            raise MathEvalError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op_func(_eval_node(node.operand))

    # Comparison: a == b, a < b, ...
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            op_func = _CMP_OPS.get(type(op))
            if not op_func:
                raise MathEvalError(f"Compare operator not allowed: {type(op).__name__}")
            right = _eval_node(comparator)
            if not op_func(left, right):
                return False
            left = right
        return True

    # Function call: sqrt(144), gcd(12, 8)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise MathEvalError("Only direct function calls allowed (no method/attribute calls)")
        func_name = node.func.id
        if func_name not in _FUNCS:
            raise MathEvalError(f"Function not allowed: {func_name}")
        if node.keywords:
            raise MathEvalError("Keyword arguments not allowed")
        args = [_eval_node(a) for a in node.args]
        try:
            # [V104.17 #3 FIX] Resource limits for factorial and power
            if func_name == 'factorial':
                n = args[0]
                if not isinstance(n, int) or n < 0 or n > 10000:
                    raise ValueError(f"factorial({n}) out of range (0-10000)")
            return _FUNCS[func_name](*args)
        except Exception as e:
            raise MathEvalError(f"Function {func_name} error: {e}") from e

    # Name (constant): pi, e
    if isinstance(node, ast.Name):
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        raise MathEvalError(f"Name not allowed: {node.id}")

    # Expression wrapper
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    raise MathEvalError(f"AST node type not allowed: {type(node).__name__}")


def evaluate_expression(expr: str) -> Any:
    """
    Đánh giá biểu thức toán học an toàn.

    Args:
        expr: "2 + 3 * 4", "sqrt(144)", "(1+2)**3", "10!", "5 % 3"

    Returns:
        Giá trị (int/float/bool).

    Raises:
        MathEvalError nếu expression không hợp lệ hoặc chứa cú pháp bị cấm.
    """
    if not expr or not isinstance(expr, str):
        raise MathEvalError("Empty expression")

    # Preprocess:
    s = expr.strip()

    # Factorial postfix: "5!" → "factorial(5)", "(2+3)!" → "factorial((2+3))"
    # Lặp để xử lý "5!!" → factorial(factorial(5))
    while '!' in s:
        new_s, n = re.subn(
            r'(\d+(?:\.\d+)?|\))\!',
            lambda m: f'factorial({m.group(1)})',
            s
        )
        if n == 0:
            break
        s = new_s

    # Modulo viết tay: "5 mod 3" → "5 % 3"
    s = re.sub(r'\bmod\b', '%', s, flags=re.IGNORECASE)

    # × → *, ÷ → /
    s = s.replace('×', '*').replace('÷', '/')

    # Power symbols: ² → **2, ³ → **3
    s = s.replace('²', '**2').replace('³', '**3').replace('¹', '**1')

    # Parse AST
    try:
        tree = ast.parse(s, mode='eval')
    except SyntaxError as e:
        raise MathEvalError(f"Syntax error: {e}") from e

    # Evaluate
    return _eval_node(tree)


# ============================================================
# QUESTION PARSING — Trích phép tính từ câu hỏi tiếng Việt
# ============================================================

# Prefixes thường gặp trước biểu thức
_QUESTION_PREFIXES = re.compile(
    r'^(?:tính|calculate|compute|eval|evaluate|đánh\s+giá|what\s+is\s+(?:the\s+)?|whats|what\'s|kết\s+quả\s+của|giá\s+trị\s+của)\s*[:?]?\s*',
    re.IGNORECASE,
)
# Suffixes thường gặp sau biểu thức
_QUESTION_SUFFIXES = re.compile(
    r'\s*(?:bằng\s+bao\s+nhiêu[??]*|=\s*\?+|bằng\s*[?]+|equals?\s*[?]*|=\s*$|[?]+$).*$',
    re.IGNORECASE,
)
# X% of Y
_PERCENT_PATTERN = re.compile(r'(\d+(?:\.\d+)?\s*%\s*of\s*\d+(?:\.\d+)?)', re.IGNORECASE)
# Pattern để kiểm tra có phải phép tính (có digit + operator/func)
_HAS_OP = re.compile(r'[+\-*/%^]|mod|\b(sqrt|abs|gcd|lcm|factorial|log|log10|log2|ln|exp|sin|cos|tan)\b|\*\*|!')
_HAS_DIGIT = re.compile(r'\d')


def extract_math_expression(question: str) -> str | None:
    """
    Trích biểu thức toán học từ câu hỏi.

    Returns:
        Biểu thức (str) hoặc None nếu không phải câu hỏi toán học.
    """
    if not question:
        return None

    q = question.strip()

    # [V91 FIX] Convert word-form math to symbols
    # "square root of 144" → "sqrt(144)"
    # "cube root of 27" → "27 ** (1/3)"
    q.lower()
    import re as _re
    q = _re.sub(r'square root of (\d+(?:\.\d+)?)', r'sqrt(\1)', q, flags=_re.IGNORECASE)
    q = _re.sub(r'cube root of (\d+(?:\.\d+)?)', r'(\1 ** (1/3))', q, flags=_re.IGNORECASE)
    # "X squared" → "X**2", "X cubed" → "X**3"
    q = _re.sub(r'(\d+(?:\.\d+)?)\s*squared', r'\1**2', q, flags=_re.IGNORECASE)
    q = _re.sub(r'(\d+(?:\.\d+)?)\s*cubed', r'\1**3', q, flags=_re.IGNORECASE)
    # "X to the power of Y" → "X**Y"
    q = _re.sub(r'(\d+(?:\.\d+)?)\s*(?:to the power of|\^|\*\*)\s*(\d+(?:\.\d+)?)', r'\1**\2', q, flags=_re.IGNORECASE)
    # "X times Y" → "X * Y", "X plus Y" → "X + Y", "X minus Y" → "X - Y"
    q = _re.sub(r'(\d+)\s*times\s*(\d+)', r'\1 * \2', q, flags=_re.IGNORECASE)
    q = _re.sub(r'(\d+)\s*plus\s*(\d+)', r'\1 + \2', q, flags=_re.IGNORECASE)
    q = _re.sub(r'(\d+)\s*minus\s*(\d+)', r'\1 - \2', q, flags=_re.IGNORECASE)
    q = _re.sub(r'(\d+)\s*divided by\s*(\d+)', r'\1 / \2', q, flags=_re.IGNORECASE)

    # Bỏ prefix (Tính/Calculate/...)
    q1 = _QUESTION_PREFIXES.sub('', q).strip()

    # Bỏ suffix (= ?, bằng bao nhiêu, ...)
    q2 = _QUESTION_SUFFIXES.sub('', q1).strip()

    # Nếu còn dấu "?" ở cuối do regex không match hết, strip thêm
    q2 = q2.rstrip('?').rstrip('=').rstrip('.').strip()

    # X% of Y pattern
    m = _PERCENT_PATTERN.search(q)
    if m:
        return m.group(1)

    # Validate: phải có digit + operator
    if _HAS_DIGIT.search(q2) and _HAS_OP.search(q2):
        # Loại bỏ các ký tự không hợp lệ (chỉ giữ số, operator, parentheses, hàm, comma, space)
        # nhưng trước tiên thử evaluate trực tiếp
        # Nếu có ký tự lạ → thử trích đoạn con hợp lệ
        try:
            evaluate_expression(q2)
            return q2
        except MathEvalError as exc:
            # silent-by-design: probe failure triggers the documented substring-extraction fallback.
            logger.debug("math_evaluator: direct evaluate failed, extracting substring: %s", exc, exc_info=True)
            # Thử tìm substring hợp lệ dài nhất
            # Pattern: tìm biểu thức toán học trong câu
            # Cho phép: digit, ., +, -, *, /, %, ^, (, ), ,, space, letters (tên hàm)
            m2 = re.search(r'[\d()][\d+\-*/%^().,\s\w]*', q2)
            if m2:
                candidate = m2.group(0).strip()
                # Cắt bỏ chữ dư ở cuối (vd "5 plus 3" → chỉ lấy "5")
                # Thử evaluate candidate, nếu fail → cắt dần
                while candidate:
                    try:
                        evaluate_expression(candidate)
                        if _HAS_DIGIT.search(candidate) and _HAS_OP.search(candidate):
                            return candidate
                        break
                    except MathEvalError as exc:
                        # silent-by-design: trim-probe failure drives the documented cut-from-end loop.
                        logger.debug("math_evaluator: candidate evaluate failed, trimming: %s", exc, exc_info=True)
                        # Cắt từ cuối
                        idx = max(
                            candidate.rfind('+'), candidate.rfind('-'),
                            candidate.rfind('*'), candidate.rfind('/'),
                            candidate.rfind('%'), candidate.rfind('^'),
                            candidate.rfind('('), candidate.rfind(')'),
                            candidate.rfind(','),
                        )
                        if idx <= 0:
                            break
                        candidate = candidate[:idx].rstrip()
                # Fallback: trả về bản gốc nếu có digit + op
                if _HAS_DIGIT.search(q2):
                    return q2
    return None


# ============================================================
# VERIFY — So sánh AI answer với kết quả deterministic
# ============================================================

def _extract_number(text: str) -> float | None:
    """Trích số cuối cùng trong text (thường là kết quả)."""
    if not text:
        return None
    nums = re.findall(r'-?\d+\.?\d*(?:[eE][+-]?\d+)?', str(text))
    if not nums:
        return None
    try:
        return float(nums[-1])
    except ValueError as exc:
        # silent-by-design: parse probe on free text; None means "no number found".
        logger.debug("math_evaluator: last-number parse failed: %s", exc, exc_info=True)
        return None


def _format_number(n: Any) -> str:
    """Format số đẹp: 5.0 → 5, 0.5 → 0.5."""
    if isinstance(n, bool):
        return str(n)
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if n.is_integer() and abs(n) < 1e15:
            return str(int(n))
        return f"{n:g}"
    return str(n)


def verify_math(question: str, ai_answer: str) -> tuple[str, float | None, str]:
    """
    Verify câu trả lời toán học của AI.

    Args:
        question: "Tính 2+3"
        ai_answer: "5" hoặc "2 + 3 = 5"

    Returns:
        (verdict, real_value, reason)
        verdict: "PASS" | "FAIL" | "UNKNOWN"
        real_value: kết quả thực (float/int/bool) hoặc None
        reason: giải thích
    """
    expr = extract_math_expression(question)

    if not expr:
        return ("UNKNOWN", None, "Không parse được biểu thức từ câu hỏi")

    try:
        real_value = evaluate_expression(expr)
    except MathEvalError as e:
        return ("UNKNOWN", None, f"Lỗi evaluate: {e}")
    except Exception as e:
        logger.debug(f"verify_math ignored: {e}", exc_info=True)
        return ("UNKNOWN", None, f"Lỗi không xác định: {e}")

    # Trích số từ AI answer
    ai_num = _extract_number(ai_answer)

    # Nếu real_value là bool (so sánh), kiểm tra True/False/1/0
    if isinstance(real_value, bool):
        ai_lower = (ai_answer or '').lower().strip()
        if ai_lower in ('true', 'đúng', 'yes', '1', 'đúng vậy'):
            ai_bool = True
        elif ai_lower in ('false', 'sai', 'no', '0', 'không'):
            ai_bool = False
        else:
            return ("UNKNOWN", real_value, f"Real={real_value}, AI không trả lời True/False")
        if ai_bool == real_value:
            return ("PASS", real_value, f"Biểu thức: {expr} = {real_value} (AI: {ai_answer})")
        return ("FAIL", real_value, f"Biểu thức: {expr} = {real_value}, AI nói: {ai_answer}")

    # So sánh số
    if ai_num is None:
        return ("UNKNOWN", real_value, f"Real={_format_number(real_value)}, AI không có số")

    # So sánh với tolerance (cho float)
    tolerance = 1e-6
    if isinstance(real_value, float):
        if abs(ai_num - real_value) < tolerance or (
            real_value != 0 and abs((ai_num - real_value) / real_value) < 1e-6
        ):
            return ("PASS", real_value, f"Biểu thức: {expr} = {_format_number(real_value)} (AI: {ai_num})")
    else:
        if ai_num == float(real_value):
            return ("PASS", real_value, f"Biểu thức: {expr} = {_format_number(real_value)} (AI: {ai_num})")

    return ("FAIL", real_value, f"Biểu thức: {expr} = {_format_number(real_value)}, AI nói: {ai_num}")


# ============================================================
# SELF-TEST
# ============================================================
if __name__ == '__main__':
    tests = [
        ("2 + 3", 5),
        ("2 + 3 * 4", 14),
        ("(1 + 2) ** 3", 27),
        ("10!", 3628800),
        ("sqrt(144)", 12.0),
        ("7 % 3", 1),
        ("10 // 3", 3),
        ("pi", math.pi),
        ("2 ** 10", 1024),
        ("abs(-5)", 5),
        ("gcd(12, 8)", 4),
        ("factorial(5)", 120),
        ("3.5 + 1.5", 5.0),
        ("log10(1000)", 3.0),
        ("2 + 2 == 4", True),
        ("5 > 3", True),
    ]

    print("=== Math Evaluator Self-Test ===")
    passed = 0
    for expr, expected in tests:
        try:
            result = evaluate_expression(expr)
            ok = (result == expected) or (
                isinstance(expected, float) and abs(result - expected) < 1e-9
            )
            mark = "OK" if ok else "FAIL"
            if ok:
                passed += 1
            print(f"  [{mark}] {expr:30s} = {result}  (expected {expected})")
        except Exception as e:
            # silent-by-design: CLI self-test prints the error directly; mirrored to logs.
            logger.debug("math_evaluator self-test: %s → %s", expr, e, exc_info=True)
            print(f"  [ERR ] {expr:30s} → {e}")

    print(f"\n{passed}/{len(tests)} passed")

    print("\n=== Verify Tests ===")
    verify_tests = [
        ("Tính 2+3", "5", "PASS"),
        ("Tính 2+3", "6", "FAIL"),
        ("Calculate 7*8", "56", "PASS"),
        ("Calculate 7*8", "54", "FAIL"),
        ("sqrt(144) bằng bao nhiêu?", "12", "PASS"),
        ("10! = ?", "3628800", "PASS"),
        ("(1+2)**3", "27", "PASS"),
        ("Tính 2**10", "1024", "PASS"),
    ]
    vpassed = 0
    for q, ai, expected_v in verify_tests:
        verdict, real, reason = verify_math(q, ai)
        ok = verdict == expected_v
        if ok:
            vpassed += 1
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] Q='{q}' AI='{ai}' → {verdict} (real={real})  expected={expected_v}")
        if not ok:
            print(f"         reason: {reason}")

    print(f"\n{vpassed}/{len(verify_tests)} verify tests passed")
