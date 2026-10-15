from pathlib import Path

p = Path(str(Path(__file__).resolve().parent.parent / "scp" / "runtime" / "judge_parts" / "judgecore_mixin.py"))
s = p.read_text(encoding="utf-8-sig")
old = (
    "                        _filtered_slm_responses, _evidence_filter_report = filter_slm_responses(\n"
    "            question, slm_responses or []\n"
    "        )\n"
    "        if _evidence_filter_report.get(\"droppedCount\"):\n"
    "            slm_responses = _filtered_slm_responses\n"
    "            verdict.slm_responses = _filtered_slm_responses\n"
    "        verdict.evidence[\"evidence_consistency\"] = _evidence_filter_report\n"
    "        ground_truth = {}\n"
)
new = (
    "                        _filtered_slm_responses, _evidence_filter_report = filter_slm_responses(\n"
    "                            question, slm_responses or []\n"
    "                        )\n"
    "                        if _evidence_filter_report.get(\"droppedCount\"):\n"
    "                            slm_responses = _filtered_slm_responses\n"
    "                            verdict.slm_responses = _filtered_slm_responses\n"
    "                        verdict.evidence[\"evidence_consistency\"] = _evidence_filter_report\n"
    "                        ground_truth = {}\n"
)
if s.count(old) != 1:
    raise RuntimeError(f"consistency block matches={s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("fixed consistency indentation")
