from __future__ import annotations

from pathlib import Path

path = Path(str(Path(__file__).resolve().parent / "scp" / "runtime" / "judge_parts" / "judge_phases.py"))
text = path.read_text(encoding="utf-8")
old = '            results = judge.antibody_system.check_all(ctx.question, str(answer))\n'
new = '''            # DomainAntibodySystem exposes check(), not the removed check_all().
            # Normalize result objects so the judge metadata stays JSON-safe.
            domain = getattr(ctx, "domain", None) or "general"
            raw_results = judge.antibody_system.check(
                ctx.question, str(answer), domain=domain
            )
            results = [
                item.to_dict() if hasattr(item, "to_dict") else dict(item)
                for item in (raw_results or [])
            ]
'''
if text.count(old) != 1:
    raise SystemExit(f"expected one check_all call, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched", path)
