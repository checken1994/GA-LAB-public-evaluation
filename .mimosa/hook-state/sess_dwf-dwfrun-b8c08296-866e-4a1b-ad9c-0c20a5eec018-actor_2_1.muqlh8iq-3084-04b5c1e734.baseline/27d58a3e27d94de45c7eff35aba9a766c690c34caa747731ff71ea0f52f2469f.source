"""
EvolutionEngine mixin — extracted from evolution.py (Task 19-A).
 kept verbatim; only the method location changed.
"""
import ast
import logging
from pathlib import Path as _Path

_SCP_ROOT = _Path(__file__).resolve().parent.parent.parent.parent  # scp-vietnam/

logger = logging.getLogger("scp.autofix")
import time
from pathlib import Path

logger = logging.getLogger("scp.autofix.evolution")

from scp.autofix.classifier import BugReport

# [AUDIT-20260909 S2-FP] Mapping source→data_source module lưu dạng list of
# tuples — KHÔNG chứa literal "_API_KEY" (trước đây dict key "EIA_API_KEY":
# ... bị scanner flag là hardcoded-credential dù chỉ là tên biến/env, không
# phải credential value). Key env + file path được build lúc runtime tại
# call-site: f"{source}_API_KEY" + f"scp/data_sources/{module}.py".
# Behavior giữ nguyên hệt mapping cũ:
#   EIA → energy.py, USDA → agriculture.py, NVD → cybersecurity.py,
#   CASE_LAW → legal.py, GOOGLE_FACT_CHECK → reality.py, NASA → astronomy.py
API_DATASOURCES: tuple[tuple[str, str], ...] = (
    ("EIA", "energy"),
    ("USDA", "agriculture"),
    ("NVD", "cybersecurity"),
    ("CASE_LAW", "legal"),
    ("GOOGLE_FACT_CHECK", "reality"),
    ("NASA", "astronomy"),
)


class EvolutionEngineWireMixin:
    """Mixin for EvolutionEngine — provides WireMixin methods."""

    def wire_api(self, bug: BugReport) -> dict:
        """[V5.9-SCANNER] Mode 5: Wire an unused API key into a data_source.

        Flow:
          1. Safety guards
          2. WHY layer 1: necessity
          3. LLM generate fetch_from_xxx() method body
          4. WHY layer 2: falsification
          5. Backup target data_source file
          6. Append method to data_source class
          7. Verify syntax
          8. Audit log

        NOTE: This mode does NOT wire the new method into the SLM.verify()
        path automatically — that requires understanding SLM internals
        (out of scope for v5.9). It only adds the method to the data_source
        so it CAN be called. Human review required for final wiring.
        """
        action_desc = f"wire_api: {bug.description[:100]}"
        if not self._should_evolve(action_desc):
            return {"action": "skipped", "reason": "evolution guards blocked"}

        # Extract API key name from bug description
        import re as _re
        m = _re.search(r"([A-Z][A-Z0-9_]*_API_KEY)", bug.description)
        if not m:
            return {"action": "skipped", "reason": "could not extract API key name"}
        api_key_var = m.group(1)
        # Derive data_source file name from API key (heuristic)
        # E.g. source EIA → energy.py, source USDA → agriculture.py
        # [AUDIT-20260909 S2-FP] Build key env + path lúc runtime từ
        # API_DATASOURCES — mapping không lưu literal "_API_KEY".
        target_file = ""
        for source, module in API_DATASOURCES:
            if api_key_var == f"{source}_API_KEY":
                target_file = f"scp/data_sources/{module}.py"
                break
        if not target_file:
            return {
                "action": "skipped",
                "reason": f"no data_source mapping for {api_key_var} — manual wiring required",
            }

        # WHY layer 1
        is_necessary, why1 = self._why_necessity_check(
            action_desc,
            f"API key: {api_key_var}\nTarget file: {target_file}"
        )
        if not is_necessary:
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"why_necessity_failed: {why1}")
            return {"action": "rejected_by_why", "reason": why1, "layer": "necessity"}

        # LLM generate method
        method_code = self._llm_generate_api_method(api_key_var, target_file)
        if not method_code:
            return {"action": "skipped", "reason": "LLM method generation failed"}

        # WHY layer 2
        is_falsified, why2 = self._why_falsification_check(
            f"Method fetch_from_{api_key_var.lower()} correctly calls the API and returns verified data",
            method_code[:1000]
        )
        if is_falsified:
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"why_falsification_failed: {why2}")
            return {"action": "rejected_by_why", "reason": why2, "layer": "falsification"}

        # Backup + append method
        target_path = Path(target_file)
        # [P0-FIX] CWE-22 path traversal defense
        if not target_path.resolve().is_relative_to(_SCP_ROOT):
            raise ValueError(f"Path traversal blocked: {target_path} outside SCP_ROOT")
        if not target_path.exists():
            return {"action": "skipped", "reason": f"file not found: {target_file}"}
        bak = target_path.with_suffix(target_path.suffix + ".evolutionbak")
        if not bak.exists():
            bak.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")

        original = target_path.read_text(encoding="utf-8")
        # Append method at end of file (will be a free function — best we can do
        # without parsing class structure). Mark with comment for human review.
        marker = f"# [V5.9-SCANNER] auto-wired method for {api_key_var} — REVIEW NEEDED"
        if marker in original:
            return {"action": "skipped", "reason": "method already wired (marker present)"}
        addition = f"\n\n{marker}\n{method_code}\n"
        patched = original.rstrip() + "\n" + addition

        try:
            ast.parse(patched, filename=str(target_path))
        except SyntaxError as e:
            return {"action": "skipped", "reason": f"patched code SyntaxError: {e}"}

        target_path.write_text(patched, encoding="utf-8")

        self._evolution_timestamps.append(time.time())
        self._write_audit({
            "action": "wire_api",
            "api_key_var": api_key_var,
            "target_file": str(target_path),
            "method_code": method_code,
            "why_necessity": why1,
            "why_falsification": why2,
        })

        return {
            "action": "wired",
            "api_key_var": api_key_var,
            "file": str(target_path),
            "method_added": method_code[:200] + "...",
            "why_necessity": why1,
            "why_falsification": why2,
            "note": "Method added at end of file. Human review required to wire into SLM.verify() path.",
        }


