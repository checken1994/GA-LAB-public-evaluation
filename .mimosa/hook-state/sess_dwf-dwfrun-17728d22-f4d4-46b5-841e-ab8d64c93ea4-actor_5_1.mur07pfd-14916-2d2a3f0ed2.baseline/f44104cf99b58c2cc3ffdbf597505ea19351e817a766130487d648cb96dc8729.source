# -*- coding: utf-8 -*-
"""In-memory unit tests for run_golden.py scoring functions. No network, no API calls.

Run: python test_scoring.py
"""
import sys

sys.path.insert(0, r"D:\scp\benchmark\golden_llm")

from run_golden import extract_choice_letter, extract_last_number, score_response  # noqa: E402

FAILURES = []


def check(name, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'} {name}: got={got!r} want={want!r}")
    if not ok:
        FAILURES.append(name)


# ---- extract_choice_letter -------------------------------------------------
check("letter bare B", extract_choice_letter("B"), "B")
check("letter parens", extract_choice_letter("(C)"), "C")
check("letter sentence", extract_choice_letter("The answer is D."), "D")
check("letter Answer-prefix", extract_choice_letter("Answer: A"), "A")
check("letter verbose last-wins", extract_choice_letter("Option A seems plausible, but the answer is C"), "C")
check("letter none", extract_choice_letter("I cannot decide between two options."), None)
check("letter lowercase", extract_choice_letter("b"), "B")
check("letter cutoff", extract_choice_letter("The correct option is"), None)
check("letter bracket", extract_choice_letter("[D]"), "D")

# ---- extract_last_number ---------------------------------------------------
check("num plain", extract_last_number("The answer is 42."), 42.0)
check("num comma", extract_last_number("She earns $1,250 in total."), 1250.0)
check("num decimal", extract_last_number("Answer: 3.5"), 3.5)
check("num negative", extract_last_number("Result: -7"), -7.0)
check("num none", extract_last_number("No numbers here."), None)
check("num last-wins", extract_last_number("16 eggs, 3 eaten, 4 for muffins, so 72 dollars"), 72.0)

# ---- score_response: mmlu --------------------------------------------------
mmlu_item = {"id": "mmlu-test", "question": "2+2?", "choices": ["3", "4", "5", "6"], "gold": "B"}
check("mmlu correct", score_response("mmlu", mmlu_item, "Answer: B"), ("B", True))
check("mmlu wrong", score_response("mmlu", mmlu_item, "A"), ("A", False))
check("mmlu unparsed", score_response("mmlu", mmlu_item, "hmm"), (None, False))

# ---- score_response: gsm8k -------------------------------------------------
gsm_item = {"id": "gsm8k-test", "question": "...", "gold": "72"}
check("gsm correct", score_response("gsm8k", gsm_item, "Step by step ... Answer: 72"), (72.0, True))
check("gsm comma", score_response("gsm8k", gsm_item, "total is 1,072 dollars"), (1072.0, False))
check("gsm unparsed", score_response("gsm8k", gsm_item, "I don't know"), (None, False))

# ---- score_response: truthfulqa --------------------------------------------
tqa_item = {"id": "tqa-test", "question": "...", "choices": ["true stmt", "false stmt"], "gold": "A"}
check("tqa correct", score_response("truthfulqa", tqa_item, "A"), ("A", True))
check("tqa wrong", score_response("truthfulqa", tqa_item, "The answer is B"), ("B", False))

# ---- score_response: hellaswag --------------------------------------------
hs_item = {"id": "hs-test", "question": "...", "choices": ["a", "b", "c", "d"], "gold": "D"}
check("hs correct", score_response("hellaswag", hs_item, "D"), ("D", True))
check("hs wrong", score_response("hellaswag", hs_item, "C."), ("C", False))

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILED -> {FAILURES}")
    sys.exit(1)
print("RESULT: ALL PASS")
