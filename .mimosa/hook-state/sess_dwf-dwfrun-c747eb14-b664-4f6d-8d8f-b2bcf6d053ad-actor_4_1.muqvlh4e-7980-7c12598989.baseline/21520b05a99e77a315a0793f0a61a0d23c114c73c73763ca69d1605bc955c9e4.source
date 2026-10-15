import json
from pathlib import Path

from scp.autofix.llm_fix import _generate_bare_except_fix


class Bug:
    bug_type = "BareExceptPass"
    file = str(Path(__file__).resolve().parent.parent / "scp" / "autofix" / "type_flow_verifier.py")
    line = 717


patch = _generate_bare_except_fix(Bug())
print(json.dumps({
    "status": "PASS" if patch else "EMPTY",
    "patch_len": len(patch or ""),
    "patch_prefix": (patch or "")[:180],
}, ensure_ascii=True))
