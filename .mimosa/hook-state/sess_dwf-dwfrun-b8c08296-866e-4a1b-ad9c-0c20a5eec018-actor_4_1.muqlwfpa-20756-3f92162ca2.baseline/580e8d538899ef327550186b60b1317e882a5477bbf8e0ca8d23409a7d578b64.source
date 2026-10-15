import os
import re
import sys
from pathlib import Path

deleted_modules = [
    "ai_patterns", "auto_backup", "dependency_resolver", "environment_snapshot",
    "evidence_filter", "file_mutex", "memory_manager", "react_agent",
    "cwe_exploit_store", "issue_parser", "scheduled_crawler", "adversary_verifier",
    "calibration_engine", "curiosity_asker", "question_tracker", "scp_meta",
    "self_questioning", "otel_exporter", "scpv14_process_mixin", "chem_reality_astro",
    "math_biology", "numeric_data", "healing_v14", "parallel_pipeline",
    "timing_and_restart", "auto_payload_generator", "h8_redteam_bridge",
    "kernel_patrol", "quorum_why", "red_team", "rogue_ai_detector", "threat_intel"
]

root = Path("D:/scp")
import_matches = []

search_dirs = ["scp", "tests", "tools", "mini-services"]
for sdir in search_dirs:
    p = root / sdir
    if not p.exists():
        continue
    for f in p.rglob("*.py"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line_num, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for mod in deleted_modules:
                # Check real imports
                if re.search(rf"\bimport\s+[\w\.]*{mod}\b", stripped) or re.search(rf"\bfrom\s+[\w\.]*{mod}\b\s+import", stripped):
                    import_matches.append((str(f.relative_to(root)), line_num, mod, stripped))

print(f"Total active import matches found across codebase: {len(import_matches)}")
for filepath, line_num, mod, line in import_matches:
    print(f"  {filepath}:{line_num} [{mod}] -> {line}")

if len(import_matches) == 0:
    print("SUCCESS: 0 active callers or imports found for all 32 deleted modules!")
    sys.exit(0)
else:
    sys.exit(1)
