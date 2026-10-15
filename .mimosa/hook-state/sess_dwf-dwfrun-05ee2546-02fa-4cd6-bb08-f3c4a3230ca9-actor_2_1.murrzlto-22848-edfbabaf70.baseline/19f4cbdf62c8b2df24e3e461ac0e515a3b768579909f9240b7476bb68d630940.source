import subprocess
import os
import json

with open(".agents/spec_miner_o6_survey_3/deleted_files_87d78da.txt", encoding="utf-8") as f:
    deleted_files = [line.strip() for line in f if line.strip()]

absent_files = [f for f in deleted_files if not os.path.exists(f)]

all_hits = {}

# Search for the exact path of each absent file in git grep
for path in absent_files:
    try:
        res = subprocess.run(
            ["git", "grep", "-n", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().splitlines()
            all_hits[path] = lines
    except Exception as e:
        pass

with open(".agents/spec_miner_o6_survey_3/exact_path_hits.json", "w", encoding="utf-8") as out:
    json.dump(all_hits, out, indent=2)

print(f"Successfully wrote {len(all_hits)} exact path hits to exact_path_hits.json")
