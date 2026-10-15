"""
benchmark/grader.py
====================
Independent SCP Benchmark Grader.

DNA #5  — Ảo giác đồng thuận: grader KHÔNG được import từ scp/ — không cùng lineage với SUT.
DNA #14 — Không tin verdict của system under test — tự tính toán từ raw API response.
DNA #22 — PASS ≠ TRUE: grader dùng exact-match normalize, không substring match ngây thơ.

Cách dùng:
  # Chạy benchmark và lưu kết quả thô:
  python benchmark/run_world_exam.py --output raw_results.jsonl

  # Chấm điểm độc lập:
  python benchmark/grader.py raw_results.jsonl --dataset gsm8k
  python benchmark/grader.py raw_results.jsonl --dataset truthfulqa

  # Output: bảng điểm với exact_match, normalize_match, false_positive_rate
  # Không cần server chạy. Không import scp.

Zero external dependencies — chỉ dùng Python stdlib.
"""
from __future__ import annotations

import json
import re
import sys
import argparse
from pathlib import Path
from typing import Any


# =============================================================================
# Normalizers — thuần Python, không phụ thuộc bất kỳ gì
# =============================================================================

def _normalize_number(s: str) -> str | None:
    """
    Chuẩn hóa một chuỗi số về dạng số học.
    Ví dụ: "$1,234.5" → "1234.5", "18%" → "18", "2.0" → "2"
    Returns None nếu không parse được thành số.
    """
    s = s.strip()
    # Bỏ ký tự đơn vị/tiền tệ phổ biến
    s = re.sub(r'[$€£¥₫,\s%]', '', s)
    try:
        f = float(s)
        # Nếu là số nguyên → trả về dạng int để "2.0" == "2"
        if f == int(f):
            return str(int(f))
        return str(f)
    except ValueError:
        return None


def _extract_gsm8k_answer(text: str) -> str:
    """
    Extract số cuối cùng từ text theo format GSM8K (#### <answer>).
    Nếu không có #### → extract số cuối cùng trong text.
    """
    # Format chuẩn GSM8K
    m = re.search(r'####\s*(-?[\d,\.]+)', text)
    if m:
        return m.group(1).replace(',', '').strip()
    # Fallback: số cuối cùng trong text
    nums = re.findall(r'-?[\d]+(?:[,\.][\d]+)*', text)
    if nums:
        return nums[-1].replace(',', '')
    return text.strip()


def _normalize_text(s: str) -> str:
    """Normalize text answer: lowercase, strip, collapse whitespace."""
    return re.sub(r'\s+', ' ', s.lower().strip())


def _exact_match_number(gold: str, pred: str) -> bool:
    """So sánh số học exact: "2" == "2.0" == "2.00"."""
    gn = _normalize_number(_extract_gsm8k_answer(gold))
    pn = _normalize_number(_extract_gsm8k_answer(pred))
    if gn is not None and pn is not None:
        return gn == pn
    return False


def _exact_match_text(gold: str, pred: str) -> bool:
    """So sánh text exact sau normalize."""
    return _normalize_text(gold) == _normalize_text(pred)


def _substring_match(gold: str, pred: str) -> bool:
    """
    Substring match — chỉ dùng để báo cáo false positive rate, KHÔNG dùng để chấm điểm chính.
    """
    return _normalize_text(gold) in _normalize_text(pred)


# =============================================================================
# Dataset-specific extractors
# =============================================================================

class DatasetGrader:
    """Base class cho dataset-specific grading logic."""

    name: str = "generic"

    def extract_gold(self, record: dict[str, Any]) -> str:
        """Lấy gold answer từ record JSONL."""
        return str(record.get("gold_answer") or record.get("answer") or "")

    def extract_prediction(self, api_response: dict[str, Any]) -> str:
        """Lấy prediction từ raw API response — KHÔNG dùng verdict của SUT."""
        # Ưu tiên final_answer, sau đó answer, sau đó text
        return str(
            api_response.get("final_answer")
            or api_response.get("answer")
            or ""
        )

    def grade(self, gold: str, prediction: str) -> dict[str, Any]:
        """Chấm điểm một cặp (gold, prediction). Returns grading breakdown."""
        exact_num = _exact_match_number(gold, prediction)
        exact_text = _exact_match_text(gold, prediction)
        substr = _substring_match(gold, prediction)

        correct = exact_num or exact_text
        return {
            "correct": correct,
            "exact_number_match": exact_num,
            "exact_text_match": exact_text,
            "substring_match": substr,
            "false_positive_risk": substr and not correct,  # substr khớp nhưng exact không khớp
        }


class GSM8KGrader(DatasetGrader):
    name = "gsm8k"

    def extract_gold(self, record: dict[str, Any]) -> str:
        answer = str(record.get("answer") or record.get("gold_answer") or "")
        return _extract_gsm8k_answer(answer)

    def grade(self, gold: str, prediction: str) -> dict[str, Any]:
        # GSM8K chỉ cần số cuối cùng đúng
        pred_num = _extract_gsm8k_answer(prediction)
        exact = _exact_match_number(gold, pred_num)
        substr = _substring_match(gold, pred_num)
        return {
            "correct": exact,
            "exact_number_match": exact,
            "exact_text_match": False,
            "substring_match": substr,
            "false_positive_risk": substr and not exact,
            "gold_extracted": gold,
            "pred_extracted": pred_num,
        }


class TruthfulQAGrader(DatasetGrader):
    name = "truthfulqa"

    def grade(self, gold: str, prediction: str) -> dict[str, Any]:
        # TruthfulQA: exact text match sau normalize
        exact = _exact_match_text(gold, prediction)
        substr = _substring_match(gold, prediction)
        return {
            "correct": exact,
            "exact_number_match": False,
            "exact_text_match": exact,
            "substring_match": substr,
            "false_positive_risk": substr and not exact,
        }


GRADERS: dict[str, type[DatasetGrader]] = {
    "gsm8k": GSM8KGrader,
    "truthfulqa": TruthfulQAGrader,
    "generic": DatasetGrader,
}


# =============================================================================
# Main grading pipeline
# =============================================================================

def grade_file(
    results_file: Path,
    dataset: str = "gsm8k",
    max_items: int | None = None,
) -> dict[str, Any]:
    """
    Chấm điểm toàn bộ file kết quả.

    Input JSONL format (một dòng một item):
      {"question": "...", "gold": "...", "api_response": {...raw JSON từ /ask...}}

    Returns:
      {"total": N, "correct": N, "accuracy": 0.XX, "false_positive_rate": 0.XX, "items": [...]}
    """
    grader_cls = GRADERS.get(dataset, DatasetGrader)
    grader = grader_cls()

    results_file = Path(results_file)
    if not results_file.exists():
        raise FileNotFoundError(f"Results file không tồn tại: {results_file}")

    items: list[dict[str, Any]] = []
    total = correct = false_positives = 0

    with results_file.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[WARN] Line {lineno}: JSON parse error — {e}", file=sys.stderr)
                continue

            gold = grader.extract_gold(record)
            api_response = record.get("api_response") or {}
            prediction = grader.extract_prediction(api_response)

            result = grader.grade(gold, prediction)
            result["lineno"] = lineno
            result["question"] = str(record.get("question", ""))[:80]
            result["gold"] = gold
            result["prediction"] = prediction[:200]

            # KHÔNG dùng verdict của SUT (circular trust)
            # result["sut_verdict"] = api_response.get("verdict")  ← ĐÃ XÓA

            items.append(result)
            total += 1
            if result["correct"]:
                correct += 1
            if result["false_positive_risk"]:
                false_positives += 1

            if max_items and total >= max_items:
                break

    accuracy = correct / total if total > 0 else 0.0
    fp_rate = false_positives / total if total > 0 else 0.0

    return {
        "dataset": dataset,
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "false_positive_rate": round(fp_rate, 4),
        "grader_class": grader_cls.__name__,
        "items": items,
    }


def print_report(report: dict[str, Any]) -> None:
    """In báo cáo ra stdout — format có thể đọc và reproduce bởi bất kỳ reviewer nào."""
    print("=" * 60)
    print(f"SCP Benchmark Grader — Independent Report")
    print(f"Dataset     : {report['dataset']}")
    print(f"Grader class: {report['grader_class']}")
    print(f"Total items : {report['total']}")
    print(f"Correct     : {report['correct']} / {report['total']}")
    print(f"Accuracy    : {report['accuracy']*100:.1f}%")
    print(f"False+rate  : {report['false_positive_rate']*100:.1f}% (substring khớp nhưng exact sai)")
    print("=" * 60)

    # In top 10 wrong items
    wrong = [i for i in report["items"] if not i["correct"]][:10]
    if wrong:
        print(f"\nTop {len(wrong)} wrong items:")
        for item in wrong:
            print(f"  L{item['lineno']:4d} | Gold: {item['gold']!r:30s} | Pred: {item['prediction'][:40]!r}")

    # Cảnh báo false positives
    fp = [i for i in report["items"] if i["false_positive_risk"]]
    if fp:
        print(f"\n[WARN] {len(fp)} false positive risks (substring match ≠ exact match):")
        for item in fp[:5]:
            print(f"  L{item['lineno']:4d} | Gold: {item['gold']!r} | Pred: {item['prediction'][:40]!r}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Independent SCP Benchmark Grader — zero import từ scp/"
    )
    parser.add_argument("results_file", type=Path, help="Path tới file JSONL chứa raw results")
    parser.add_argument(
        "--dataset",
        choices=list(GRADERS.keys()),
        default="gsm8k",
        help="Dataset type để chọn grading logic phù hợp",
    )
    parser.add_argument("--max-items", type=int, default=None, help="Giới hạn số items (debug)")
    parser.add_argument("--json", action="store_true", help="Output JSON thay vì human-readable")
    args = parser.parse_args()

    report = grade_file(args.results_file, dataset=args.dataset, max_items=args.max_items)

    if args.json:
        # Bỏ items khỏi JSON output để gọn
        out = {k: v for k, v in report.items() if k != "items"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_report(report)

    # Exit code: 0 = có kết quả, 1 = không có item nào
    sys.exit(0 if report["total"] > 0 else 1)


if __name__ == "__main__":
    main()
