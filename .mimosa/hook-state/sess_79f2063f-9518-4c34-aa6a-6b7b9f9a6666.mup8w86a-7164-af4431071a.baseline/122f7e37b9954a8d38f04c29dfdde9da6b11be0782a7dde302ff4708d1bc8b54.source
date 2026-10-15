from __future__ import annotations

from pathlib import Path

path = Path(str(Path(__file__).resolve().parent / "scp" / "api_server.py"))
lines = path.read_text(encoding="utf-8").splitlines()
source_idx = next(i for i, line in enumerate(lines) if '"source": r.get("evidence"' in line)
if any('"evidence": r.get("evidence"' in line for line in lines[source_idx:source_idx + 8]):
    print("evidence already present")
else:
    insert_at = source_idx + 1
    while insert_at < len(lines) and not lines[insert_at].lstrip().startswith('"processing_time_ms"'):
        insert_at += 1
    lines.insert(insert_at, '            "evidence": r.get("evidence", {}) if isinstance(r.get("evidence"), dict) else {},')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("patched slm_trace evidence", path)
