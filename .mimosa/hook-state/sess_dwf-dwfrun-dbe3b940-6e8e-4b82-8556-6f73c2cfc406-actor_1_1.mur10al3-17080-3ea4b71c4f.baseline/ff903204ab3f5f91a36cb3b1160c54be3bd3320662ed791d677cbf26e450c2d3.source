"""
[OPT-27] AutoFix diagnostic — classify failure root cause.

DNA SCP #6 Evidence: when AutoFix fails, need to know WHY.
Classifications:
  - LLM_FAILED_TO_GENERATE: LLM returned empty/no output
  - LLM_OUTPUT_FORMAT_ERROR: LLM output doesn't match SEARCH/REPLACE format
  - PATCH_VALIDATION_FAILED: Patch parsed but validation failed (search not found, syntax error, dangerous)
  - PATCH_APPLIED_BUT_FAILED_TESTS: Patch applied but tests failed → rollback
  - PATTERN_FIX_SKIPPED: Bug type skipped (e.g., BareExceptPass)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("scp.autofix.diagnostic")


@dataclass
class DiagnosticReport:
    bug_id: str
    bug_type: str
    llm_output_received: bool = False
    patch_parsed: bool = False
    patch_validated: bool = False
    patch_applied: bool = False
    rollback_occurred: bool = False
    diagnosis: str = ""
    root_cause: str = ""
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "bug_id": self.bug_id,
            "bug_type": self.bug_type,
            "llm_output_received": self.llm_output_received,
            "patch_parsed": self.patch_parsed,
            "patch_validated": self.patch_validated,
            "patch_applied": self.patch_applied,
            "rollback_occurred": self.rollback_occurred,
            "diagnosis": self.diagnosis,
            "root_cause": self.root_cause,
            "suggestions": self.suggestions,
        }


def diagnose_fix_failure(
    bug_id: str,
    bug_type: str,
    llm_output: str | None,
    patch_parsed: dict | None,
    validation_result: dict | None,
    apply_result: str | None,  # "success" | "rollback" | "skipped" | "failed"
) -> DiagnosticReport:
    """Classify why an AutoFix attempt failed.

    Args:
        bug_id: Unique bug identifier
        bug_type: Type of bug (BareExceptPass, SQLInjection, etc.)
        llm_output: Raw LLM response (None if LLM failed)
        patch_parsed: Parsed patch dict {search, replace} or None
        validation_result: Validation result dict or None
        apply_result: Final apply result

    Returns:
        DiagnosticReport with diagnosis + root_cause + suggestions
    """
    report = DiagnosticReport(bug_id=bug_id, bug_type=bug_type)
    report.llm_output_received = bool(llm_output)
    report.patch_parsed = bool(patch_parsed)
    report.patch_validated = bool(validation_result and validation_result.get("valid"))
    report.patch_applied = apply_result == "success"
    report.rollback_occurred = apply_result == "rollback"

    # Classify
    if apply_result == "skipped":
        report.diagnosis = "PATTERN_FIX_SKIPPED"
        report.root_cause = f"Bug type {bug_type} is exempt from auto-fix"
        report.suggestions = ["Manual review required"]
    elif not llm_output:
        report.diagnosis = "LLM_FAILED_TO_GENERATE"
        report.root_cause = "LLM returned empty or None"
        report.suggestions = [
            "Check LLM provider is enabled (Ollama multi-model + OpenRouter)",
            "Check API key is valid (OpenRouter)",
            "Check rate limit not exceeded",
            "Verify Ollama has expected models: deepseek-r1:8b, qwen2.5:7b, llama3.2",
        ]
    elif not patch_parsed:
        report.diagnosis = "LLM_OUTPUT_FORMAT_ERROR"
        report.root_cause = "LLM output doesn't match SEARCH/REPLACE format"
        report.suggestions = [
            "Improve prompt with clearer format instructions",
            "Add few-shot examples to prompt",
            "Use stronger LLM (Claude/GPT-4) for complex bugs",
            "Check _extract_search_replace_block() regex",
        ]
    elif not report.patch_validated:
        report.diagnosis = "PATCH_VALIDATION_FAILED"
        if validation_result:
            report.root_cause = validation_result.get("reason", "Unknown validation failure")
        report.suggestions = [
            "Check SEARCH block matches actual file content (indent, whitespace)",
            "Check REPLACE block has valid Python syntax",
            "Check REPLACE doesn't contain dangerous patterns",
            "Verify file hasn't been modified since scan",
        ]
    elif report.rollback_occurred:
        report.diagnosis = "PATCH_APPLIED_BUT_FAILED_TESTS"
        report.root_cause = "Patch applied but introduced new bugs or failed tests"
        report.suggestions = [
            "Review patch for completeness — may not fix root cause",
            "Check if patch introduces new bug type (e.g., new BareExceptPass)",
            "Add more test cases to catch regressions",
            "Consider manual review for this bug type",
        ]
    elif apply_result == "success":
        report.diagnosis = "SUCCESS"
        report.root_cause = "Fix applied successfully"
    else:
        report.diagnosis = "UNKNOWN_FAILURE"
        report.root_cause = f"Unrecognized apply_result: {apply_result}"
        report.suggestions = ["Check logs for more details"]

    logger.info(f"[Diagnostic] {bug_id} ({bug_type}): {report.diagnosis} — {report.root_cause}")
    return report


__all__ = ["diagnose_fix_failure", "DiagnosticReport"]
