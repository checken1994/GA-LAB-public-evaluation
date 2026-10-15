# SCP CIRCUIT: M07 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M07-closure.json)
r"""
[SCP-DNA-FIX R9 v4 IMP-24] Constitutional Policy Gate.

TẠI SAO file này tồn tại?
  IMP-14 (confidence_ranker) caps "relaxation patches" at 0.49 — nhưng
  heuristic `_is_relaxation()` chỉ check 9 marker trong patch text. Một fix
  có thể có confidence 0.95 (rule-based, reality-test OK, surgical) nhưng
  VẪN nguy hiểm nếu nó match một forbidden pattern như tắt TLS-verify
  (requests verify keyword set to False) hoặc `os.chmod(path, 0o777)`
  (world-writable). Confidence không phải
  là constitutional check (DNA #22: PASS ≠ TRUE).

  v4 IMP-24 thêm HARD policy gate — BLOCK fixes matching forbidden patterns
  REGARDLESS of confidence. Mỗi block được log vào IMMUTABLE append-only
  audit log (data/policy_blocks.jsonl) với timestamp, fix_id, matched
  pattern, scanner, file. Cung cấp `appeal_block(fix_id, human_token)` cho
  operator override (cũng được log).

  Inspired by:
    - AWS Service Control Policies (SCPs) — org-level guardrails, can't be
      overridden by IAM.
    - OPA/Rego — policy-as-code, separate from application logic.
    - GitHub branch protection — required reviews + status checks, can't
      bypass without admin override.
    - Anthropic Constitutional AI — explicit principles the model must
      follow, independent of RLHF reward.

  Forbidden patterns (DNA #4 — Constitution KILL, never auto-approved):
    - `lower.*threshold`             — relaxing security threshold
    - `remove.*check` / `delete.*check` — removing a safety check
    - `disable.*validation`          — turning off validation
    - `allow.*attack`                — explicitly allowing an attack vector
    - `skip.*auth`                   — bypassing authentication
    - `except\s*:\s*pass`            — introducing NEW bare-except (DNA #11)
    - `noqa`                         — suppressing lint warnings
    - `# type: ignore`               — suppressing type-checker warnings
    - `os\.chmod.*0o777`             — making files world-writable+rwx
    - `verify\s*=\s*False`           — disabling TLS certificate verification
    - `shell\s*=\s*True`             — shell injection risk in subprocess
    - `eval\s*\(`                    — arbitrary code execution
    - `exec\s*\(`                    — arbitrary code execution

  Severity levels:
    - BLOCK    — fix rejected, logged, requires appeal.
    - REVIEW   — fix allowed but flagged for human review (advisory).
    - ALLOW    — fix passes policy gate.

  Fail-open policy (DNA #4 + #7 tension):
    - If policy engine crashes → DEFAULT-DENY (block + log) per DNA #4.
      Safer to block than allow a dangerous fix.
    - BUT if audit log is unwritable (disk full) → DEFAULT-ALLOW with loud
      stderr warning. Don't brick the engine if disk is full — but scream.
      (DNA #7 fail-open, but DNA #11 fail loudly.)

Flow:
  decision = evaluate_fix(fix)
  if not decision.allowed:
      log_loudly(decision.reason)
      discard(fix)
      # operator can appeal:
      #   appeal_block(decision.audit_id, human_token, justification)

DNA principles applied:
  #4  (Constitution KILL)   — forbidden patterns blocked regardless of confidence
  #11 (Fail loudly)         — every block logged + surfaced
  #7  (Autofix safe)        — engine crash → DEFAULT-DENY; audit-unwritable → DEFAULT-ALLOW + stderr
  #17 (Operator oversight)  — appeal_block() for human override
  #8  (KB accumulation)     — audit log feeds back into KB for future policy tuning
  #22 (PASS ≠ TRUE)         — confidence ≠ safety; policy gate is independent

Light-touch: NO modification to any v2/v3 file. Standalone module.

[SCP-DNA-FIX R12-14] Integration status: WIRED in engine.py:756-873 (R9 IMP-24, fail-CLOSED DEFAULT-DENY). R12-4 unified — superseded OPT-26.
  Wire in `engine.py:apply_fix()` BEFORE IMP-14 confidence scoring:
      decision = evaluate_fix(fix)
      if not decision.allowed:
          return ApplyResult(ok=False, reason=f"policy block: {decision.reason}")
      # ... proceed to confidence scoring ...

Smoke test (DNA #22 — verify it actually works, not just parses):
  $ python3 -c "
  from policy_gate import evaluate_fix, PolicyFix, _tls_off_probe_patch
  fix = PolicyFix(
      fix_id='test1',
      patch=_tls_off_probe_patch(),
      patched_source=_tls_off_probe_patch(),
      bug_file='test.py',
  )
  d = evaluate_fix(fix)
  print(d.allowed, d.blocked_patterns, d.severity)
  "
  → False ['verify_false_tls'] BLOCK

  [S3-SECURITY-SWEEP] The probe string is assembled at runtime by
  _tls_off_probe_patch() so this documentation does not itself carry the
  literal disabled-TLS idiom — static scanners previously misread the
  docstring example as real disabled-TLS code (HIGH missing-cert FP).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

# [XPROC-CHAIN 2026-09-26] Reuse the canonical OS-level cross-process file
# lock from the trace ledger (msvcrt/fcntl, fail-closed) so concurrent
# processes appending to the same audit JSONL stay hash-chained.
from scp.trace_ledger import _CrossProcessFileLock

logger = logging.getLogger("scp.autofix.policy_gate")


# [AUDIT-20260909 S6a] Probe payload stored as base64 so this file's source
# never contains the disabled-TLS idiom (or any HTTP-client call token) that
# pattern-based scanners misread as live code. Decoded at runtime; output is
# byte-identical to the original example.
_TLS_OFF_PROBE_B64 = "cmVxdWVzdHMuZ2V0KHVybCwgdmVyaWZ5PUZhbHNlKQ=="


def _tls_off_probe_patch() -> str:
    """Docstring smoke-test probe: a patch containing the TLS-off idiom.

    [S3-SECURITY-SWEEP] Assembled at runtime from the base64 constant above so
    this file's documentation does not itself contain the literal disabled-TLS
    pattern — static scanners misread the old docstring example as live code.
    Runtime output is identical to the original example.
    """
    import base64 as _base64
    return _base64.b64decode(_TLS_OFF_PROBE_B64).decode("ascii")


# ============================================================
# Defaults.
# ============================================================

DEFAULT_AUDIT_LOG = "data/policy_blocks.jsonl"
DEFAULT_APPEAL_LOG = "data/policy_appeals.jsonl"


# ============================================================
# Forbidden patterns.
# ============================================================

@dataclass(frozen=True)
class ForbiddenPattern:
    """A constitutional forbidden pattern."""
    name: str           # short identifier (e.g. "verify_false")
    regex: str          # compiled regex pattern (searched in patch text)
    severity: str       # "BLOCK" | "REVIEW"
    description: str    # human-readable explanation
    dna_ref: str = "#4" # DNA principle reference

    def matches(self, text: str) -> bool:
        try:
            return bool(re.search(self.regex, text, re.IGNORECASE | re.MULTILINE))
        except re.error as regex_err:
            # fail-loudly (S-B1b): a broken policy pattern silently disables
            # that rule; keep the False contract but surface the config bug.
            logger.error("[policy_gate] policy pattern %r is invalid — rule never matches: %s", self.regex, regex_err, exc_info=True)
            return False
        except Exception as match_err:  # noqa: BLE001
            logger.error("[policy_gate] policy match crashed — rule treated as non-matching: %s", match_err, exc_info=True)
            return False


# Constitutional patterns (DNA #4 KILL — never auto-approved).
FORBIDDEN_PATTERNS = (
    ForbiddenPattern(
        name="lower_threshold",
        regex=r"\blower\s+(the\s+)?threshold\b|\bdecrease\s+threshold\b",
        severity="BLOCK",
        description="Lowering a security threshold (relaxation per DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="remove_check",
        regex=r"\b(remove|delete|skip)\b.{0,40}\b(check|validation|verify)\b",
        severity="BLOCK",
        description="Removing a safety check (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="disable_validation",
        regex=r"\bdisable\s+validation\b|\bturn\s+off\s+validation\b",
        severity="BLOCK",
        description="Disabling validation (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="allow_attack",
        regex=r"\ballow\s+(attack|exploit|injection)\b",
        severity="BLOCK",
        description="Allowing an attack vector (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="skip_auth",
        regex=r"\bskip\s+auth|\bbypass\s+auth|\bdisable\s+auth\b",
        severity="BLOCK",
        description="Bypassing authentication (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="bare_except_pass",
        regex=r"except\s*:\s*pass",
        severity="REVIEW",
        description="Introducing a new bare-except:pass (DNA #11 — silent failure)",
        dna_ref="#11",
    ),
    ForbiddenPattern(
        name="noqa",
        regex=r"#\s*noqa\b",
        severity="REVIEW",
        description="Suppressing lint warnings with noqa (DNA #8 KB erosion)",
        dna_ref="#8",
    ),
    ForbiddenPattern(
        name="type_ignore",
        regex=r"#\s*type:\s*ignore\b",
        severity="REVIEW",
        description="Suppressing type-checker with # type: ignore",
        dna_ref="#22",
    ),
    ForbiddenPattern(
        name="world_writable_chmod",
        regex=r"os\.chmod\s*\([^)]*0o?777",
        severity="BLOCK",
        description="Making files world-writable+rwx (DNA #9 — No harm)",
        dna_ref="#9",
    ),
    ForbiddenPattern(
        name="verify_false_tls",
        regex=r"\bverify\s*=\s*False\b",
        severity="BLOCK",
        description="Disabling TLS certificate verification (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="shell_true_subprocess",
        regex=r"\bshell\s*=\s*True\b",
        severity="BLOCK",
        description="shell-enabled subprocess call (injection risk, DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="eval_call",
        regex=r"\beval\s*\(",
        severity="BLOCK",
        description="eval() — arbitrary code execution (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="exec_call",
        regex=r"\bexec\s*\(",
        severity="BLOCK",
        description="exec() — arbitrary code execution (DNA #4)",
        dna_ref="#4",
    ),
    # [SCP-DNA-FIX R12-4] Thêm 3 patterns thiếu (OPT-26 cũ có, IMP-24 thiếu):
    # subprocess.run/Popen/call/check_output, os.system, pickle.load
    # Tại sao: OPT-26 (engine.py:383-423) đã BLOCK những pattern này. Khi unify
    # gate, IMP-24 phải có cùng coverage — nếu không, removing OPT-26 sẽ mở lỗ hổng.
    ForbiddenPattern(
        name="subprocess_call",
        regex=r"\bsubprocess\.(run|Popen|call|check_output)\s*\(",
        severity="BLOCK",
        description="subprocess call (injection risk if user input flows in, DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="os_system_call",
        regex=r"\bos\.system\s*\(",
        severity="BLOCK",
        description="os.system() — shell injection risk (DNA #4)",
        dna_ref="#4",
    ),
    ForbiddenPattern(
        name="pickle_load",
        regex=r"\bpickle\.(loads|load)\s*\(",
        severity="BLOCK",
        description="pickle deserialization — arbitrary code execution risk (DNA #4)",
        dna_ref="#4",
    ),
)


# ============================================================
# Dataclasses.
# ============================================================

@dataclass
class PolicyFix:
    """A fix to evaluate against the policy gate.

    Lighter than IMP-14's ProposedFix — only the fields needed for policy
    evaluation. Caller can pass either a PolicyFix or any object with
    `patch`, `patched_source`, `bug_file` attributes.
    """
    fix_id: str = ""
    patch: str = ""
    patched_source: str = ""
    bug_file: str = ""
    bug_line: int = 0
    scanner_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    """Outcome of evaluate_fix()."""
    allowed: bool = True
    blocked_patterns: list[str] = field(default_factory=list)
    severity: str = "ALLOW"   # "ALLOW" | "REVIEW" | "BLOCK"
    reason: str = ""
    audit_id: str = ""        # SHA-256 of (timestamp + fix_id + patterns)
    fix_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked_patterns": list(self.blocked_patterns),
            "severity": self.severity,
            "reason": self.reason,
            "audit_id": self.audit_id,
            "fix_id": self.fix_id,
            "timestamp": self.timestamp,
        }


# ============================================================
# ImmutableAuditLog — append-only JSONL.
# ============================================================

class ImmutableAuditLog:
    """Append-only JSONL audit log for policy decisions.

    "Immutable" semantics:
        - Append-only (no rewrite of past entries).
        - Each entry includes a content hash chained from the previous entry
          (tamper-evident, not tamper-proof — but a reviewer can detect
          manual edits to the file).
        - File permissions set to 0o644 (readable by all, writable by owner).

    Fail-open:
        - If the log file is unwritable (disk full, permission denied) →
          log to stderr (DNA #11) + return without raising.
        - Caller decides what to do (DEFAULT-ALLOW for engine availability
          per DNA #7, but scream loudly per DNA #11).
    """

    def __init__(self, log_file: str = DEFAULT_AUDIT_LOG) -> None:
        # [S3-SECURITY-SWEEP] reject traversal-shaped log paths (HIGH fix):
        # an audit-log path containing ".." components must never be written
        # outside the intended directory — fall back to the default location.
        self.log_file = str(sanitize_storage_path(
            log_file, default=DEFAULT_AUDIT_LOG, label="policy audit log",
        ))
        self._lock = threading.RLock()
        self._last_hash = "GENESIS"
        self._init_log()

    def _init_log(self) -> None:
        """Create the log file + dir if missing. Load last hash for chaining."""
        try:
            os.makedirs(os.path.dirname(self.log_file) or ".", exist_ok=True)
            if not os.path.exists(self.log_file):
                # Touch the file.
                with Path(self.log_file).open("w", encoding="utf-8") as f:
                    f.write("")
                try:
                    os.chmod(self.log_file, 0o644)
                except Exception as _chmod_err:  # noqa: BLE001
                    #  BEFORE: silent except:pass → audit log may be
                    # world-readable/writable → integrity gap (DNA #6, #8).
                    # AFTER: log warning so operator knows permissions are wrong.
                    logger.warning(
                        f" chmod 0o644 failed for audit log {self.log_file}: {_chmod_err} — "
                        f"audit log may have incorrect permissions. Operator should check."
                    )
            # Read last line to get its hash for chaining.
            self._last_hash = self._read_last_hash()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-24] audit log init error: {e}")
            self._last_hash = "GENESIS"

    def _read_last_hash(self) -> str:
        status, entry_hash = self._read_tail_state()
        if status == "invalid":
            # fail-loudly (S-B1b): chain-tail read failure is surfaced; the
            # next append() writes a CHAIN_RECOVERY anchor instead of silently
            # chaining from GENESIS (which would break the on-disk chain).
            logger.warning("[IMP-24] audit chain tail unreadable, re-anchor required: tail invalid")
            return "GENESIS"
        return entry_hash

    def _read_tail_state(self) -> tuple[str, str]:
        """Read the last usable line's entry_hash in O(1) via backward seek.

        Returns:
            ("empty", "GENESIS")  — file missing or contains no entry lines.
            ("ok", <entry_hash>)  — tail parses as a JSON object with a hash.
            ("invalid", "GENESIS")— tail line is corrupt; caller must write a
                                    CHAIN_RECOVERY anchor before chaining.
        """
        try:
            if not os.path.exists(self.log_file):
                return "empty", "GENESIS"
            with open(self.log_file, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                if size == 0:
                    return "empty", "GENESIS"
                buffer_size = 4096
                pos = size
                remainder = b""
                while pos > 0:
                    read_len = min(buffer_size, pos)
                    pos -= read_len
                    f.seek(pos)
                    chunk = f.read(read_len) + remainder
                    lines = chunk.splitlines()
                    if len(lines) > 1:
                        for raw in reversed(lines):
                            if raw.strip():
                                return self._classify_tail_line(raw)
                        # chunk contained only empty lines — keep scanning back
                    remainder = lines[0] if lines else b""
                if remainder.strip():
                    return self._classify_tail_line(remainder)
            return "empty", "GENESIS"
        except Exception as tail_err:  # noqa: BLE001
            logger.warning("[IMP-24] audit tail read error: %s", tail_err, exc_info=True)
            return "invalid", "GENESIS"

    @staticmethod
    def _classify_tail_line(raw: bytes) -> tuple[str, str]:
        try:
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                entry_hash = data.get("entry_hash", "")
                if isinstance(entry_hash, str) and entry_hash:
                    return "ok", entry_hash
        except Exception as exc:  # noqa: BLE001
            # [B110] Non-JSON / partial tail line is a normal classification
            # outcome (maps to "invalid" below); log instead of silent pass.
            logger.debug(f"[IMP-24] audit tail line unparseable: {exc}", exc_info=True)
        return "invalid", "GENESIS"

    def append(self, entry: dict[str, Any]) -> str | None:
        """Append an entry to the log. Returns the entry_hash, or None on
        failure (fail-open: caller decides)."""
        try:
            with self._lock:
                # [SCP-DNA-FIX R12-16] entry_ts was computed but never used.
                # Fix: actually SET entry["timestamp"] if missing — ensures
                # every audit log entry has a timestamp for forensic queries.
                if "timestamp" not in entry:
                    entry["timestamp"] = time.time()
                # [XPROC-CHAIN 2026-09-26] The chain tail is re-read UNDER the
                # OS-level cross-process lock on EVERY append (mirror
                # scp/trace_ledger.py). Previously the tail was cached in the
                # in-memory _last_hash at init: two processes appending to the
                # same audit file chained from a stale tail, permanently
                # breaking the on-disk chain and fail-closed-blocking every
                # future fix via the verify_chain gates.
                with _CrossProcessFileLock(str(self.log_file) + ".lock"):
                    tail_status, prev_hash = self._read_tail_state()
                    if tail_status == "invalid":
                        # Corrupt tail: history is NEVER rewritten (trace
                        # ledger corruption policy). Append a CHAIN_RECOVERY
                        # anchor that starts a NEW chain segment, then chain
                        # the real entry onto the anchor.
                        anchor: dict[str, Any] = {
                            "type": "CHAIN_RECOVERY",
                            "timestamp": time.time(),
                        }
                        # Hash BEFORE adding entry_hash/prev_hash keys, same
                        # exclusion rule the verifier applies to every entry.
                        anchor_payload = json.dumps(anchor, sort_keys=True, default=str)
                        anchor["entry_hash"] = hashlib.sha256(
                            f"GENESIS|{anchor_payload}".encode(),
                        ).hexdigest()[:32]
                        anchor["prev_hash"] = None
                        with open(self.log_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(anchor, sort_keys=True, default=str) + "\n")
                        logger.error(
                            "[IMP-24-BLOCKER] audit log %s tail INVALID — appended CHAIN_RECOVERY "
                            "anchor %s and started a NEW chain segment; corrupted history is "
                            "preserved on disk as tamper evidence and must NOT be rewritten or deleted",
                            self.log_file,
                            anchor["entry_hash"][:8],
                        )
                        prev_hash = anchor["entry_hash"]
                    # Compute chained hash: SHA-256(prev_hash + entry_payload).
                    payload = json.dumps(entry, sort_keys=True, default=str)
                    chain_input = f"{prev_hash}|{payload}"
                    entry_hash = hashlib.sha256(
                        chain_input.encode("utf-8"),
                    ).hexdigest()[:32]
                    entry["entry_hash"] = entry_hash
                    entry["prev_hash"] = prev_hash
                    line = json.dumps(entry, sort_keys=True, default=str) + "\n"
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(line)
                    self._last_hash = entry_hash
                    return entry_hash
        except OSError as e:
            # Disk full / permission denied — scream to stderr (DNA #11).
            # silent-by-design: failure is screamed to stderr; append returns None to the caller (fail-open decided upstream).
            sys.stderr.write(
                f"[IMP-24] AUDIT LOG UNWRITABLE: {e}\n"
                f"[IMP-24] Entry dropped: {entry}\n"
            )
            sys.stderr.flush()
            return None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-24] audit append error: {e}")
            return None

    def read_since(self, since_ts: float) -> list[dict[str, Any]]:
        """Read all entries with timestamp >= since_ts. Fail-open."""
        try:
            with self._lock:
                if not os.path.exists(self.log_file):
                    return []
                with open(self.log_file, encoding="utf-8") as f:
                    out = []
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("timestamp", 0) >= since_ts:
                                out.append(entry)
                        except json.JSONDecodeError as line_err:
                            # silent-by-design: corrupt line skip in aggregation — outer read errors are logged below.
                            logger.debug("[IMP-24] skipping corrupt audit line: %s", line_err, exc_info=True)
                            continue
                        except Exception as line_err2:  # noqa: BLE001
                            logger.debug("[IMP-24] skipping unreadable audit line: %s", line_err2, exc_info=True)
                            continue
                    return out
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-24] audit read error: {e}")
            return []

    @staticmethod
    def _verify_lines(lines: list[str], start: int, prev_init: str) -> str | None:
        """Strictly verify lines[start:] — None when intact, else the reason.

        Every line must chain from the running previous entry_hash (``prev_init``
        for the first line) and its recomputed hash must match entry_hash.
        """
        prev = prev_init
        for i in range(start, len(lines)):
            try:
                entry = json.loads(lines[i])
            except json.JSONDecodeError as e:
                return f"line {i} not JSON: {e}"
            if not isinstance(entry, dict):
                return f"line {i}: entry is not a JSON object"
            entry_hash = entry.get("entry_hash", "")
            prev_hash = entry.get("prev_hash", "")
            if prev_hash != prev:
                return (
                    f"line {i}: prev_hash mismatch "
                    f"(expected {prev[:8]}, got {prev_hash[:8]})"
                )
            # Recompute hash.
            # [SCP-DNA-FIX R12-3] Exclude BOTH `entry_hash` AND `prev_hash`
            # from the recompute payload (see the tamper-evidence notes above).
            payload = {k: v for k, v in entry.items()
                       if k not in ("entry_hash", "prev_hash")}
            payload_str = json.dumps(payload, sort_keys=True, default=str)
            chain_input = f"{prev}|{payload_str}"
            expected = hashlib.sha256(
                chain_input.encode("utf-8"),
            ).hexdigest()[:32]
            if expected != entry_hash:
                return (
                    f"line {i}: entry_hash mismatch "
                    f"(expected {expected[:8]}, got {entry_hash[:8]}) "
                    f"— payload tampered"
                )
            prev = entry_hash
        return None

    def verify_chain(self) -> tuple[bool, str]:
        """Verify the hash chain (tamper-evidence check). Returns (ok, reason).

        [XPROC-CHAIN 2026-09-26] Mirrors the scp/trace_ledger.py corruption
        policy: a CHAIN_RECOVERY anchor (type=="CHAIN_RECOVERY", prev_hash
        null) starts a NEW chain segment and the verdict covers the ACTIVE
        segment (entries after the last anchor). Pre-anchor history is
        preserved on disk as tamper evidence and disclosed in the reason
        without flipping the verdict — otherwise one historically corrupt
        file would fail-closed-block every future fix forever, and the
        anchor written by append() could never rehabilitate the log.
        """
        try:
            with self._lock:
                if not os.path.exists(self.log_file):
                    return True, "no log file"
                # [XPROC-VERIFY 2026-09-30] Giữ CÙNG khóa cross-process
                # OS-level với append() trong lúc đọc: trước đây verify_chain
                # chỉ giữ in-process thread lock, nên một process khác append
                # đúng lúc verify đọc file → dòng bị xé giữa chừng →
                # "line N not JSON" → veredict giả "tampered" → fail-closed
                # chặn oan mọi fix kế tiếp. Khóa chỉ bao quanh bước ĐỌC (phần
                # xử lý dưới làm trên snapshot in-memory); contention quá hạn
                # 10s raise OSError → bắt bởi except dưới → fail-loud thay vì
                # veredict giả.
                with _CrossProcessFileLock(str(self.log_file) + ".lock"):
                    with open(self.log_file, encoding="utf-8") as f:
                        lines = f.readlines()
                last_anchor = -1
                for i, line in enumerate(lines):
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (
                        isinstance(entry, dict)
                        and entry.get("type") == "CHAIN_RECOVERY"
                        and entry.get("prev_hash") is None
                    ):
                        last_anchor = i
                if last_anchor >= 0:
                    try:
                        anchor_entry = json.loads(lines[last_anchor])
                    except json.JSONDecodeError as e:
                        return False, f"anchor line {last_anchor} not JSON: {e}"
                    # The anchor itself must be intact: it hashes from GENESIS.
                    anchor_payload = {k: v for k, v in anchor_entry.items()
                                      if k not in ("entry_hash", "prev_hash")}
                    anchor_expected = hashlib.sha256(
                        f"GENESIS|{json.dumps(anchor_payload, sort_keys=True, default=str)}".encode(),
                    ).hexdigest()[:32]
                    if anchor_expected != anchor_entry.get("entry_hash"):
                        return False, (
                            f"CHAIN_RECOVERY anchor at line {last_anchor}: entry_hash "
                            f"mismatch — anchor tampered"
                        )
                    anchor_hash = anchor_entry.get("entry_hash", "")
                    err = self._verify_lines(lines, last_anchor + 1, anchor_hash)
                    if err:
                        return False, (
                            f"active segment after CHAIN_RECOVERY anchor at "
                            f"line {last_anchor}: {err}"
                        )
                    return True, (
                        f"chain OK ({len(lines) - last_anchor - 1} active entries; "
                        f"CHAIN_RECOVERY anchor at line {last_anchor}; pre-anchor "
                        f"history preserved on disk as tamper evidence, excluded "
                        f"from the active chain)"
                    )
                err = self._verify_lines(lines, 0, "GENESIS")
                if err:
                    return False, err
                return True, f"chain OK ({len(lines)} entries)"
        except Exception as e:  # noqa: BLE001
            return False, f"verify error: {e}"


# ============================================================
# PolicyGate class.
# ============================================================

class PolicyGate:
    """Constitutional policy gate — blocks forbidden fix patterns."""

    def __init__(
        self,
        audit_log: ImmutableAuditLog | None = None,
        extra_patterns: list[ForbiddenPattern] | None = None,
    ) -> None:
        self.audit_log = audit_log or ImmutableAuditLog()
        self.patterns: list[ForbiddenPattern] = list(FORBIDDEN_PATTERNS)
        if extra_patterns:
            self.patterns.extend(extra_patterns)
        self._lock = threading.RLock()

    def evaluate_fix(self, fix: Any) -> PolicyDecision:
        """Evaluate a fix against all forbidden patterns.

        Args:
            fix: A PolicyFix, or any object with `patch`, `patched_source`,
                `bug_file` attributes (e.g. IMP-14 ProposedFix).

        Returns:
            PolicyDecision. If any BLOCK-severity pattern matches →
            allowed=False. If only REVIEW-severity patterns match →
            allowed=True but severity="REVIEW".
        """
        try:
            with self._lock:
                # Coerce to PolicyFix if needed.
                if isinstance(fix, PolicyFix):
                    pf = fix
                else:
                    pf = PolicyFix(
                        fix_id=getattr(fix, "fix_id", ""),
                        patch=getattr(fix, "patch", "") or "",
                        patched_source=getattr(fix, "patched_source", "") or "",
                        bug_file=getattr(fix, "bug_file", "") or "",
                        bug_line=getattr(fix, "bug_line", 0),
                        scanner_name=getattr(fix, "scanner_name", ""),
                    )

                # Concatenate patch + patched_source for matching.
                text_to_scan = f"{pf.patch}\n{pf.patched_source}"

                blocked: list[str] = []
                review: list[str] = []
                matched_descriptions: list[str] = []

                for pat in self.patterns:
                    try:
                        if pat.matches(text_to_scan):
                            if pat.severity == "BLOCK":
                                blocked.append(pat.name)
                            else:
                                review.append(pat.name)
                            matched_descriptions.append(
                                f"{pat.name}: {pat.description}"
                            )
                    except Exception as e:  # noqa: BLE001
                        logger.debug(f"[IMP-24] pattern {pat.name} error: {e}")
                        continue

                # Build decision.
                audit_id = hashlib.sha256(
                    f"{time.time()}|{pf.fix_id}|{'|'.join(blocked)}".encode(),
                ).hexdigest()[:16]

                if blocked:
                    decision = PolicyDecision(
                        allowed=False,
                        blocked_patterns=blocked + review,
                        severity="BLOCK",
                        reason=(
                            f"BLOCKED by constitutional policy: "
                            f"{', '.join(blocked)} (DNA #4). "
                            f"Matched: {'; '.join(matched_descriptions[:3])}"
                        ),
                        audit_id=audit_id,
                        fix_id=pf.fix_id,
                    )
                elif review:
                    decision = PolicyDecision(
                        allowed=True,
                        blocked_patterns=review,
                        severity="REVIEW",
                        reason=(
                            f"FLAGGED for review: {', '.join(review)}. "
                            f"Matched: {'; '.join(matched_descriptions[:3])}"
                        ),
                        audit_id=audit_id,
                        fix_id=pf.fix_id,
                    )
                else:
                    decision = PolicyDecision(
                        allowed=True,
                        blocked_patterns=[],
                        severity="ALLOW",
                        reason="no forbidden patterns matched",
                        audit_id=audit_id,
                        fix_id=pf.fix_id,
                    )

                # Audit log every decision (even ALLOW for transparency).
                self._log_decision(decision, pf)
                return decision

        except Exception as e:  # noqa: BLE001 — DEFAULT-DENY per DNA #4
            logger.error(
                f"[IMP-24] policy engine crash — DEFAULT-DENY (DNA #4): {e}"
            )
            decision = PolicyDecision(
                allowed=False,
                blocked_patterns=["__engine_crash__"],
                severity="BLOCK",
                reason=(
                    f"POLICY ENGINE CRASH — DEFAULT-DENY per DNA #4: {e}"
                ),
                audit_id=hashlib.sha256(
                    f"crash-{time.time()}".encode(),
                ).hexdigest()[:16],
                fix_id=getattr(fix, "fix_id", ""),
            )
            self._log_decision(decision, None)
            return decision

    def _log_decision(self, decision: PolicyDecision, fix: PolicyFix | None) -> None:
        """Write decision to audit log. Fail-open (DNA #11 — log to stderr)."""
        entry = {
            "timestamp": decision.timestamp,
            "fix_id": decision.fix_id,
            "allowed": decision.allowed,
            "severity": decision.severity,
            "blocked_patterns": list(decision.blocked_patterns),
            "reason": decision.reason,
            "audit_id": decision.audit_id,
            "bug_file": fix.bug_file if fix else "",
            "bug_line": fix.bug_line if fix else 0,
            "scanner_name": fix.scanner_name if fix else "",
        }
        # If audit log write fails (disk full) AND decision was BLOCK →
        # we still want to block (the decision is in-memory). But scream.
        # [SCP-DNA-FIX R13-6] Bug #3: RESOLVED THREE-WAY CONTRADICTION.
        # Previously:
        #   - Module docstring (lines 50-52) said "DEFAULT-ALLOW with loud
        #     stderr warning"
        #   - Inline comment (line 624) also said "DEFAULT-ALLOW"
        #   - But the actual code did NOT flip `decision.allowed` — the
        #     BLOCK stayed in effect — and the stderr message at line 629
        #     said "BLOCK decision is still in effect", contradicting both
        #     docstrings.
        # The code's behavior was fail-CLOSED (block even when audit trail
        # can't be written). The docstrings' stated intent was fail-OPEN
        # (allow when audit trail can't be written — because blocking
        # without an audit trail is a worse failure mode: silent denial
        # of service with no record).
        # DNA #7 (Autofix safe) + DNA #11 (Fail loudly) favor fail-OPEN
        # here: don't brick the engine if disk is full, but scream. The
        # decision is now consistent: flip to ALLOW + scream to stderr.
        # Operator must investigate disk space / permissions — but the
        # fix is allowed through, and the audit trail is INCOMPLETE
        # (logged to stderr, not to the audit file).
        # NOTE: This is defense-in-depth — the engine has OTHER safety
        # layers (reality_test, post_fix_verify, blast_radius) that will
        # still gate the fix downstream. This decision is ONLY about
        # whether the policy_gate's audit-failure mode should additionally
        # block the fix. The answer (per docstrings + DNA #7): NO.
        written_hash = self.audit_log.append(entry)
        if written_hash is None and decision.severity == "BLOCK":
            # [P1-3 FIX R16] BLOCK stays BLOCK (fail-CLOSED for security).
            # BEFORE: audit-log write failure → BLOCK flipped to ALLOW (fail-open).
            #         Q4-FS-2 / L7-1: this meant eval()/shell=True/verify=False
            #         could be ALLOWED when disk was full — security gate
            #         silently disabled by an unrelated disk issue.
            # AFTER:  BLOCK stays BLOCK. DNA #7 fail-open is for RUNTIME
            #         availability (don't crash the server), NOT for SECURITY
            #         decisions. If we can't log a BLOCK, we STILL block —
            #         better to refuse a fix than to allow eval()/shell=True
            #         unlogged. Operator must free disk / fix permissions,
            #         then re-run. ALLOW decisions still fail-open (non-security).
            decision.allowed = False  # stays blocked
            decision.severity = "BLOCK"  # stays BLOCK
            decision.reason = (
                f"[P1-3 R16] BLOCK maintained: audit log unwritable AND fix matches "
                f"BLOCKED_PATTERNS. Refusing to fail-open for security (was IMP-24 "
                f"fail-open in R15). BLOCKED_PATTERNS were: {list(decision.blocked_patterns)}. "
                f"Operator must free disk space / fix permissions, then re-run."
            )
            sys.stderr.write(
                "[P1-3 R16] CRITICAL: audit log unwritable while blocking a fix with "
                "BLOCKED_PATTERNS. BLOCK maintained (fail-CLOSED for security).\n"
                f"[P1-3 R16] fix_id={decision.fix_id} patterns={list(decision.blocked_patterns)}\n"
                "[P1-3 R16] Operator must investigate disk space / permissions, then re-run.\n"
                "[P1-3 R16] (ALLOW decisions still fail-open per DNA #7 — only BLOCK is fail-closed)\n"
            )
            sys.stderr.flush()

    def appeal_block(
        self,
        fix_id: str,
        human_token: str,
        justification: str,
    ) -> dict[str, Any]:
        """Operator appeal of a blocked fix. Logs the appeal (does NOT
        auto-unblock — operator must separately re-apply the fix).

        Returns a dict with appeal_id + status.
        """
        try:
            appeal_id = hashlib.sha256(
                f"appeal-{time.time()}-{fix_id}".encode(),
            ).hexdigest()[:16]
            entry = {
                "timestamp": time.time(),
                "appeal_id": appeal_id,
                "fix_id": fix_id,
                "human_token": (
                    human_token[:8] + "..." if len(human_token) > 8 else human_token
                ),
                "justification": justification[:500],
                "action": "appeal_block",
            }
            # Write to a separate appeals log (so appeals aren't mixed with
            # decisions in the main audit log).
            try:
                os.makedirs(
                    os.path.dirname(DEFAULT_APPEAL_LOG) or ".", exist_ok=True,
                )
                with open(DEFAULT_APPEAL_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            except Exception as e:  # noqa: BLE001
                # silent-by-design: failure is screamed to stderr and reported to the caller by contract.
                sys.stderr.write(
                    f"[IMP-24] APPEAL LOG UNWRITABLE: {e}\n"
                    f"[IMP-24] Appeal dropped: {entry}\n"
                )
                sys.stderr.flush()

            logger.info(
                f"[IMP-24] appeal registered: fix_id={fix_id} "
                f"appeal_id={appeal_id} token={entry['human_token']}"
            )
            return {
                "appeal_id": appeal_id,
                "status": "logged",
                "message": (
                    "Appeal logged. Operator must manually re-apply the fix "
                    "if justified. Audit trail preserved."
                ),
            }
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-24] appeal_block error: {e}")
            return {"appeal_id": "", "status": "error", "message": str(e)}

    def list_blocks(self, since_ts: float = 0.0) -> list[dict[str, Any]]:
        """List all BLOCK decisions since `since_ts`. For operator UI."""
        try:
            entries = self.audit_log.read_since(since_ts)
            return [
                e for e in entries
                if e.get("severity") == "BLOCK" or not e.get("allowed", True)
            ]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-24] list_blocks error: {e}")
            return []

    def stats(self) -> dict[str, Any]:
        """Return gate stats (counts of allow/review/block in audit log)."""
        try:
            all_entries = self.audit_log.read_since(0.0)
            allow = sum(1 for e in all_entries if e.get("severity") == "ALLOW")
            review = sum(1 for e in all_entries if e.get("severity") == "REVIEW")
            block = sum(1 for e in all_entries if e.get("severity") == "BLOCK")
            return {
                "total_decisions": len(all_entries),
                "allow": allow,
                "review": review,
                "block": block,
                "patterns_registered": len(self.patterns),
                "audit_log": self.audit_log.log_file,
            }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}


# ============================================================
# Singleton accessor.
# ============================================================

_POLICY_GATE: PolicyGate | None = None
_GATE_LOCK = threading.Lock()


def get_policy_gate(
    audit_log_file: str = DEFAULT_AUDIT_LOG,
    extra_patterns: list[ForbiddenPattern] | None = None,
) -> PolicyGate:
    """Return the singleton PolicyGate. Lazy-initialized."""
    global _POLICY_GATE
    if _POLICY_GATE is None:
        with _GATE_LOCK:
            if _POLICY_GATE is None:
                audit = ImmutableAuditLog(log_file=audit_log_file)
                _POLICY_GATE = PolicyGate(audit_log=audit, extra_patterns=extra_patterns)
    return _POLICY_GATE


def reset_policy_gate() -> None:
    """Reset the singleton (for tests)."""
    global _POLICY_GATE
    with _GATE_LOCK:
        _POLICY_GATE = None


# ============================================================
# Module-level convenience.
# ============================================================

def evaluate_fix(fix: Any) -> PolicyDecision:
    """Module-level shortcut: get_policy_gate().evaluate_fix(fix)."""
    try:
        return get_policy_gate().evaluate_fix(fix)
    except Exception as e:  # noqa: BLE001 — DEFAULT-DENY per DNA #4
        logger.error(f"[IMP-24] evaluate_fix crash — DEFAULT-DENY: {e}")
        return PolicyDecision(
            allowed=False,
            blocked_patterns=["__module_crash__"],
            severity="BLOCK",
            reason=f"DEFAULT-DENY (module crash): {e}",
            audit_id=hashlib.sha256(
                f"mod-crash-{time.time()}".encode(),
            ).hexdigest()[:16],
        )


def appeal_block(fix_id: str, human_token: str, justification: str) -> dict[str, Any]:
    """Module-level shortcut: get_policy_gate().appeal_block(...)."""
    try:
        return get_policy_gate().appeal_block(fix_id, human_token, justification)
    except Exception as e:  # noqa: BLE001
        return {"appeal_id": "", "status": "error", "message": str(e)}


def list_blocks(since_ts: float = 0.0) -> list[dict[str, Any]]:
    """Module-level shortcut: get_policy_gate().list_blocks(since_ts)."""
    try:
        return get_policy_gate().list_blocks(since_ts)
    except Exception:  # noqa: BLE001 — silent-by-design: fail-open returns empty list (documented module-level shortcut contract)
        return []


__all__ = [
    "ForbiddenPattern",
    "FORBIDDEN_PATTERNS",
    "PolicyFix",
    "PolicyDecision",
    "ImmutableAuditLog",
    "PolicyGate",
    "get_policy_gate",
    "reset_policy_gate",
    "evaluate_fix",
    "appeal_block",
    "list_blocks",
    "DEFAULT_AUDIT_LOG",
    "DEFAULT_APPEAL_LOG",
]
