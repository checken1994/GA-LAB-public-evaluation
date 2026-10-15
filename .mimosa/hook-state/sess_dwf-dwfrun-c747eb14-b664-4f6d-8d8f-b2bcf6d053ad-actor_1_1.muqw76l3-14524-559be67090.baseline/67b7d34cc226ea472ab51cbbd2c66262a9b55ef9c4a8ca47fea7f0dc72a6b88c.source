"""Runtime imports must use an explicit disposable storage boundary."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _probe(tmp_path: Path, code: str, extra: dict[str, str] | None = None):
    allow = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allow}
    target = tmp_path / "isolated-state"
    env.update({
        "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "SCP_ENV_FILE": str(tmp_path / "no-runtime-env"), "SCP_DATA_DIR": str(target),
        "SCP_API_PROFILE": "full", "SCP_EGRESS_MODE": "deny",
        "SCP_CAPABILITY_SECRET": "isolated-probe-capability-only-0123456789abcdef",
    })
    env.update(extra or {})
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env,
        text=True, capture_output=True, timeout=90, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout.splitlines()[-1]), target


def test_learning_and_db_manager_share_configured_data_root(tmp_path):
    actual, target = _probe(tmp_path, """
import json
from scp import api_server as api
from scp.core import db_manager
print(json.dumps({'db': str(db_manager.DB_PATH), 'real_db': str(api._real_learning.scp_db_path), 'fast_db': str(api._fast_learning.scp_db_path), 'real_data': str(api._real_learning.data_dir), 'fast_data': str(api._fast_learning.data_dir)}))
""")
    assert {Path(actual[k]).resolve() for k in ("db", "real_db", "fast_db")} == {target / "v13.db"}
    assert {Path(actual[k]).resolve() for k in ("real_data", "fast_data")} == {target}
    assert (target / "v13.db").is_file()
    assert not (tmp_path / "data" / "v13.db").exists()


def test_db_import_does_not_create_storage(tmp_path):
    actual, target = _probe(tmp_path, """
import json
from pathlib import Path
from scp.core import db_manager
print(json.dumps({'path': str(db_manager.DB_PATH), 'exists': Path(db_manager.DATA_DIR).exists()}))
""")
    assert Path(actual["path"]).resolve() == target / "v13.db"
    assert actual["exists"] is False


def test_kernel_defaults_share_configured_data_root(tmp_path):
    actual, target = _probe(tmp_path, """
import json
from scp import api_server as api
adapter = api._get_ask_kernel_adapter()
assert adapter is not None
print(json.dumps({'paths': [list(k) for k in api._ASK_KERNEL_ADAPTERS]}))
""")
    assert len(actual["paths"]) == 1
    assert [Path(p).resolve() for p in actual["paths"][0]] == [target / "ask_task_kernel.sqlite3", target / "ask_task_kernel_trace.jsonl"]


def test_explicit_db_path_is_created_lazily(tmp_path):
    explicit = tmp_path / "separate" / "nested" / "custom.sqlite3"
    actual, _ = _probe(tmp_path, """
import json
from pathlib import Path
from scp.core import db_manager
before = Path(db_manager.DB_PATH).exists()
conn = db_manager.get_db()
conn.execute('CREATE TABLE boundary_probe(value TEXT)')
conn.commit()
conn.close()
print(json.dumps({'path': str(db_manager.DB_PATH), 'before': before, 'after': Path(db_manager.DB_PATH).exists()}))
""", {"SCP_DB_PATH": str(explicit)})
    assert Path(actual["path"]).resolve() == explicit
    assert actual["before"] is False
    assert actual["after"] is True
