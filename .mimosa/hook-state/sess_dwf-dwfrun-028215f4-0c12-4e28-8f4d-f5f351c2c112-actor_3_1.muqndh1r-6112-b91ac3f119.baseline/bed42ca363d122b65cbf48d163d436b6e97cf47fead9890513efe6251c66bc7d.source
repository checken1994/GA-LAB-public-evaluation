"""
[OPT-14] ExternalTrustRoot — Gà §8: "Gốc tin cậy bên ngoài"

WHY re-implement: was 9-line stub returning True always.
Proper implementation needs:
  - Verify external audit tests exist and pass
  - Verify CI/CD pipeline exists
  - Verify constitution file exists and is human-approved
  - Check file integrity (hasn't been modified by SCP)

Wired into: scp/api_server.py (startup check — if external trust broken, warn)
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("scp.meta.external_trust")

# [SCP-DNA-FIX 4-b-003] Strict HUMAN_APPROVED_BY line-1 marker.
# TẠI SAO: previously HUMAN_APPROVED_MARKERS was a tuple of substrings
# ("HUMAN_APPROVED", "# human-approved", "# human_reviewed", "Copyright (c) 2026")
# matched ANYWHERE in the constitution file. Any of these substrings — including
# an auto-added copyright notice — passed the "human-approved" check. The trust
# root was forgeable by SCP itself (DNA #6 violation; DNA #22 PASS≠TRUE).
# Fix: require an explicit `# HUMAN_APPROVED_BY: <name> <YYYY-MM-DD>` line as
# the FIRST non-empty/non-shebang line of the file. Case-sensitive, name
# non-empty, date must be a valid YYYY-MM-DD.
HUMAN_APPROVED_PATTERN = re.compile(
    r'^#\s*HUMAN_APPROVED_BY:\s*(\S+)\s+(\d{4}-\d{2}-\d{2})\s*$'
)

# Deprecated markers from the pre-Fix-4-b-003 substring check. Kept ONLY for
# emitting a migration warning when an old-format constitution is detected
# (so operators know to migrate). They are NOT used to grant approval.
_DEPRECATED_HUMAN_APPROVED_SUBSTRINGS = (
    "# human-approved",
    "# human_reviewed",
)


class ExternalTrustRoot:
    """Gà §8: External trust root — SCP cannot self-verify, needs external anchors.

    3 external trust roots:
      1. tests/external_audit/ — independent tests (no SCP imports)
      2. CI/CD pipeline — GitHub Actions (external)
      3. Constitution — human-approved, SCP cannot modify
    """

    EXPECTED_FILES = [
        "tests/external_audit/test_cascade.py",
        "tests/external_audit/test_security.py",
        "tests/external_audit/conftest.py",
        ".github/workflows/",  # CI/CD
        "meta/constitution.py",  # Constitution
    ]

    # [SCP-DNA-FIX 4-b-003] Approval is now granted ONLY by the strict
    # HUMAN_APPROVED_PATTERN (line-1 marker) — see module-level constant.
    # The previous substring-based HUMAN_APPROVED_MARKERS tuple is GONE.
    # 'Copyright (c) 2026' is NOT an approval signal — it is an auto-added
    # copyright notice that the old substring check mistakenly trusted.
    #
    # Deprecated markers are tracked in _DEPRECATED_HUMAN_APPROVED_SUBSTRINGS
    # (module level) to emit migration warnings when old-format constitutions
    # are detected. They do NOT grant approval.

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self._baseline_hashes: dict[str, str] = {}

    def _resolve_expected_path(self, expected: str) -> Path:
        """Resolve an anchor from either the repository root or the scp package root.

        The desktop starts from the repository root, while some maintenance commands
        start inside ``scp``. The old code assumed one current working directory and
        produced a false warning even when the anchors existed.
        """
        direct = self.project_root / expected
        if direct.exists():
            return direct
        package_relative = self.project_root / "scp" / expected
        if package_relative.exists():
            return package_relative
        return direct

    def verify_external(self) -> dict:
        """Verify all external trust roots exist + intact.

        Returns dict with:
          - passed: bool (all checks passed)
          - checks: list of individual check results
          - missing: list of missing files
        """
        checks = []
        missing = []
        for expected in self.EXPECTED_FILES:
            path = self._resolve_expected_path(expected)
            exists = path.exists()
            checks.append({
                "file": expected,
                "exists": exists,
                "type": "dir" if expected.endswith("/") else "file",
            })
            if not exists:
                missing.append(expected)

        # Check constitution is human-approved (strict line-1 marker).
        # [SCP-DNA-FIX 4-b-003] Was: substring match against 4 markers,
        # forgeable by SCP itself (auto-added copyright notice passed).
        # Now: requires `# HUMAN_APPROVED_BY: <name> <YYYY-MM-DD>` as the
        # FIRST non-empty/non-shebang line. Substring matches NOT accepted.
        constitution_path = self._resolve_expected_path("meta/constitution.py")
        constitution_approved = False
        if constitution_path.exists():
            content = constitution_path.read_text(encoding="utf-8")
            constitution_approved = self._is_constitution_human_approved(content)
            if not constitution_approved:
                # Migration warning: detect old-format markers and warn operators
                # to migrate. Do NOT auto-approve (DNA #22 — claim ≠ true).
                content_lower = content.lower()
                has_deprecated = any(
                    m in content_lower
                    for m in _DEPRECATED_HUMAN_APPROVED_SUBSTRINGS
                ) or "human_approved" in content_lower
                if has_deprecated:
                    logger.warning(
                        "[external_trust] Constitution has a deprecated "
                        "human-approval marker (substring format) but does NOT "
                        "have the strict line-1 '# HUMAN_APPROVED_BY: <name> "
                        "<YYYY-MM-DD>' marker. Constitution is NOT approved. "
                        "Migration: add the strict marker as line 1 (after any "
                        "shebang). DNA #6/#22 — substring is forgeable."
                    )

        checks.append({
            "file": "constitution.py",
            "check": "human_approved",
            "passed": constitution_approved,
        })

        passed = len(missing) == 0 and constitution_approved
        return {
            "passed": passed,
            "checks": checks,
            "missing": missing,
            "constitution_approved": constitution_approved,
        }

    def _is_constitution_human_approved(self, content: str) -> bool:
        """Constitution is human-approved IFF line 1 (after shebang/blank lines)
        matches the strict HUMAN_APPROVED_BY pattern.

        Substring matches are NOT accepted — DNA #6: trust root must not be
        forgeable by the system itself. DNA #22: PASS≠TRUE — a substring match
        is a claim, not a verification.

        Required format (case-sensitive, exactly):
            # HUMAN_APPROVED_BY: <name> <YYYY-MM-DD>

        Args:
            content: Full text of the constitution file.

        Returns:
            True only if line 1 (first non-empty, non-shebang line) matches
            the strict pattern AND the date is parseable. False otherwise.
        """
        if not content:
            return False
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#!"):
                continue
            m = HUMAN_APPROVED_PATTERN.match(stripped)
            if not m:
                # First real line is NOT the approval marker → not approved.
                return False
            # Validate date is parseable.
            try:
                datetime.strptime(m.group(2), "%Y-%m-%d")
            except ValueError as exc:
                # silent-by-design: unparseable date means the candidate does not validate, by contract.
                logger.debug("external_trust: date validation failed: %s", exc, exc_info=True)
                return False
            return True
        return False

    def get_baseline_hash(self, file_path: str) -> str | None:
        """Get baseline hash of a file (for tamper detection)."""
        path = self._resolve_expected_path(file_path)
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def verify_integrity(self, file_path: str, expected_hash: str) -> bool:
        """Verify file hasn't been tampered with (matches expected hash)."""
        actual = self.get_baseline_hash(file_path)
        if not actual:
            return False
        return actual == expected_hash

    def establish_baseline(self, file_paths: list[str]) -> dict[str, str]:
        """Establish baseline hashes for tamper detection.

        Call this once after human review — store hashes externally.
        """
        baselines = {}
        for fp in file_paths:
            h = self.get_baseline_hash(fp)
            if h:
                baselines[fp] = h
        self._baseline_hashes = baselines
        return baselines

    # ---- [SCP-DNA-FIX R13-3 BUG-009] Public tamper-detection API ----
    # R5 added verify_integrity + establish_baseline but vulture found 0 callers
    # → hashes were computed and stored but NEVER compared. Attacker who edits
    # the constitution or external_audit tests is NEVER detected. Below are
    # the public methods that a scheduler (startup + 24h cron) should call.
    #
    # TODO(parent — scp/api_server_parts/lifespan.py owner): wire this into the FastAPI
    # lifespan startup + a 24h recurring task:
    #     from scp.meta.external_trust import get_external_trust_root
    #     trust = get_external_trust_root()
    #     # On startup: register all anchor files + verify
    #     for f in trust.EXPECTED_FILES:
    #         if not f.endswith("/"):
    #             trust.register_file(f)
    #     results = trust.verify_all_baselines()
    #     if not all(results.values()):
    #         logger.error(f"[external_trust] TAMPER DETECTED: {results}")
    #     # Schedule: every 24h call trust.verify_all_baselines() and alert on
    #     # any False.
    # Until the lifespan wires this in, callers can invoke the API directly.
    def register_file(self, file_path: str) -> bool:
        """Register a single anchor file for tamper detection.

        Computes the current SHA-256 hash of the file and stores it as the
        baseline. Future calls to `verify_all_baselines()` will compare
        against this hash. Idempotent: re-registering the same file refreshes
        the baseline.

        Args:
            file_path: Path relative to project_root (e.g.,
                "scp/meta/constitution.py").

        Returns:
            True if the baseline was stored; False if the file does not
            exist (in which case no baseline is recorded).
        """
        h = self.get_baseline_hash(file_path)
        if not h:
            logger.warning(f"[external_trust] register_file: '{file_path}' does not exist — no baseline stored")
            return False
        self._baseline_hashes[file_path] = h
        logger.info(f"[external_trust] baseline registered for {file_path} (hash={h[:12]}...)")
        return True

    def verify_all_baselines(self) -> dict[str, bool]:
        """Verify all registered anchor files match their baseline hashes.

        Iterates every file registered via `register_file()` /
        `establish_baseline()` and calls `verify_integrity()` on each. Use
        this on startup + every 24h to detect tampering with constitution,
        external_audit tests, or any other anchor file.

        Returns:
            Dict mapping file_path → bool (True if hash matches baseline,
            False if mismatch or file missing). Empty dict if no files
            have been registered.
        """
        results: dict[str, bool] = {}
        # Snapshot under no-lock (single-threaded lifespan context); the
        # underlying verify_integrity is itself lock-safe via Path ops.
        for file_path, expected_hash in list(self._baseline_hashes.items()):
            ok = self.verify_integrity(file_path, expected_hash)
            results[file_path] = ok
            if not ok:
                logger.error(
                    f"[external_trust] TAMPER DETECTED: '{file_path}' "
                    f"hash mismatch (expected={expected_hash[:12]}...)"
                )
        return results

    def stats(self) -> dict:
        verification = self.verify_external()
        return {
            "passed": verification["passed"],
            "missing_count": len(verification["missing"]),
            "constitution_approved": verification["constitution_approved"],
            "baseline_files": len(self._baseline_hashes),
        }


# Module-level singleton — used by api_server lifespan() at startup.
_external_trust_root: ExternalTrustRoot | None = None


def get_external_trust_root(project_root: str = ".") -> ExternalTrustRoot:
    """Get the singleton ExternalTrustRoot instance."""
    global _external_trust_root
    if _external_trust_root is None:
        _external_trust_root = ExternalTrustRoot(project_root)
    return _external_trust_root


__all__ = ["ExternalTrustRoot", "get_external_trust_root"]
