#!/usr/bin/env python3
"""Reality test: explicit egress deny blocks external URLs before DNS/network."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scp.core.url_fetcher import _safe_fetch_url

old=os.environ.get("SCP_EGRESS_MODE")
os.environ["SCP_EGRESS_MODE"]="deny"
try:
    try:
        _safe_fetch_url("https://example.com", timeout=1)
    except ValueError as exc:
        # S17 pin update: commit 61d068f (EE/M13-G1) moved the deny
        # enforcement to the url_safety choke point — denial now raises
        # EgressDeniedError (ValueError subclass) with "SCP_EGRESS_MODE=deny
        # blocks all non-loopback hosts"; the fetcher's own "external egress
        # disabled" ValueError remains as defense in depth (url_fetcher.py).
        # Accept either denial message, and REQUIRE the denied URL to be
        # cited — strictness increased vs the old message-only pin.
        msg = str(exc)
        assert "SCP_EGRESS_MODE" in msg and (
            "blocks all non-loopback" in msg or "external egress disabled" in msg
        ), msg
        assert "https://example.com" in msg, f"denial must cite the URL: {msg}"
        print("PASS [1]: external egress denied before network")
    else:
        raise AssertionError("external URL was not denied")
finally:
    if old is None: os.environ.pop("SCP_EGRESS_MODE", None)
    else: os.environ["SCP_EGRESS_MODE"]=old
print("✓ Reality test 4-d-025 PASSED")
