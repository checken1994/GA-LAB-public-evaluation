# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""SCP Hands v3.5 action registry.

The registry is deliberately explicit: an action is executable only when its
name, risk, capability, approval rule and verification contract are known.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from scp.capabilities.tools import (
    SafeCommandRunnerTool,
    SystemInspectionTool,
    WorkspaceAnalysisTool,
)


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    description: str
    domain: str
    risk: str
    capability_level: int
    requires_approval: bool
    mutates_state: bool
    verifier: str
    rollback: str

    def public(self) -> dict[str, Any]:
        return asdict(self)


class ActionRegistry:
    """Allowlisted catalog for bounded PC, process and browser actions."""

    def __init__(self) -> None:
        definitions = [
            ActionDefinition("pc.status", "Read PC Controller status", "pc", "low", 0, False, False, "controller_online", "none"),
            ActionDefinition("cmd.run", SafeCommandRunnerTool.description, "pc", "medium", 1, False, False, "command_success", "none"),
            ActionDefinition("sys.inspect", SystemInspectionTool.description, "pc", "low", 0, False, False, "metrics_collected", "none"),
            ActionDefinition("workspace.analyze", WorkspaceAnalysisTool.description, "pc", "low", 0, False, False, "entries_bounded", "none"),
            ActionDefinition("pc.read_file", "Read a non-sensitive workspace file", "pc", "low", 0, False, False, "read_success", "none"),
            ActionDefinition("pc.list_dir", "List entries inside the SCP workspace", "pc", "low", 0, False, False, "path_inside_workspace", "none"),
            ActionDefinition("pc.process_snapshot", "Read a bounded process snapshot", "pc", "low", 0, False, False, "command_success", "none"),
            ActionDefinition("pc.process_list_owned", "List processes started and owned by Hands", "pc", "low", 0, False, False, "owned_process_report", "none"),
            ActionDefinition("pc.process_info", "Read info for a Hands-owned process PID", "pc", "low", 0, False, False, "owned_process_report", "none"),
            ActionDefinition("pc.process_start_managed", "Start one fixed diagnostic command owned by Hands", "pc", "medium", 3, True, True, "owned_process_started", "stop_owned_process"),
            ActionDefinition("pc.process_stop_owned", "Stop a process previously started by Hands", "pc", "high", 4, True, True, "owned_process_stopped", "none"),
            ActionDefinition("pc.service_snapshot", "Read a bounded Windows service snapshot", "pc", "low", 0, False, False, "command_success", "none"),
            ActionDefinition("pc.workspace_diff_check", "Run git diff --check in the workspace", "pc", "low", 0, False, False, "command_success", "none"),
            ActionDefinition("pc.file_hash", "Compute SHA-256 for a non-sensitive workspace file", "pc", "low", 0, False, False, "file_hash_and_exists", "none"),
            ActionDefinition("pc.search_workspace", "Search bounded text matches inside the workspace", "pc", "low", 0, False, False, "matches_bounded", "none"),
            ActionDefinition("pc.directory_tree", "Read a bounded workspace directory tree", "pc", "low", 0, False, False, "entries_bounded", "none"),
            ActionDefinition("pc.git_status", "Read git branch and status", "pc", "low", 0, False, False, "command_success", "none"),
            ActionDefinition("pc.validate_jsonl", "Validate JSONL syntax in a non-sensitive file", "pc", "low", 0, False, False, "jsonl_parse_report", "none"),
            ActionDefinition("pc.write_file", "Write a workspace file with backup", "pc", "medium", 3, True, True, "file_hash_and_exists", "restore_backup"),
            ActionDefinition("web.search_public", "Search public Internet sources", "web", "low", 0, False, False, "results_normalized", "none"),
            ActionDefinition("web.browse_public", "Read a public HTTP page", "web", "low", 0, False, False, "http_success", "none"),
            ActionDefinition("web.extract_links", "Extract bounded public HTTP links", "web", "low", 0, False, False, "links_normalized", "none"),
            ActionDefinition("web.tab_snapshot", "Read bounded local DevTools page targets", "web", "low", 0, False, False, "page_targets", "none"),
            ActionDefinition("web.dom_snapshot", "Read bounded text from an approved local browser page", "web", "medium", 1, True, False, "dom_text", "none"),
            ActionDefinition("web.open_public_tab", "Navigate a local browser tab to a public HTTP URL", "web", "medium", 2, True, True, "navigation_url", "restore_previous_tab_not_automatic"),
            ActionDefinition("web.follow_public_link", "Follow a public anchor link in a local browser tab", "web", "medium", 2, True, True, "navigation_url", "restore_previous_tab_not_automatic"),
            ActionDefinition("web.wait_for_text", "Wait for bounded text evidence in a local browser tab", "web", "medium", 1, True, False, "text_observed", "none"),
            ActionDefinition("web.read_logged_in", "Read a user-approved local browser page", "web", "high", 1, True, False, "browser_evidence", "none"),
        ]
        self._definitions = {definition.name: definition for definition in definitions}

    def get(self, name: str) -> ActionDefinition | None:
        return self._definitions.get(name)

    def require(self, name: str) -> ActionDefinition:
        definition = self.get(name)
        if definition is None:
            raise KeyError(f"Unknown Hands action: {name}")
        return definition

    def list(self) -> list[dict[str, Any]]:
        return [self._definitions[name].public() for name in sorted(self._definitions)]

    def policy_preview(self, name: str, capability_level: int = 0, approved: bool = False) -> dict[str, Any]:
        definition = self.require(name)
        allowed = capability_level >= definition.capability_level and (approved or not definition.requires_approval)
        reason = "allowlisted action" if allowed else "capability or approval requirement not met"
        return {
            "action": definition.public(),
            "allowed": allowed,
            "reason": reason,
            "requestedCapability": capability_level,
            "approved": approved,
        }
