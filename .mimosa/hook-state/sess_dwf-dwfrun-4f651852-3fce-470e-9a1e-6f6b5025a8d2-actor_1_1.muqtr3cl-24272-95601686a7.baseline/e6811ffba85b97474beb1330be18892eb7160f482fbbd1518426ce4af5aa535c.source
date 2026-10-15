import json
import sys

with open(".agents/spec_miner_o6_survey_3/dangling_findings.json", encoding="utf-8") as f:
    findings = json.load(f)

with open(".agents/spec_miner_o6_survey_3/dangling_report.txt", "w", encoding="utf-8") as out:
    for x in findings:
        out.write(f"{x['file']}:{x['line']} -> {x['content']} | matches: {x['matches']}\n")

print(f"Wrote {len(findings)} findings to dangling_report.txt")
