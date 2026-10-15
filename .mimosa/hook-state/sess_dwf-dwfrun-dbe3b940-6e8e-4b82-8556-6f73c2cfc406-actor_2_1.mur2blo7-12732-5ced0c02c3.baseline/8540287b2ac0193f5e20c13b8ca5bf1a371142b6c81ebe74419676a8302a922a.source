# SCP CIRCUIT: M04 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M04-closure.json)
"""SCP Hands v3.4 managed process primitives.

Only fixed, catalogued commands can be started. A process can be stopped only
when its PID is owned by this manager instance; arbitrary PID termination is
never exposed.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)



class ManagedProcessManager:
    def __init__(self, data_dir: Path, project_root: Path) -> None:
        self.data_dir = data_dir
        self.project_root = project_root
        self.ledger_path = data_dir / "processes.jsonl"
        self.workspace_root = data_dir / "workspaces"
        self._owned: dict[int, subprocess.Popen[Any]] = {}
        self._meta: dict[int, dict[str, Any]] = {}
        self._workspaces: dict[int, Path] = {}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.catalog: dict[str, list[str]] = {
            "hands_probe": [sys.executable, str(project_root / "scp" / "hands" / "process_probe.py")],
        }

    def catalog_public(self) -> list[dict[str, Any]]:
        return [{"commandId": key, "description": "Fixed SCP-owned diagnostic process", "approval": "capability>=3 and approved"} for key in sorted(self.catalog)]

    def _record(self, event: str, payload: dict[str, Any]) -> None:
        record = {"timestamp": time.time(), "event": event, **payload}
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")

    @staticmethod
    def _alive(process: subprocess.Popen[Any]) -> bool:
        return process.poll() is None

    @staticmethod
    def _safe_env(command_id: str, workspace_id: str) -> dict[str, str]:
        """Allow only execution essentials; never forward the caller's full environment."""
        safe: dict[str, str] = {
            "PATH": os.path.dirname(sys.executable),
            "SCP_HANDS_OWNED": "1",
            "SCP_HANDS_COMMAND_ID": command_id,
            "SCP_HANDS_WORKSPACE_ID": workspace_id,
        }
        for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
            value = os.environ.get(key)
            if value:
                safe[key] = value
        return safe

    def _new_workspace(self) -> tuple[str, Path]:
        workspace_id = uuid.uuid4().hex
        workspace = (self.workspace_root / workspace_id).resolve()
        workspace.relative_to(self.workspace_root.resolve())
        workspace.mkdir(parents=False, exist_ok=False)
        return workspace_id, workspace

    def _cleanup_workspace(self, pid: int) -> bool:
        workspace = self._workspaces.pop(pid, None)
        if workspace is None:
            return True
        try:
            resolved = workspace.resolve()
            resolved.relative_to(self.workspace_root.resolve())
            shutil.rmtree(resolved)
            self._record("PROCESS_WORKSPACE_CLEANED", {"pid": pid, "workspaceId": resolved.name})
            return True
        except (OSError, ValueError) as exc:
            logger.debug('ManagedProcessManager._cleanup_workspace: OSError, ValueError ignored: %s', exc)
            self._record(
                "PROCESS_WORKSPACE_CLEANUP_FAILED",
                {"pid": pid, "workspaceId": workspace.name, "error": str(exc)},
            )
            self._workspaces[pid] = workspace
            return False

    def start(self, command_id: str) -> dict[str, Any]:
        command = self.catalog.get(command_id)
        if not command:
            result = {"success": False, "error": "Unknown managed command"}
            self._record("PROCESS_START_BLOCKED", {"commandId": command_id, **result})
            return result
        workspace_id = ""
        workspace: Path | None = None
        try:
            workspace_id, workspace = self._new_workspace()
            kwargs: dict[str, Any] = {
                "cwd": str(workspace),
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "env": self._safe_env(command_id, workspace_id),
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(command, **kwargs)
            now = time.time()
            metadata = {
                "pid": process.pid,
                "commandId": command_id,
                "startedAt": now,
                "command": command,
                "workspaceId": workspace_id,
                "workspaceScoped": True,
                "environmentScoped": True,
            }
            self._owned[process.pid] = process
            self._meta[process.pid] = metadata
            self._workspaces[process.pid] = workspace
            result = {
                "success": True,
                "pid": process.pid,
                "commandId": command_id,
                "startedAt": now,
                "owned": True,
                "workspaceId": workspace_id,
                "workspaceScoped": True,
                "environmentScoped": True,
            }
            self._record("PROCESS_STARTED", result)
            return result
        except OSError as exc:
            if workspace is not None:
                try:
                    shutil.rmtree(workspace)
                except OSError:
                    logger.debug('ManagedProcessManager.start: OSError ignored', exc_info=True)
            result = {"success": False, "commandId": command_id, "error": str(exc)}
            self._record("PROCESS_START_FAILED", result)
            return result

    def info(self, pid: int) -> dict[str, Any]:
        process = self._owned.get(pid)
        metadata = self._meta.get(pid, {"pid": pid, "owned": False})
        if process is not None:
            return {"success": True, **metadata, "owned": True, "alive": self._alive(process), "returnCode": process.poll()}
        return {"success": False, "pid": pid, "owned": False, "error": "PID is not owned by Hands"}

    def list_owned(self) -> dict[str, Any]:
        processes = []
        for pid, process in list(self._owned.items()):
            item = {**self._meta.get(pid, {"pid": pid}), "owned": True, "alive": self._alive(process), "returnCode": process.poll()}
            if process.poll() is not None:
                cleaned = self._cleanup_workspace(pid)
                item["workspaceCleaned"] = cleaned
                if not cleaned:
                    item["cleanupError"] = "Managed workspace cleanup failed"
                self._owned.pop(pid, None)
                self._meta.pop(pid, None)
            processes.append(item)
        return {"success": True, "processes": processes, "count": len(processes), "catalog": self.catalog_public()}

    def stop(self, pid: int) -> dict[str, Any]:
        process = self._owned.get(pid)
        if process is None:
            result = {"success": False, "pid": pid, "error": "PID is not owned by Hands; arbitrary stop is blocked"}
            self._record("PROCESS_STOP_BLOCKED", result)
            return result
        try:
            if self._alive(process):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.debug('ManagedProcessManager.stop: subprocess.TimeoutExpired ignored', exc_info=True)
                    process.kill()
                    process.wait(timeout=5)
            cleaned = self._cleanup_workspace(pid)
            result = {
                "success": cleaned,
                "pid": pid,
                "owned": True,
                "stopped": True,
                "returnCode": process.poll(),
                "workspaceCleaned": cleaned,
            }
            if not cleaned:
                result["error"] = "Managed workspace cleanup failed"
            self._record("PROCESS_STOPPED" if cleaned else "PROCESS_STOP_CLEANUP_FAILED", result)
            self._owned.pop(pid, None)
            self._meta.pop(pid, None)
            return result
        except OSError as exc:
            result = {"success": False, "pid": pid, "owned": True, "error": str(exc)}
            self._record("PROCESS_STOP_FAILED", result)
            return result
