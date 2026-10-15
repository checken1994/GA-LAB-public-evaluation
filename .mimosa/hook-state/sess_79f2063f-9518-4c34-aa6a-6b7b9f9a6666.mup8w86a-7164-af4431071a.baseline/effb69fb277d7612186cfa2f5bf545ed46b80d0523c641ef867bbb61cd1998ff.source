from pathlib import Path
import json

in_file = Path(__file__).resolve().parent / "benchmark" / "gold_anchor_1000_VERIFIED.jsonl"
out_gold = Path(__file__).resolve().parent / "benchmark" / "gold_anchor_5_QUICK.jsonl"

def _contained_in_repo(p: Path) -> bool:
    """[SEC-S4] Containment guard: paths must resolve inside the repo tree."""
    return p.resolve().is_relative_to(Path(__file__).resolve().parent.parent)

if not (_contained_in_repo(in_file) and _contained_in_repo(out_gold)):
    raise SystemExit("SEC-S4: derived path escapes repository tree")

print("Đang trích xuất 5 câu hỏi...")
count = 0
# [SEC-S6] Paths open via pathlib Path.open after the containment guard above.
with in_file.open("r", encoding="utf-8") as fin, out_gold.open("w", encoding="utf-8") as fout:
    for line in fin:
        if not line.strip(): continue
        data = json.loads(line)
        # Đóng con dấu cuối cùng mà RAGAS đòi hỏi
        data["eligible_for_ragas"] = True
        fout.write(json.dumps(data, ensure_ascii=False) + "\n")
        count += 1
        if count >= 5: break
print("Đã tạo bộ đề 5 câu thành công.")
