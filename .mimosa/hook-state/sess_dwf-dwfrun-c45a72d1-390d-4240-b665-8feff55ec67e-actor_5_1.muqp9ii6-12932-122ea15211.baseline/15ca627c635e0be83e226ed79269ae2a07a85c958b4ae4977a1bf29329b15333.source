"""Read the token from a private PC file, then start the outbound bridge."""
from __future__ import annotations

import json
import os
import runpy
from pathlib import Path


def main() -> None:
    root = Path(os.environ.get("SCP_ROOT", Path(__file__).resolve().parents[1])).resolve()
    config_path = Path(os.environ.get("SCP_BRIDGE_CONFIG", root / ".private-secrets" / "scp-public-bridge" / "agent.json"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not all(isinstance(config.get(key), str) and config[key] for key in ("agentId", "token", "publicUrl", "localUrl")):
        raise SystemExit("invalid private bridge configuration")
    auth_token_file = str(config.get("backendTokenFile") or root / ".private-secrets" / "release-audit" / "scp-247" / "scp-admin-token")
    os.environ.update({
        "SCP_PUBLIC_URL": config["publicUrl"],
        "SCP_AGENT_ID": config["agentId"],
        "SCP_RELAY_TOKEN": config["token"],
        "SCP_LOCAL_URL": config["localUrl"],
        "SCP_LOCAL_ASK_PATH": str(config.get("localAskPath") or "/ask"),
        "SCP_LOCAL_AUTH_TOKEN_FILE": auth_token_file,
        "SCP_BRIDGE_LOG": str(config_path.parent / "bridge.log"),
    })
    runpy.run_path(str(root / "scripts" / "scp_local_bridge.py"), run_name="__main__")


if __name__ == "__main__":
    main()
