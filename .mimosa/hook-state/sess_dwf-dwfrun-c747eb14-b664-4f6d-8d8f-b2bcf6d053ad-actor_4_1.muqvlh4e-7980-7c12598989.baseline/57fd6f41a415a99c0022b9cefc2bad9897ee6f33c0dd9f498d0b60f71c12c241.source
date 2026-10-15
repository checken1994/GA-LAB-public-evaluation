from __future__ import annotations

import json
from pathlib import Path
from benchmark.question_generator import generate_random_questions

questions, attacks = generate_random_questions(
    num_math=400,
    num_geography=400,
    num_ambiguous=200,
    num_attacks=0,
    seed=42,
)
path = Path(str(Path(__file__).resolve().parent.parent / "benchmark" / "questions_1000.jsonl"))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(
    "\n".join(json.dumps(item, ensure_ascii=False) for item in questions) + "\n",
    encoding="utf-8",
)
print(f"wrote={path} count={len(questions)} attacks={len(attacks)}")
