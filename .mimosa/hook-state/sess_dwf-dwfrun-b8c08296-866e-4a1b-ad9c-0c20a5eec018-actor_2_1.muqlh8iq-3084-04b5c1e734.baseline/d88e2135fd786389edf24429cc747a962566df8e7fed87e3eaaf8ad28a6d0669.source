"""
[Task 7-A] PubChem source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_pubchem() was 15 LOC inline. Extracted as
standalone function for modularity. Backward-compatible — WhyEngine delegates.
"""
from __future__ import annotations

import json as _json
import logging
import urllib.request

from scp.security.url_safety import safe_urlopen  # noqa: B310

logger = logging.getLogger("scp.why.sources.pubchem")


def query_pubchem(target: str) -> str | None:
    """Query PubChem for molecular weight."""
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{target}/property/MolecularWeight/JSON"
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            props = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                return str(props[0].get("MolecularWeight", ""))
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        logger.warning(f"[why_sources.pubchem] failed for target='{target}': {e}", exc_info=True)
        return None
