"""
Mảnh ghép #32 + #44 — Context Pruner với AST Heat Scoring.

TẠI SAO: nhét ±50 dòng quanh bug vào prompt LLM là lãng phí + nhiễu; nhét
cả dự án là 413 Payload Too Large. Pruner này đọc AST, tính "độ nóng" của
từng hàm (hàm chứa bug luôn nóng nhất; hàm có tên/docstring khớp mô tả bug
nóng nhì), giữ NGUYÊN VĂN các hàm nóng và GẤP các hàm nguội thành chữ ký +
marker. Kết quả: LLM thấy trọn vẹn vùng quan trọng, không bị nhiễu bởi
95% code nguội lạnh — nhìn xuyên thấu dự án lớn mà không tràn context.

Deterministic hoàn toàn (AST + token match), không LLM, không mạng.
"""
from __future__ import annotations

import ast
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# [^\W_] = alphanumeric loại trừ underscore → snake_case tách thành token
# riêng ("validate_password_policy" → validate/password/policy)
_WORD_RE = re.compile(r"[^\W_]{2,}", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").replace("_", " ").lower()))


def _function_span(node: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str]) -> tuple[int, int]:
    start = max(1, node.lineno)
    end = getattr(node, "end_lineno", None) or node.lineno
    return start, min(end, len(lines))


def score_functions(source: str, bug_line: int, description: str) -> list[dict[str, Any]]:
    """Trả về danh sách hàm top-level kèm điểm nóng, sắp giảm dần."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        # silent-by-design: source may legitimately be non-Python; hotspots cannot be computed.
        logger.debug("context_pruner: source not parseable, no hotspots: %s", exc, exc_info=True)
        return []
    desc_tokens = _tokens(description)
    scored: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name_tokens = _tokens(node.name)
        doc = ast.get_docstring(node) or ""
        overlap = len(name_tokens & desc_tokens)
        score = overlap * 10
        contains = node.lineno <= (bug_line or -1) <= (getattr(node, "end_lineno", -1) or -1)
        if contains:
            score += 100
        if doc and any(t in _tokens(doc) for t in desc_tokens):
            score += 5
        scored.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": min(getattr(node, "end_lineno", node.lineno), len(source.splitlines()) or 1),
                "score": score,
                "contains_bug": contains,
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["lineno"]))
    return scored


def prune_source(source: str, bug_line: int, description: str, keep_verbatim: int = 2) -> str:
    """Gấp các hàm nguội thành chữ ký + marker; giữ nguyên văn hàm nóng.

    Hàm chứa bug_line LUÔN được giữ nguyên văn bất kể điểm. Module docstring
    và imports luôn được giữ (khung lire của file).
    """
    lines = source.splitlines()
    if not lines:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        # silent-by-design: unparseable source is returned unchanged by design.
        logger.debug("context_pruner: source not parseable, returned unchanged: %s", exc, exc_info=True)
        return source

    scored = score_functions(source, bug_line, description)
    hot_names = {item["name"] for item in scored[: max(0, keep_verbatim)] if item["score"] > 0}
    cold = {item["name"]: item["score"] for item in scored if item["name"] not in hot_names}

    out: list[str] = []
    for node in tree.body:
        start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in cold:
                out.append(lines[start - 1])
                out.append(f"    ...  # [folded: cold context, heat={cold[node.name]}]")
                continue
            # hàm nóng: giữ nguyên văn
            out.extend(lines[start - 1: end])
            continue
        # statement khác (imports, gán module-level, class): giữ nguyên văn
        out.extend(lines[start - 1: end])
    return "\n".join(out)


def build_context_from_file(path: str, bug_line: int, description: str, fallback_lines: int = 50) -> str:
    """Đọc file + prune. Mọi lỗi (file không đọc được, syntax hỏng) → fallback
    cửa sổ ±fallback_lines quanh bug (hành vi cũ), không bao giờ raise."""
    from pathlib import Path

    try:
        source = Path(path).read_text(encoding="utf-8", errors="replace")
        pruned = prune_source(source, bug_line, description)
        if pruned.strip():
            return pruned
    except Exception as exc:
        # silent-by-design: pruning is an optional refinement; the line-window fallback below is documented.
        logger.debug("context_pruner: prune failed, using raw line window: %s", exc, exc_info=True)
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, (bug_line or 1) - fallback_lines)
        end = min(len(lines), (bug_line or 1) + fallback_lines)
        return "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1))
    except Exception as exc:
        logger.warning("context_pruner: context build failed, returning empty context: %s", exc, exc_info=True)
        return ""
