from __future__ import annotations

from pathlib import Path

path = Path(str(Path(__file__).resolve().parent / "scp" / "runtime" / "judge_parts" / "judge_phases.py"))
lines = path.read_text(encoding="utf-8").splitlines()
anchor = next(i for i, line in enumerate(lines) if 'if hasattr(judge, "antibody_system")' in line)
start = next(i for i in range(anchor, len(lines)) if lines[i].strip() == "if answer:")
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("    except Exception as e:"))
replacement = [
    "        if answer:",
    "            # DomainAntibodySystem exposes check(), not removed check_all().",
    "            # Normalize results so judge metadata remains JSON-safe.",
    "            domain = getattr(ctx, \"domain\", None) or \"general\"",
    "            raw_results = judge.antibody_system.check(",
    "                ctx.question, str(answer), domain=domain",
    "            )",
    "            results = [",
    "                item.to_dict() if hasattr(item, \"to_dict\") else dict(item)",
    "                for item in (raw_results or [])",
    "            ]",
    "            if results:",
    "                triggered = [r for r in results if not r.get(\"passed\", True)]",
    "                ctx.metadata[\"antibody_results\"] = results",
    "                ctx.metadata[\"antibody_triggered\"] = len(triggered)",
    "                if triggered:",
    "                    ctx.warnings.append(f\"antibody_triggered={len(triggered)}\")",
]
lines[start:end] = replacement
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"replaced lines {start + 1}..{end} in {path}")
