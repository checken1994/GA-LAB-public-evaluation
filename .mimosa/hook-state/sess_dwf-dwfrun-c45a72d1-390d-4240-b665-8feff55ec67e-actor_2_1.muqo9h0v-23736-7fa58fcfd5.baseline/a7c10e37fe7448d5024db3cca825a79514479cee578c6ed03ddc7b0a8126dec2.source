import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


_CHILD_PROBE = r'''
import json
import os
import sys

sys.path.insert(0, os.environ["SCP_TEST_PROJECT_ROOT"])
if os.environ.get("SCP_IMPORT_ORDER_MODE") == "route_first":
    import scp.api.routes.v104_routes  # noqa: F401
from scp.api_server import app

paths = set(app.openapi().get("paths", {}))
print(json.dumps({
    "path_count": len(paths),
    "v102": sum(p.startswith("/v102") for p in paths),
    "v103": sum(p.startswith("/v103") for p in paths),
    "v104": sum(p.startswith("/v104") for p in paths),
    "v105": sum(p.startswith("/v105") for p in paths),
    "import": sum(p.startswith("/import") for p in paths),
}))
'''


def _run_import_probe(mode: str) -> tuple[dict[str, int], str]:
    env = os.environ.copy()
    env["SCP_TEST_PROJECT_ROOT"] = str(PROJECT_ROOT)
    env["SCP_IMPORT_ORDER_MODE"] = mode
    # This contract measures full-router import stability, independent of the
    # production default API-surface profile.
    env["SCP_API_PROFILE"] = "full"
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD_PROBE],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    return result, completed.stderr



def test_extra_routers_survive_both_import_orders():
    # [2026-08-29] v104: 17 → 21 (additive free-API warehouse + TOP-1%
    # learning routes: top-systems status/learn/advise + free-apis/search).
    # v104: 21 → 23 (additive: /v104/doubt/status + /v104/doubt/run — Cronjob of Doubt)
    # [AUDIT-20260909 M3] v104: 23 → 24 (additive: /v104/learn/consolidate,
    # landed with the Step-0 autofix work between the previous pin and
    # 1f00d00). Count drift is documented here per the additive-changelog
    # guard contract; the exact-equality pin itself is unchanged.
    # [AUDIT-20260909 M3] This test previously failed for a PRODUCT reason:
    # v105_routes.py used `request: Request` without importing Request, so
    # app.openapi() crashed with PydanticUserError "class not fully defined"
    # in both import orders. Fixed at the product (import added).
    expected = {"v102": 2, "v103": 6, "v104": 24, "import": 3}
    for mode in ("canonical", "route_first"):
        result, stderr = _run_import_probe(mode)
        assert result["path_count"] >= 135
        for key, value in expected.items():
            assert result[key] == value, (mode, result)
        assert result["v105"] >= 31, (mode, result)
        assert "routers unavailable" not in stderr
        assert "partially initialized" not in stderr
