#!/usr/bin/env python3
"""Reality test: AutoFix provider calls use the canonical file-backed key contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
wrapper = (root / "scp/autofix/llm_fix.py").read_text(encoding="utf-8")
openrouter_part = (
    root / "scp/autofix/llm_fix_parts/_call_openrouter.py"
).read_text(encoding="utf-8")
provider_keys = (root / "scp/security/provider_keys.py").read_text(encoding="utf-8")

# GOD split invariant: the public wrapper owns composition; the extracted
# provider-call module owns provider credential loading.
assert "from .llm_fix_parts import _call_openrouter as _p_openrouter" in wrapper
assert "_call_openrouter = _p_openrouter._call_openrouter" in wrapper
for marker in ["load_openrouter_keys", "ProviderCredentialError"]:
    assert marker in openrouter_part, marker
for marker in ["file_env = f\"{slot}_FILE\"", "_FILE", "Path(file_ref)"]:
    assert marker in provider_keys, marker

print("PASS [1]: AutoFix wrapper wires the extracted provider-call implementation")
print("PASS [2]: provider-call implementation uses the canonical credential loader")
print("PASS [3]: provider loader supports file-backed key references")
print("Reality test 4-d-030 PASSED")
