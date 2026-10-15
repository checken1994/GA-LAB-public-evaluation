"""Generate the frozen Golden Fitness Suite (deterministic, offline).

TẠI SAO: Cổng B/H của audit — SCP tự sửa code (evolution) nhưng không có hệ
quy chiếu liên tục nên không thể chứng minh N+1 tốt hơn N. Golden Suite là
bộ test ĐÓNG BĂNG (static JSON, seed cố định, không mạng, gold tính bằng
toán học) để Evolution Gate chạy trước khi chấp nhận mọi bản vá.

Run:  python scripts/generate_golden_suite.py
Out:  tests/golden/golden_dataset.json  (100 decisions = 50 base x 2 variants)

Mỗi item: {id, category, question, context, candidate, gold, expected}
  - expected=ACCEPT: candidate KHỚP gold (bản đúng)
  - expected=REJECT: candidate bị perturb có kiểm soát (bản sai)
SUT của fitness engine = LỚP XÁC MINH DETERMINISTIC của SCP (tier1 guard +
solver toán + grounding check) — KHÔNG dùng LLM để chấm (Reality > Model).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20260829
OUT = Path(__file__).resolve().parents[1] / "tests" / "golden" / "golden_dataset.json"

rng = random.Random(SEED)

CONVERSIONS = [
    ("1 km = ? m", 1000), ("1 kg = ? g", 1000), ("1 giờ = ? phút", 60),
    ("1 ngày = ? giờ", 24), ("1 tuần = ? ngày", 7), ("1 tấn = ? kg", 1000),
    ("1 phút = ? giây", 60), ("1 thập kỷ = ? năm", 10),
    ("1 thế kỷ = ? năm", 100), ("1 MB = ? KB", 1024),
]
ENTITIES = [("Thủ đô của Pháp là gì?", "Paris"), ("Màu của bầu trời ban ngày?", "xanh"),
            ("Chất khí thực vật hấp thụ?", "carbon dioxide"), ("Nguyên tố hóa học của nước?", "hydrogen"),
            ("Hành tinh gần Mặt Trời nhất?", "Sao Thủy"), ("Động vật lớn nhất Trái Đất?", "cá voi xanh"),
            ("Quốc gia có diện tích lớn nhất?", "Nga"), ("Dãy núi dài nhất thế giới?", "Andes"),
            ("Đại dương lớn nhất?", "Thái Bình Dương"), ("Kim loại lỏng ở nhiệt độ phòng?", "thủy ngân")]
WRONG_ENTITIES = ["Madrid", "đỏ", "oxygen", "helium", "Sao Kim", "cá voi đầu cong",
                  "Canada", "Rockies", "Đại Tây Dương", "sắt"]

items = []
nid = 0

def add(category, question, context, candidate, gold, expected):
    global nid
    nid += 1
    items.append({
        "id": f"golden-{nid:03d}", "category": category, "question": question,
        "context": context, "candidate": candidate, "gold": gold, "expected": expected,
    })

# --- 20 math (solver metadata nằm trong câu hỏi dạng chuẩn a op b) ---
for i in range(10):
    a, b = rng.randint(11, 99), rng.randint(11, 99)
    q = f"Tính: {a} + {b} = ?"
    add("math", q, "", str(a + b), str(a + b), "ACCEPT")
    add("math", q, "", str(a + b + rng.choice([1, -1, 10])), str(a + b), "REJECT")
for i in range(10):
    a, b = rng.randint(3, 19), rng.randint(3, 19)
    q = f"Tính: {a} × {b} = ?"
    add("math", q, "", str(a * b), str(a * b), "ACCEPT")
    add("math", q, "", str(a * b + rng.choice([a, b, 2])), str(a * b), "REJECT")

# --- 10 conversion ---
for q, val in CONVERSIONS:
    add("conversion", q, f"Quy ước chuẩn: {q.replace('?', str(val))}", str(val), str(val), "ACCEPT")
    add("conversion", q, f"Quy ước chuẩn: {q.replace('?', str(val))}", str(val * rng.choice([2, 10]) or 1), str(val), "REJECT")

# --- 10 logic (suy luận 2 bước xác định) ---
for i in range(10):
    x, y = rng.randint(2, 40), rng.randint(2, 40)
    q = f"Nếu mỗi hộp chứa {x} viên bi và có {y} hộp thì tổng số bi là bao nhiêu?"
    total = x * y
    add("logic", q, f"Mỗi hộp chứa {x} viên bi. Có {y} hộp.", str(total), str(total), "ACCEPT")
    add("logic", q, f"Mỗi hộp chứa {x} viên bi. Có {y} hộp.", str(total + x), str(total), "REJECT")

# --- 10 RAG grounding (câu trả lời phải nằm trong context) ---
for i, (q, ans) in enumerate(ENTITIES):
    ctx = f"Tài liệu tham khảo: {q.replace('?', '')} là {ans}. Thông tin này được xác nhận."
    add("rag", q, ctx, ans, ans, "ACCEPT")
    add("rag", q, ctx, WRONG_ENTITIES[i], ans, "REJECT")

assert len(items) == 100, f"expected 100 items, got {len(items)}"
OUT.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "schema_version": 1,
    "seed": SEED,
    "frozen_at": "2026-08-29",
    "description": "Golden Fitness Suite - 100 deterministic decisions (50 base x correct/corrupted)",
    "items": items,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"frozen {len(items)} decisions -> {OUT}")
