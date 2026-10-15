"""Real request-ledger writer and trace HTTP reader must share configured storage."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("explicit_ledger", [False, True])
def test_trace_route_resolves_runtime_ledger_from_another_cwd(tmp_path, explicit_ledger):
    root = Path(__file__).resolve().parents[2]
    env = {key: value for key, value in os.environ.items() if key.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
    }}
    state = tmp_path / "runtime-state"
    state.mkdir()
    env_file = tmp_path / "empty.env"
    env_file.touch()
    env.update({
        "PYTHONPATH": str(root), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "SCP_ENV_FILE": str(env_file), "SCP_DATA_DIR": str(state),
        "SCP_TRACE_STORE_PATH": str(state / "traces.sqlite3"),
        "SCP_EGRESS_MODE": "deny", "SCP_API_PROFILE": "full",
        "SCP_AUTH_TOKEN_SECRET": "trace-probe-admin-only-0123456789abcdef",
        "SCP_ADMIN_KEY": "trace-probe-admin-only-0123456789abcdef",
        "SCP_JWT_SECRET": "trace-probe-jwt-only-0123456789abcdef",
        "SCP_CAPABILITY_SECRET": "trace-probe-capability-only-0123456789abcdef",
    })
    if explicit_ledger:
        env["SCP_REQUEST_RUN_LEDGER_PATH"] = str(tmp_path / "separate-ledger" / "requests.jsonl")
    child = subprocess.run(
        [sys.executable, "-B", "-c", """
import hashlib, json, os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from scp.api.routes.openai_compat import router as producer, _OPENAI_COMPAT_LEDGER
from scp.api_server_parts._trace_impl import router as reader
from scp.security.jwt_guard import create_access_token
app = FastAPI()
app.include_router(producer)
app.include_router(reader)
client = TestClient(app)
models = client.get('/v1/models', headers={'Authorization': 'Bearer ' + create_access_token({'sub': 'trace-probe', 'role': 'admin'})})
assert models.status_code == 200, models.text
trace_id = models.json()['trace_id']
ledger = _OPENAI_COMPAT_LEDGER.path
before = hashlib.sha256(ledger.read_bytes()).hexdigest()
headers = {'Authorization': 'Bearer ' + os.environ['SCP_ADMIN_KEY']}
results = [client.get(prefix + trace_id, headers=headers) for prefix in ['/v3/trace/', '/api/v3/trace/', '/api/scp/v3/trace/']]
denied = client.get('/v3/trace/' + trace_id)
after = hashlib.sha256(ledger.read_bytes()).hexdigest()
print(json.dumps({'statuses': [r.status_code for r in results], 'ids': [r.json().get('trace_id') for r in results], 'trace_id': trace_id, 'ledger': str(ledger), 'unchanged': before == after, 'unauthenticated': denied.status_code}))
"""], cwd=tmp_path, env=env, text=True, capture_output=True, timeout=60, check=False,
    )
    assert child.returncode == 0, child.stdout + child.stderr
    observation = json.loads(child.stdout.splitlines()[-1])
    assert observation["statuses"] == [200, 200, 200], observation
    assert observation["ids"] == [observation["trace_id"]] * 3
    expected = Path(env["SCP_REQUEST_RUN_LEDGER_PATH"]) if explicit_ledger else state / "request_runs.jsonl"
    assert Path(observation["ledger"]).resolve() == expected
    assert observation["unchanged"] is True, "trace GET must not rewrite request evidence"
    assert observation["unauthenticated"] == 401
