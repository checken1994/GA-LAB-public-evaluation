import logging
import re
from pathlib import Path
from typing import Any

from scp.capabilities.tools import SafeCommandRunnerTool
from scp.security.capability_epoch import CapabilityAuthority, CapabilityToken

logger = logging.getLogger(__name__)

class AutonomousCapabilityGovernor:
    """Independent PDP and authority to evaluate autonomous plan steps and issue signed HMAC-SHA256 CapabilityToken instances."""

    BLOCKED_PATTERNS = list(SafeCommandRunnerTool.BLOCKED_PATTERNS)

    def __init__(self, capability_authority: CapabilityAuthority | None = None):
        self.authority = capability_authority
        self._compiled_patterns = [re.compile(p) for p in self.BLOCKED_PATTERNS]

    def evaluate_and_grant_step(
        self, step: dict[str, Any], plan: dict[str, Any], working_dir: str
    ) -> tuple[bool, CapabilityToken | None, str]:
        if not self.authority:
            return False, None, "No CapabilityAuthority configured for Governor."

        action = step.get("action", "")
        params = step.get("params", {})

        # 1. Path isolation (sandbox)
        # [SEC-FIX governor-path 2026-09-26] PRE-FIX chỉ kiểm tra 4 tên param
        # cố định (cwd/path/file_path/target) — plan step mang escape dưới tên
        # khác ('dest', 'filename', 'output_path', 'source', ...) đi thẳng qua
        # (probe xác nhận: token được cấp). Contract mới, 2 lớp:
        #   a) 4 param canonical: GIỮ check nghiêm ngặt cũ — mọi value non-empty
        #      đều resolve+containment (không suy luận path-like).
        #   b) MỌI param string khác: value "path-like" (segment '..' kèm
        #      separator, absolute path/drive/~) cũng phải containment.
        # Ngoại lệ có chủ đích: 'command' — chuỗi lệnh có boundary riêng ở
        # bước 2 (SafeCommandRunnerTool), không phải tham số đường dẫn.
        if action in ["pc.execute", "pc.write_file", "pc.read_file", "os.write_file", "os.read_file", "fs.read", "fs.write", "fs.delete"]:
            working_path = Path(working_dir).resolve()
            canonical_path_params = ("cwd", "path", "file_path", "target")
            for p_name, val in params.items():
                if p_name == "command":
                    continue  # dedicated boundary at step 2
                if not isinstance(val, str) or not val:
                    continue
                if p_name in canonical_path_params:
                    must_check = True
                else:
                    norm = val.replace("\\", "/")
                    must_check = (
                        ".." in norm.split("/")
                        or val.startswith("~")
                        or norm.startswith("/")
                        or (len(val) >= 2 and val[1] == ":")  # Windows drive (C:\, C:/)
                    )
                if not must_check:
                    continue
                try:
                    resolved = Path(val).expanduser().resolve()
                    if not resolved.is_relative_to(working_path):
                        return False, None, f"Path violation: '{val}' is outside working_dir '{working_dir}'"
                except Exception as e:
                    logger.debug("path resolution failed for %r: %s", val, e, exc_info=True)
                    return False, None, f"Path resolution failed: {e}"

        # 2. Command safety (SafeCommandRunnerTool boundary execution)
        if action in ("pc.execute", "cmd.run"):
            command = params.get("command", "")
            cap_level = max(1, int(step.get("capabilityLevel", 0)))
            approved = bool(step.get("approved", False))
            runner = SafeCommandRunnerTool(working_dir=working_dir)
            allowed, reason, required_cap = runner.evaluate_command(command, cap_level, approved)
            if not allowed:
                return False, None, reason

        # If passed, issue token
        task_id = plan.get("task_id") or plan.get("planId") or "unknown_task"
        step_id = step.get("stepId", "unknown_step")
        subject = f"hands:{action}"

        # Embed metadata in token_id for tracking and traceability
        import base64
        import json
        metadata = {"task_id": task_id, "step_id": step_id, "action": action}
        # token_id is truncated or kept full depending on the DB, but token_id in CapabilityToken is just a string.
        # CapabilityAuthority doesn't impose length on token_id in issue(), but we keep it reasonable.
        # We'll use base64 urlsafe without padding.
        token_id_b64 = base64.urlsafe_b64encode(json.dumps(metadata).encode()).decode().rstrip("=")

        try:
            token = self.authority.issue(subject=subject, token_id=token_id_b64)
            return True, token, "Autonomous safety invariants satisfied."
        except Exception as e:
            logger.debug("token issuance failed: %s", e, exc_info=True)
            return False, None, f"Failed to issue token: {e}"
