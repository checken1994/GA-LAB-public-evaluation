#!/usr/bin/env python3
"""EE-G1 census runner — inventory of HTTP client method call-sites in scp/.

Runs the shared AST scanner (``scp.security.egress_static_scan``) over the
scp/ tree (excluding the 3 gated canonical modules), and writes a census JSON
with every client-method call-site plus its gated/ungated verdict.

This is the evidence artifact for gap EE-G1 (static gate was blind to
``session = requests.Session(); session.get(url)`` style bypasses, found by
hand by V-EE as V-EE-1/2). Re-run any time:

    python tools/ee_g1_census.py
    python tools/ee_g1_census.py --output <path>

[AUDIT-R2 M-01] Exit code contract changed (fail-closed): exit 1 when any
scanned file cannot be parsed (a hole in egress visibility — never silently
skipped) or when an UNGATED call-site exists; exit 0 otherwise. Enforcement
also lives in tests/T03_capability/test_egress_enforcement.py (fail-closed
gate). The scanner tracks import-alias constructors, cross-module client
imports, and dominance-based (not line-order) gating since AUDIT-R2.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scp.security.egress_static_scan import (  # noqa: E402
    GATE_EXCLUDED_MODULES,
    scan_client_method_calls,
    scan_raw_http_calls,
)

DEFAULT_OUTPUT = REPO_ROOT / "reports" / "expert-panel" / "EE-G1-client-method-census.json"


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(REPO_ROOT / "scp"))
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = ap.parse_args()

    root = Path(args.root)
    unparsable: list[str] = []
    raw_sites = scan_raw_http_calls([root], unparsable=unparsable)
    client_sites = scan_client_method_calls([root], unparsable=unparsable)

    def rel(p: str) -> str:
        try:
            return Path(p).resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return Path(p).as_posix()

    excluded = GATE_EXCLUDED_MODULES
    client_sites = [s for s in client_sites if rel(s["file"]) not in excluded]
    raw_sites = [(f, ln, k) for (f, ln, k) in raw_sites if rel(f) not in excluded]

    ungated = [s for s in client_sites if not s["gated"]]
    census = {
        "gap": "EE-G1",
        "description": (
            "AST census of HTTP client method call-sites on tracked client "
            "variables (requests.Session/httpx.Client/AsyncClient/urllib "
            "opener/aiohttp.ClientSession) — the class of bypass the raw "
            "direct-spelling gate could not see (V-EE-1/2 were found by hand). "
            "AUDIT-R2 M-01: import-alias constructors, cross-module client "
            "imports and dominance-based gating are tracked; unparsable files "
            "fail the census instead of being skipped."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_head": _git_head(),
        "scanner": "scp/security/egress_static_scan.py",
        "scanned_root": rel(str(root)),
        "excluded_modules": sorted(excluded),
        "unparsable_files": sorted(rel(p) for p in unparsable),
        "summary": {
            "raw_direct_spelling_sites": len(raw_sites),
            "client_method_call_sites": len(client_sites),
            "gated": sum(1 for s in client_sites if s["gated"]),
            "ungated": len(ungated),
            "unparsable_files": len(unparsable),
        },
        "ungated_sites": [
            {**s, "file": rel(s["file"])} for s in ungated
        ],
        "gated_sites": [
            {**s, "file": rel(s["file"])} for s in client_sites if s["gated"]
        ],
        "raw_direct_spelling_sites_list": [
            {"file": rel(f), "line": ln, "kind": k} for (f, ln, k) in raw_sites
        ],
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(census, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"EE-G1 census: {census['summary']['client_method_call_sites']} client "
        f"call-sites ({census['summary']['gated']} gated, "
        f"{census['summary']['ungated']} UNGATED), "
        f"{census['summary']['raw_direct_spelling_sites']} raw direct-spelling "
        f"sites, {census['summary']['unparsable_files']} unparsable files "
        f"-> {out}"
    )
    for s in census["ungated_sites"]:
        print(f"  UNGATED {s['file']}:{s['line']} {s['receiver']}.{s['method']} in {s['function']}")
    for p in census["unparsable_files"]:
        print(f"  UNPARSABLE {p}")
    # [AUDIT-R2 M-01] fail-closed exit contract: unparsable file = visibility
    # hole; ungated site = open bypass. Both fail the census.
    if census["unparsable_files"] or census["ungated_sites"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
