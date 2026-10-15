import json
import logging
import os
import secrets
import threading
from pathlib import Path

from scp.security.circuit_breaker import CircuitBreaker as DosCircuitBreaker  # noqa: F401
from scp.security.playbooks import FORBIDDEN_ACTIONS, PlaybookRegistry  # noqa: F401

# Security playbooks and the RPS DoS breaker are intentionally imported here so
# all escalation callers reach one visible guardrail namespace.

logger = logging.getLogger("scp.security.escalation")

# Create a lock for thread safety
lock = threading.Lock()

# Define the default defensive playbook
DEFAULT_DEFENSIVE_PLAYBOOK = {
    "block_ip": True,
    "tighten_rate_limit": True,
    "enable_honeypot": True,
    "forensic_logging": True,
    "alert_cert": True
}

class EscalationManager:
    # [SCP-DNA-FIX R5-3] Thresholds for auto-arming Dead Man's Switch.
    # When on_threat_detected sees severity in this set, start_countdown is
    # automatically called — previously start_countdown had 0 callers so the
    # Dead Man's Switch was inert (it logged threats but never armed the
    # countdown that would trigger execute_defensive_playbook on timeout).
    AUTO_ARM_SEVERITIES = {"high", "critical"}
    DEFAULT_TIMEOUT_MIN = 30

    def __init__(self, data_dir: str = "data"):
        self.escalation_log_path = Path(data_dir) / "escalation_log.jsonl"
        self.escalation_state_path = Path(data_dir) / "escalation_state.json"
        self.escalation_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._active: dict = {}
        self._history: list = []
        # Track live Timer objects so on_human_approval/rejection can cancel them.
        self._timers: dict[str, threading.Timer] = {}
        # Dedicated lock protects JSONL and atomic state writes without holding
        # the escalation state lock during filesystem I/O.
        self._write_lock = threading.Lock()
        self._restore_state()

    def _persist_state(self) -> None:
        """Atomically persist authoritative escalation state."""
        with lock:
            payload = {
                "schema_version": 1,
                "active": self._active,
                "history": self._history,
            }
        temporary = self.escalation_state_path.with_name(
            f"{self.escalation_state_path.name}.{secrets.token_hex(4)}.tmp"
        )
        with self._write_lock:
            try:
                temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                os.replace(temporary, self.escalation_state_path)
            except Exception as exc:
                logger.warning("[escalation] state persist warning: %s", exc, exc_info=True)
            finally:
                if temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError:
                        logger.debug('EscalationManager._persist_state: OSError ignored', exc_info=True)

    def _restore_state(self) -> None:
        """Restore state and re-arm non-terminal deadlines after restart."""
        try:
            raw = self.escalation_state_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except FileNotFoundError:
            logger.debug('EscalationManager._restore_state: FileNotFoundError ignored', exc_info=True)
            return
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[escalation] state restore skipped: %s", exc)
            return
        if not isinstance(payload, dict):
            logger.warning("[escalation] state restore skipped: invalid root")
            return
        active = payload.get("active", {})
        history = payload.get("history", [])
        if not isinstance(active, dict) or not isinstance(history, list):
            logger.warning("[escalation] state restore skipped: invalid collections")
            return
        with lock:
            self._active = {
                str(key): value for key, value in active.items() if isinstance(value, dict)
            }
            self._history = [value for value in history if isinstance(value, dict)]
            armed = [value for value in self._active.values() if value.get("status") == "armed"]
        dropped = False
        for entry in armed:
            threat_id = str(entry.get("threat_id") or self._threat_id(entry.get("threat", {})))
            try:
                deadline = float(entry["deadline_at"])
            except (KeyError, TypeError, ValueError):
                logger.warning("[escalation] dropping armed entry without valid deadline: %s", threat_id)
                with lock:
                    self._active.pop(threat_id, None)
                dropped = True
                continue
            delay = max(0.0, deadline - self._now())
            timer = threading.Timer(delay, self.on_timeout, args=(entry.get("threat", {}),))
            timer.daemon = True
            with lock:
                self._timers[threat_id] = timer
            timer.start()
        if armed or dropped:
            self._persist_state()

    def on_threat_detected(self, threat: dict):
        """[SCP-DNA-FIX R5-3] Entry point — called by judgecore_mixin:417.

        Now ALSO auto-arms the Dead Man's Switch countdown for high/critical
        threats (previously start_countdown was never called → switch was
        inert). Threats are also tracked in self._active so dashboard via
        escalation_status() can see them.
        """
        # Classify the severity of the threat
        severity = self.classify_threat(threat)
        threat_id = self._threat_id(threat)
        with lock:
            self._active[threat_id] = {
                "threat_id": threat_id,
                "threat": threat,
                "severity": severity,
                "armed_at": self._now(),
                "status": "armed" if severity in self.AUTO_ARM_SEVERITIES else "monitoring",
            }
        self._persist_state()
        # [SCP-DNA-FIX 4-b-018] log_action does file I/O — must NOT happen
        # while holding the escalation `lock`. Pre-fix: log_action was called
        # INSIDE the `with lock:` block above → all escalation decisions
        # serialized on disk I/O; if disk was full, the lock was held during
        # exception handling. Fix: build the state under the lock, then call
        # log_action AFTER releasing. The log message string is constructed
        # here (under no lock — fast), then log_action writes it to disk
        # without touching the escalation lock.
        self.log_action(f"Threat detected: {threat}, severity: {severity}", "threat_detection")

        # [SCP-DNA-FIX R5-3] Auto-arm Dead Man's Switch for high/critical threats.
        # Previously start_countdown was never called by anyone → switch inert.
        if severity in self.AUTO_ARM_SEVERITIES:
            try:
                self.start_countdown(threat, timeout_min=self.DEFAULT_TIMEOUT_MIN)
            except Exception as e:
                logger.warning(f"[escalation] start_countdown failed for threat {threat_id}: {e}", exc_info=True)

    @staticmethod
    def _threat_id(threat: dict) -> str:
        """Derive a stable id from a threat dict (for tracking + human approval)."""
        if not isinstance(threat, dict):
            return str(id(threat))
        # Prefer explicit id; fall back to a hash of the threat content.
        if threat.get("id"):
            return str(threat["id"])
        if threat.get("threat_id"):
            return str(threat["threat_id"])
        import hashlib
        payload = json.dumps(threat, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    @staticmethod
    def _now() -> float:
        import time
        return time.time()

    def classify_threat(self, threat_data: dict) -> str:
        """Classify threat severity: low | medium | high | critical.

        [SCP-DNA-FIX 4-b-005] Was a stub `return "high"` — every threat that
        hit `on_threat_detected` was classified "high" → matched
        `AUTO_ARM_SEVERITIES = {"high", "critical"}` → `start_countdown` was
        called → 30-min Dead Man's Switch armed → on timeout,
        `execute_defensive_playbook` runs (block_ip, tighten_rate_limit,
        enable_honeypot, forensic_logging, alert_cert). 100% false-alarm rate
        for low/medium threats (DNA #22: PASS≠TRUE — classifier claimed to
        classify but always returned "high"; DNA #9: No harm — false alarms
        cause operator alert fatigue + unnecessary defensive playbook; DNA #11:
        HITL — every threat auto-armed 30-min countdown without discrimination).

        Conservative default: "medium" (does NOT auto-arm Dead Man's Switch).
        Only "high"/"critical" when explicit evidence supports it.

        Args:
            threat_data: Dict from caller (judgecore_mixin). Observed fields in
                production callers:
                  - id, type, severity, prediction_confidence, description
                    (predictive escalation path, judgecore_mixin:410-417)
                  - type, severity, falsification_status, question, verdict,
                    confidence, note (falsification-human-review path,
                    judgecore_mixin:2943-2951)

        Returns:
            "low" | "medium" | "high" | "critical"
        """
        if not isinstance(threat_data, dict):
            return "medium"

        # Explicit severity in threat_data takes precedence — callers that
        # already know the severity (e.g. falsification_human_review always
        # sets severity="high") get their value respected.
        severity = (threat_data.get("severity") or "").lower()
        if severity in ("critical", "high", "medium", "low"):
            return severity

        # Confidence — accept either `confidence` or `prediction_confidence`
        # (both are used by production callers; see judgecore_mixin:414, 2949).
        confidence = threat_data.get("confidence")
        if confidence is None:
            confidence = threat_data.get("prediction_confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            logger.debug('EscalationManager.classify_threat: TypeError, ValueError ignored', exc_info=True)
            confidence = 0.0

        # Indicator type — production callers use `type` (e.g.
        # "falsification_human_review" or a forecast.threat_type). Fall back to
        # explicit `indicator_type` / `indicator` if present.
        indicator = (
            threat_data.get("indicator_type")
            or threat_data.get("indicator")
            or threat_data.get("type")
            or ""
        ).lower()

        # Heuristic: only 'high' if confidence is very high AND an explicit
        # severe indicator type is present (not just a generic anomaly).
        if confidence >= 0.9 and indicator in (
            "exploit_attempt", "data_exfiltration", "privilege_escalation",
        ):
            return "high"
        # Critical indicators (known-bad signatures) require even higher
        # confidence to avoid false alarms.
        if confidence >= 0.95 and indicator in (
            "malware_signature", "known_bad_ip",
        ):
            return "critical"
        # Falsification human-review is a known caller-set severity path; if
        # severity wasn't explicit but type indicates it, treat as medium
        # (operator review required, but does NOT auto-arm countdown).
        if indicator == "falsification_human_review" and confidence >= 0.7:
            return "medium"
        if confidence >= 0.5:
            return "medium"
        # Conservative default — "medium" (NOT "high", NOT auto-arm).
        # Empty / ambiguous threat_data lands here. Returning "medium" rather
        # than "low" ensures the threat is operator-visible (low may be
        # filtered out by dashboards), while still NOT triggering the
        # Dead Man's Switch countdown.
        return "medium"

    def start_countdown(self, threat: dict, timeout_min: int = 30):
        # Start a countdown timer and persist its absolute deadline before it runs.
        threat_id = self._threat_id(threat)
        deadline_at = self._now() + (timeout_min * 60)
        timer = threading.Timer(timeout_min * 60, self.on_timeout, args=(threat,))
        timer.daemon = True  # don't block process exit
        with lock:
            # Cancel any prior timer for the same threat (re-arm case).
            prior = self._timers.get(threat_id)
            if prior is not None:
                try:
                    prior.cancel()
                except Exception:  # noqa: BLE001 — timer.cancel() best-effort
                    logger.exception("[escalation.py:112] silenced exception")
            self._timers[threat_id] = timer
            if threat_id in self._active:
                self._active[threat_id]["status"] = "armed"
                self._active[threat_id]["timeout_min"] = timeout_min
                self._active[threat_id]["deadline_at"] = deadline_at
        self._persist_state()
        timer.start()
        # [SCP-DNA-FIX 4-b-018] log_action (file I/O) OUTSIDE the escalation
        # lock — pre-fix held the lock during disk write → serialized all
        # escalation decisions on disk I/O; on disk-full, lock was held
        # during exception handling.
        self.log_action(f"Countdown started for threat: {threat}, timeout: {timeout_min} minutes", "countdown_started")

    def on_timeout(self, threat: dict):
        threat_id = self._threat_id(threat)
        with lock:
            timer = self._timers.pop(threat_id, None)
            state = self._active.pop(threat_id, None)
            if state is not None:
                self._history.append({
                    "threat_id": threat_id,
                    "action": "timeout",
                    "timestamp": self._now(),
                })
        if timer is not None:
            timer.cancel()
        self._persist_state()
        # [SCP-DNA-FIX 4-b-018] log_action (file I/O) — state has already been
        # terminalized above, so dashboard cannot retain stale armed/timer data.
        self.log_action(
            f"Timeout occurred for threat: {threat}, evaluating defensive playbook",
            "timeout_occurred",
        )
        self.execute_defensive_playbook(threat)

    def execute_defensive_playbook(self, threat: dict):
        """[SCP-DNA-FIX R5-3] Execute the default defensive playbook.

        Each action is now validated against PlaybookRegistry.validate_action()
        BEFORE being executed — refuses FORBIDDEN_ACTIONS (hack_back,
        data_destruction, preemptive_strike, counter_attack, reverse_exploit)
        with a WARNING log. Previously the entire playbooks.py module was
        dead-imported so the guardrail was unenforced.
        """
        # Only forensic logging is implemented in this module today. The
        # other names are policy intents, not real OS/network controls. DNA #22:
        # never record a skipped action as if it had been enforced.
        implemented_actions = {"forensic_logging"}
        results = []
        for action, enabled in DEFAULT_DEFENSIVE_PLAYBOOK.items():
            if not enabled:
                continue
            # [SCP-DNA-FIX R5-3] Guardrail: refuse forbidden actions.
            try:
                if not PlaybookRegistry.validate_action(action):
                    logger.warning(
                        f"[escalation] GUARDRAIL refused forbidden action "
                        f"'{action}' for threat {self._threat_id(threat)} "
                        f"skipping (FORBIDDEN_ACTIONS={sorted(FORBIDDEN_ACTIONS)})"
                    )
                    self.log_action(
                        f"GUARDRAIL refused forbidden action: {action}",
                        "guardrail_refused",
                    )
                    results.append({"action": action, "status": "GUARDRAIL_REFUSED"})
                    continue
            except Exception as guard_err:
                # If the guardrail itself fails, fail-safe (skip the action).
                logger.warning(f"[escalation] guardrail check error for '{action}': {guard_err} — skipping", exc_info=True)
                results.append({"action": action, "status": "GUARDRAIL_ERROR"})
                continue
            if action not in implemented_actions:
                message = (
                    f"DEFENSIVE_ACTION_NOT_IMPLEMENTED: {action} for threat "
                    f"{self._threat_id(threat)}; no OS/network enforcement performed"
                )
                logger.warning("[escalation] %s", message)
                self.log_action(message, "action_not_implemented")
                results.append({"action": action, "status": "SKIPPED_NOT_IMPLEMENTED"})
                continue
            self.log_action(f"Forensic logging recorded for threat: {threat}", action)
            results.append({"action": action, "status": "RECORDED"})
        return {
            "threat_id": self._threat_id(threat),
            "enforcement_performed": False,
            "actions": results,
        }

    def log_action(self, message: str, why: str):
        """Write a log entry to disk.

        [SCP-DNA-FIX 4-b-018] This method does FILE I/O. Callers MUST NOT
        hold the escalation `lock` when invoking this method — the file
        write blocks on disk I/O (could be slow under load, could hang
        on disk-full). All callers in this module have been refactored to
        release the escalation lock BEFORE calling log_action (or to not
        acquire it at all when no state mutation is needed).

        Pre-fix: callers like on_threat_detected, start_countdown,
        on_timeout, and execute_defensive_playbook called log_action
        INSIDE `with lock:` blocks → all escalation decisions serialized
        on disk I/O; if disk was full, the lock was held during the
        exception handling → subsequent calls to on_threat_detected /
        get_active_escalations / escalation_status blocked on the held
        lock.

        Post-fix: log_action is called OUTSIDE any caller's `with lock:`
        block. The log_entry dict is built here (fast, microseconds), then
        written to disk. If disk is slow or full, only this method's
        caller is blocked — not all escalation decisions.
        """
        import time
        log_entry = {
            "timestamp": time.time(),
            "message": message,
            "why": why
        }
        with self._write_lock:
            with self.escalation_log_path.open("a") as log_file:
                json.dump(log_entry, log_file)
                log_file.write("\n")

    def get_active_escalations(self) -> list:
        """[SCP-DNA-FIX R5-3] Return all currently-armed escalations.

        Previously this method had 0 callers → Dead Man's Switch armed threats
        were invisible to the dashboard. Now exposed via escalation_status()
        so any caller (admin dashboard, /v105/escalation/status route, metrics
        scraper) can see armed threats.
        """
        with lock:
            return list(self._active.values())

    def get_escalation_history(self) -> list:
        with lock:
            return list(self._history)

    def escalation_status(self) -> dict:
        """[SCP-DNA-FIX R5-3] Public dashboard snapshot.

        Returns:
            {
              "active_count": int,
              "active": [...],          # via get_active_escalations()
              "history_count": int,
              "armed_count": int,       # subset of active with status='armed'
              "timers_count": int,      # live Timer objects
            }
        """
        with lock:
            active = list(self._active.values())
            armed = [e for e in active if e.get("status") == "armed"]
            return {
                "active_count": len(active),
                "active": active,
                "history_count": len(self._history),
                "armed_count": len(armed),
                "timers_count": len(self._timers),
            }

    # ---- Human-in-the-loop wiring ----
    # [SCP-DNA-FIX R5-3] DESIGN TODO: on_human_approval / on_human_rejection
    # are now reachable from any admin code path (e.g. FastAPI route handlers)
    # but are NOT yet wired to HTTP endpoints. Recommended wiring (out of
    # scope for this fix — api_server_parts/lifespan.py + api_server.py are owned by parent):
    #
    #   @app.post("/v105/escalation/{threat_id}/approve")
    #   async def approve_escalation(threat_id: str, action: str = "default"):
    #       judge.escalation_manager.on_human_approval(threat_id, action)
    #       return {"status": "approved"}
    #
    #   @app.post("/v105/escalation/{threat_id}/reject")
    #   async def reject_escalation(threat_id: str):
    #       judge.escalation_manager.on_human_rejection(threat_id)
    #       return {"status": "rejected"}
    #
    # These endpoints would let a human operator cancel the Dead Man's Switch
    # countdown before the 30-min timeout fires execute_defensive_playbook.
    # Until those routes exist, threats that are auto-armed will fire the
    # default defensive playbook on timeout (fail-safe: act, don't wait).
    def on_human_approval(self, threat_id: str, action: str = "default"):
        with lock:
            self._history.append({"threat_id": threat_id, "action": "approved", "human_action": action})
            if threat_id in self._active:
                self._active[threat_id]["status"] = "approved"
            timer = self._timers.pop(threat_id, None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:  # noqa: BLE001 — timer.cancel() best-effort
                logger.exception("[escalation.py:239] silenced exception")
        self._persist_state()
        self.log_action(f"Human approved {threat_id}: {action}", "human_approval")

    def on_human_rejection(self, threat_id: str):
        with lock:
            self._history.append({"threat_id": threat_id, "action": "rejected"})
            if threat_id in self._active:
                self._active[threat_id]["status"] = "rejected"
            timer = self._timers.pop(threat_id, None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:  # noqa: BLE001 — timer.cancel() best-effort
                logger.exception("[escalation.py:252] silenced exception")
        self._persist_state()
        self.log_action(f"Human rejected {threat_id}", "human_rejection")

    # ---- [SCP-DNA-FIX R13-3 BUG-004] Public admin API ----
    # R5-3 added on_human_approval / on_human_rejection but they had 0 callers
    # → Dead Man's Switch auto-armed 30-min countdown with NO human override.
    # Any false-positive high-severity threat fired execute_defensive_playbook
    # with no way to cancel. Below are the public API methods that admin route
    # handlers should call (delegating to the existing internal methods).
    #
    # TODO(parent — api_server.py owner): wire these into FastAPI routes:
    #     @app.post("/v105/escalation/{threat_id}/approve")
    #     async def approve_escalation(threat_id: str, action: str = "default"):
    #         judge.escalation_manager.approve(threat_id, action)
    #         return {"status": "approved"}
    #
    #     @app.post("/v105/escalation/{threat_id}/reject")
    #     async def reject_escalation(threat_id: str):
    #         judge.escalation_manager.reject(threat_id)
    #         return {"status": "rejected"}
    #
    # Until those routes exist, the override capability is reachable only
    # programmatically (e.g., via the dashboard's Python REPL or a script).
    def approve(self, threat_id: str, action: str = "default") -> None:
        """Public admin API — human approves an armed escalation.

        Cancels the Dead Man's Switch countdown for `threat_id` and marks the
        escalation as 'approved' in the audit log. Safe to call on unknown
        threat_id (no-op).

        Args:
            threat_id: ID returned by `on_threat_detected` (visible via
                `get_dashboard_status()`).
            action: Optional free-form description of the chosen action
                (e.g., "blocked_ip_manual", "monitored_only").
        """
        self.on_human_approval(threat_id, action)

    def reject(self, threat_id: str) -> None:
        """Public admin API — human rejects an armed escalation as false-positive.

        Cancels the Dead Man's Switch countdown for `threat_id` and marks the
        escalation as 'rejected' in the audit log. Safe to call on unknown
        threat_id (no-op).
        """
        self.on_human_rejection(threat_id)

    # ---- [SCP-DNA-FIX R13-3 BUG-005] Dashboard aggregation ----
    # R5-3 added get_active_escalations / get_escalation_history /
    # escalation_status but they had 0 callers → dashboard could not see live
    # Dead Man's Switch state. Below is a single aggregation method that
    # dashboard endpoints should call.
    #
    # TODO(parent — api_server.py owner): wire this into a FastAPI route:
    #     @app.get("/v105/escalation/status")
    #     async def escalation_status():
    #         return judge.escalation_manager.get_dashboard_status()
    #
    # Until that route exists, this method is callable programmatically
    # (e.g., from a metrics scraper or the dashboard's Python REPL).
    def get_dashboard_status(self) -> dict:
        """Aggregate dashboard snapshot — one call returns everything.

        Returns:
            {
              "status": <escalation_status()>,
              "active": [<get_active_escalations()>],
              "history": [<get_escalation_history()>],
              "summary": {
                  "active_count": int,
                  "armed_count": int,
                  "history_count": int,
                  "timers_count": int,
              },
            }
        """
        status = self.escalation_status()
        active = self.get_active_escalations()
        history = self.get_escalation_history()
        return {
            "status": status,
            "active": active,
            "history": history,
            "summary": {
                "active_count": status.get("active_count", 0),
                "armed_count": status.get("armed_count", 0),
                "history_count": status.get("history_count", 0),
                "timers_count": status.get("timers_count", 0),
            },
        }
