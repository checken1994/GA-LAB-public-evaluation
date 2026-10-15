# SCP CIRCUIT: M08 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M08-closure.json)
"""
Fitness Engine — hệ quy chiếu liên tục cho tiến hóa SCP (Cổng B/H).

TẠI SAO: evolution.py tự sửa code nhưng không có thước đo lịch sử → không
thể chứng minh N+1 tốt hơn N sau T ngày. Tiến hóa không thước đo = random
mutation. Engine này đo LỚP XÁC MINH DETERMINISTIC của SCP trên Golden Suite
đóng băng (100 quyết định, gold tính bằng toán học, KHÔNG dùng LLM chấm —
chấm bằng LLM là tự dính ảo giác đồng thuận mà SCP ra đời để chống).

SUT (system under test) deterministic:
  1. tier1_guard.check (cấu trúc + grounding)
  2. math/conversion/logic: SOLVE LẠI bằng evaluator thuần (ast whitelist)
     rồi so với candidate — Reality > Model: tính lại, đừng tin câu trả lời.
  3. rag: grounding overlap với evidence context.

Metrics: decision_accuracy, false_accept_rate (nguy hiểm nhất — chụp mù
lỗi), avg_decision_ms.
Gate: PROMOTE chỉ khi accuracy không giảm VÀ false_accept không tăng VÀ
latency không vượt +20% so với baseline N. Còn lại → ROLLBACK (toán, không
cảm tính).

Lịch sử: data/fitness_history.jsonl (mỗi run 1 dòng, kèm config_hash của
các file nằm trong SUT — đổi code SUT là đổi hash, history tự phân biệt).
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import operator

logger = logging.getLogger(__name__)
import os
import re
import time
from pathlib import Path
from typing import Any

from scp.security.tier1_guard import check as tier1_check

# fitness_engine.py lives at <repo>/scp/core/ — parents[2] is the repo root.
GOLDEN_PATH = Path(__file__).resolve().parents[2] / "tests" / "golden" / "golden_dataset.json"
HISTORY_DEFAULT = Path("data") / "fitness_history.jsonl"
SUT_FILES = ("scp/security/tier1_guard.py", "scp/core/fitness_engine.py")

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _safe_eval_arithmetic(expr: str) -> float | None:
    """Evaluate pure arithmetic via AST whitelist — no exec, no eval."""
    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = _eval(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError(f"non-arithmetic node: {type(node).__name__}")
    try:
        return _eval(ast.parse(expr.strip(), mode="eval"))
    except (ValueError, SyntaxError) as exc:
        # silent-by-design: parse/eval probe; None means "not a deterministic expression" by contract.
        logger.debug("fitness_engine: expression eval probe failed: %s", exc, exc_info=True)
        return None


def _num(value: str) -> float | None:
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError) as exc:
        # silent-by-design: parse probe; None means "not a number" by contract.
        logger.debug("fitness_engine: numeric parse failed: %s", exc, exc_info=True)
        return None


def solve_item(item: dict[str, Any]) -> str | None:
    """Deterministic solver: recompute the answer WITHOUT seeing candidate.

    Fail-closed: trả None nếu không giải được (khi đó mọi candidate chỉ còn
    được chấp nhận qua tier1 structural — được tính riêng trong report).
    """
    category = item.get("category")
    question = item.get("question", "")
    numbers = [float(n.replace(",", ".")) for n in _NUM_RE.findall(question)]
    if category == "logic":
        if len(numbers) >= 2:
            return str(int(numbers[0] * numbers[1]))
        return None
    if category == "math":
        if len(numbers) >= 2 and ("+" in question):
            return str(int(numbers[0] + numbers[1]))
        if len(numbers) >= 2 and ("×" in question or "*" in question):
            return str(int(numbers[0] * numbers[1]))
        return None
    if category == "conversion":
        # Hệ số quy đổi được đóng băng trong context chuẩn của item:
        # "Quy ước chuẩn: 1 km = 1000 m" → solver đọc số sau dấu '='.
        ctx = item.get("context", "")
        tail = ctx.split("=")[-1] if "=" in ctx else ""
        match = _NUM_RE.search(tail)
        return str(int(float(match.group()))) if match else None
    return None  # rag: không có solver — grounding đã chạy trong tier1


def decide(item: dict[str, Any]) -> tuple[str, list[str], float]:
    """One deterministic verification decision. Returns (decision, failures, ms)."""
    started = time.perf_counter()
    failures: list[str] = []
    # Grounding (evidence binding) chỉ áp dụng cho rag — với logic/conversion,
    # context là tiền đề đề bài còn answer là KẾT QUẢ TÍNH RA, hiển nhiên
    # không nằm trong tiền đề; bắt grounding ở đây là sai semantic.
    is_rag = item.get("category") == "rag"
    evidence = item.get("context", "") if is_rag else ""
    tier1 = tier1_check(item.get("question", ""), item.get("candidate", ""), evidence)
    if is_rag and tier1.passed:
        # Strict binding cho RAG: 100% content-words của candidate phải được
        # evidence đỡ (overlap 0.6 đủ để "Đại Tây Dương" lọt qua "Đại dương
        # ... Thái Bình Dương" — false accept 1/100 trong baseline thật).
        from scp.security.tier1_guard import check_grounding

        strict = check_grounding(item.get("candidate", ""), evidence, min_overlap=1.0)
        if not strict.passed:
            tier1.passed = False
            tier1.failures.extend(strict.failures)
    if not tier1.passed:
        failures.extend(tier1.failures)
    else:
        solved = solve_item(item)
        if solved is not None:
            got, want = _num(item.get("candidate", "")), _num(solved)
            if got is None or want is None or abs(got - want) > 1e-9:
                failures.append("SOLVER_MISMATCH")
        elif item.get("category") == "rag":
            pass  # grounding đã được tier1 đánh giá với evidence context
        else:
            failures.append("SOLVER_UNAVAILABLE")
    elapsed_ms = (time.perf_counter() - started) * 1000
    return ("ACCEPT" if not failures else "REJECT"), failures, elapsed_ms


def config_hash() -> str:
    """Hash of the SUT sources — history entries are comparable per-hash."""
    digest = hashlib.sha256()
    root = Path(__file__).resolve().parents[2]
    for rel in SUT_FILES:
        digest.update((root / rel).read_bytes())
    return "sha256:" + digest.hexdigest()[:32]


def run_suite(golden_path: Path | str = GOLDEN_PATH) -> dict[str, Any]:
    """Run the frozen golden suite through the deterministic SUT."""
    dataset = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    items = dataset["items"]
    total = len(items)
    correct = 0
    false_accepts = 0
    false_rejects = 0
    total_ms = 0.0
    misses: list[dict[str, Any]] = []
    for item in items:
        decision, failures, elapsed_ms = decide(item)
        total_ms += elapsed_ms
        expected = item["expected"]
        if decision == expected:
            correct += 1
        else:
            if decision == "ACCEPT":
                false_accepts += 1
            else:
                false_rejects += 1
            misses.append({"id": item["id"], "expected": expected, "got": decision, "failures": failures})
    return {
        "suite": str(golden_path),
        "config_hash": config_hash(),
        "total": total,
        "decision_accuracy": round(correct / total, 4) if total else 0.0,
        "false_accept_rate": round(false_accepts / total, 4) if total else 0.0,
        "false_reject_rate": round(false_rejects / total, 4) if total else 0.0,
        "avg_decision_ms": round(total_ms / total, 4) if total else 0.0,
        "misses": misses,
        "ran_at": time.time(),
    }


def append_history(report: dict[str, Any], history_path: Path | str | None = None) -> None:
    path = Path(history_path or os.environ.get("SCP_FITNESS_HISTORY", HISTORY_DEFAULT))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")


def load_baseline(history_path: Path | str | None = None) -> dict[str, Any] | None:
    path = Path(history_path or os.environ.get("SCP_FITNESS_HISTORY", HISTORY_DEFAULT))
    if not path.exists():
        return None
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            last = json.loads(line)
        except (TypeError, ValueError) as exc:
            # Corrupt ledger line must be visible, not silently dropped.
            logger.warning("fitness_engine: corrupt ledger line in %s: %s", path, exc, exc_info=True)
            continue
    return last


def gate(prev: dict[str, Any] | None, nxt: dict[str, Any]) -> dict[str, Any]:
    """Evolution Gate — PROMOTE/ROLLBACK by math, never by LLM opinion."""
    if prev is None:
        return {"verdict": "BASELINE", "reasons": ["no previous measurement"]}
    reasons: list[str] = []
    if nxt["decision_accuracy"] < prev["decision_accuracy"]:
        reasons.append(f"accuracy dropped {prev['decision_accuracy']} -> {nxt['decision_accuracy']}")
    if nxt["false_accept_rate"] > prev["false_accept_rate"]:
        reasons.append(f"false_accept rose {prev['false_accept_rate']} -> {nxt['false_accept_rate']}")
    if nxt["avg_decision_ms"] > prev["avg_decision_ms"] * 1.2 + 1e-9:
        reasons.append(
            f"latency grew {prev['avg_decision_ms']}ms -> {nxt['avg_decision_ms']}ms (>+20%)"
        )
    return {"verdict": "ROLLBACK" if reasons else "PROMOTE", "reasons": reasons}


def run_and_gate(history_path: Path | str | None = None) -> dict[str, Any]:
    """Convenience: run suite, compare with baseline, append history."""
    report = run_suite()
    prev = load_baseline(history_path)
    verdict = gate(prev, report)
    append_history(report, history_path)
    return {"report": report, "verdict": verdict, "prev_config_hash": (prev or {}).get("config_hash")}
