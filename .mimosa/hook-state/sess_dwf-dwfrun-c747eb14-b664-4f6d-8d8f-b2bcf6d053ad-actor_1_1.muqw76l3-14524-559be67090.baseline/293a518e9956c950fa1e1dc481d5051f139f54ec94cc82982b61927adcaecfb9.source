import os
import re
import subprocess
import json

# Get list of all tracked files in git HEAD
tracked_files = subprocess.check_output(
    ["git", "ls-files"],
    text=True,
    encoding="utf-8"
).splitlines()

# Load deleted files
with open(os.path.join(os.path.dirname(__file__), "deleted_files_87d78da.txt"), "r", encoding="utf-8") as f:
    deleted_files = [line.strip() for line in f if line.strip()]

# Filter to actually currently absent files
absent_files = [f for f in deleted_files if not os.path.exists(f)]
print(f"Total deleted in 87d78da: {len(deleted_files)}")
print(f"Currently absent files: {len(absent_files)}")

# Build search targets:
# 1. full paths of absent files (e.g. docs/evidence-summary/M01-closure.json)
# 2. basenames of absent files (e.g. M01-closure.json, STATUS-LEDGER.md, WITNESS-REPORT-W2-2026-09-11.md)
# 3. general keywords: circuit-closures, STATUS-LEDGER, witness-report, etc.

# We only want basenames that are specific enough (not generic like "summary.json", "health.json", "empty.env", "cleanup.json")
generic_names = {
    "summary.json", "health.json", "empty.env", "cleanup.json", "root.json",
    "git-status.txt", "common_paths.json", "report.json", "evidence.json",
    "trace.jsonl", "audit.jsonl", "checkpoints.jsonl", "queue.csv", "queue.jsonl"
}

specific_basenames = {}
for path in absent_files:
    bname = os.path.basename(path)
    if bname not in generic_names and len(bname) > 4:
        specific_basenames[bname] = path

print(f"Specific basenames to search: {len(specific_basenames)}")

findings = []

# Scan tracked files (excluding .agents/ directory to focus on repo source & docs, though we can also check .agents/)
# Actually let's check tracked files.
for rel_path in tracked_files:
    # Skip binary files or big files if any
    try:
        with open(rel_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        continue

    for line_idx, line in enumerate(lines, 1):
        # Check for "reports/" or "archive/" or specific patterns
        # 1. Match "reports/" or "archive/" references
        if "reports/" in line or "archive/" in line or "circuit-closures" in line or "STATUS-LEDGER" in line or "witness" in line.lower():
            # Check if it actually refers to a deleted path or pattern
            matched_items = []
            for path in absent_files:
                if path in line:
                    matched_items.append(("full_path", path))
                elif os.path.basename(path) in line and os.path.basename(path) in specific_basenames:
                    matched_items.append(("basename", path))

            # Also pattern matches: M\d\d?-closure
            m_closures = re.findall(r"M\d{1,2}-closure(?:\.json)?", line)
            if m_closures:
                for mc in m_closures:
                    matched_items.append(("pattern", mc))

            # STATUS-LEDGER
            if "STATUS-LEDGER" in line:
                matched_items.append(("pattern", "STATUS-LEDGER"))

            # witness report
            if re.search(r"WITNESS-REPORT", line, re.I):
                matched_items.append(("pattern", "WITNESS-REPORT"))

            if matched_items:
                findings.append({
                    "file": rel_path,
                    "line": line_idx,
                    "content": line.strip(),
                    "matches": list(set([m[1] for m in matched_items]))
                })

# Save findings
out_file = os.path.join(os.path.dirname(__file__), "dangling_findings.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)

print(f"Total dangling reference matches found: {len(findings)}")

# Summarize by file
files_summary = {}
for item in findings:
    files_summary[item["file"]] = files_summary.get(item["file"], 0) + 1

print("\nMatches by file:")
for f, count in sorted(files_summary.items(), key=lambda x: -x[1]):
    print(f"  {f}: {count} matches")
