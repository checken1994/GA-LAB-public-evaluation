"""
CISA KEV (Known Exploited Vulnerabilities) feed — real-time CVE exploitation data.

Source: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
Updated: CISA updates this catalog multiple times per week.

Usage:
    from scp.security.cisa_kev import CisaKevFeed
    feed = CisaKevFeed(data_dir="data")
    feed.refresh()  # fetch latest
    is_exploited = feed.is_exploited("CVE-2026-20963")
    recent = feed.get_recent(limit=10)
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

from scp.security.url_safety import safe_urlopen

logger = logging.getLogger("scp.security.cisa_kev")

# [FIX] CISA blocks direct access (403 Akamai). Use GitHub mirror instead.
CISA_KEV_URL = "https://raw.githubusercontent.com/cisagov/kev-data/main/known_exploited_vulnerabilities.json"
CISA_KEV_URL_FALLBACK = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours — CISA updates multiple times/week
_CISA_ALLOWED_HOSTS = {"raw.githubusercontent.com", "www.cisa.gov"}


def _open_cisa_feed(url: str):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _CISA_ALLOWED_HOSTS:
        raise ValueError(f"Unsupported CISA feed URL: {url!r}")
    allowed_prefixes = {
        "raw.githubusercontent.com": "/cisagov/kev-data/",
        "www.cisa.gov": "/sites/default/files/feeds/",
    }
    if not parsed.path.startswith(allowed_prefixes[parsed.hostname]):
        raise ValueError(f"Unsupported CISA feed path: {parsed.path!r}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("CISA feed URL must not contain credentials or query data")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SCP-CISA-KEV/1.0",
            "Accept": "application/json, text/plain, */*",
        },
    )
    # [EE] Route through the canonical egress choke point (safe_urlopen =
    # SCP_EGRESS_MODE gate + SSRF validation) instead of raw
    # urllib.request.urlopen. The fixed host/path allowlist above stays as
    # defense in depth.
    return safe_urlopen(request, timeout=30)  # nosec B310 — URL validated by SCP


class CisaKevFeed:
    """CISA Known Exploited Vulnerabilities feed.

    Provides:
      - is_exploited(cve_id) → bool
      - get_vuln(cve_id) → dict (full record)
      - get_recent(limit) → list[dict]
      - get_by_product(product) → list[dict]
      - get_by_vendor(vendor) → list[dict]
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / "cisa_kev.json"
        self._vulns: dict[str, dict] = {}  # cveID -> record
        self._last_refresh = 0
        self._load_cache()

    def _load_cache(self):
        """Load from local cache file."""
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                self._vulns = {v.get("cveID", ""): v for v in data.get("vulnerabilities", [])}
                self._last_refresh = data.get("timestamp", 0)
                logger.info(f"[CISA KEV] Loaded {len(self._vulns)} vulns from cache")
            except Exception as e:
                logger.warning(f"[CISA KEV] Cache load error: {e}", exc_info=True)

    def refresh(self, force: bool = False) -> dict:
        """Fetch latest from CISA. Returns summary dict.

        Args:
            force: If True, ignore cache TTL.
        """
        if not force and time.time() - self._last_refresh < CACHE_TTL_SECONDS:
            return {"action": "skipped", "reason": "cache fresh", "count": len(self._vulns)}

        try:
            with _open_cisa_feed(CISA_KEV_URL) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            vulns = data.get("vulnerabilities", [])
            self._vulns = {v.get("cveID", ""): v for v in vulns}
            self._last_refresh = time.time()

            # Save cache
            self.cache_file.write_text(
                json.dumps({"timestamp": self._last_refresh, "vulnerabilities": vulns}, ensure_ascii=False),
                encoding="utf-8",
            )

            logger.info(f"[CISA KEV] Refreshed: {len(self._vulns)} vulns")
            return {"action": "refreshed", "count": len(self._vulns), "catalog_version": data.get("catalogVersion", "")}
        except Exception as e:
            logger.warning(f"[CISA KEV] Refresh failed: {e}", exc_info=True)
            return {"action": "failed", "error": str(e)}

    def is_exploited(self, cve_id: str) -> bool:
        """Check if a CVE is in CISA KEV (actively exploited)."""
        return cve_id.upper() in self._vulns

    def get_vuln(self, cve_id: str) -> dict | None:
        """Get full record for a CVE."""
        return self._vulns.get(cve_id.upper())

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get most recently added vulnerabilities."""
        sorted_vulns = sorted(
            self._vulns.values(),
            key=lambda v: v.get("dateAdded", ""),
            reverse=True,
        )
        return sorted_vulns[:limit]

    def get_by_product(self, product: str) -> list[dict]:
        """Get vulns by product name."""
        p_lower = product.lower()
        return [v for v in self._vulns.values() if p_lower in v.get("product", "").lower()]

    def get_by_vendor(self, vendor: str) -> list[dict]:
        """Get vulns by vendor name."""
        v_lower = vendor.lower()
        return [v for v in self._vulns.values() if v_lower in v.get("vendorProject", "").lower()]

    def stats(self) -> dict:
        """Get feed stats."""
        return {
            "total_vulns": len(self._vulns),
            "last_refresh": self._last_refresh,
            "cache_age_hours": round((time.time() - self._last_refresh) / 3600, 1) if self._last_refresh else None,
        }

    # ---- [SCP-DNA-FIX R13-3 BUG-007] Public API (canonical names) ----
    # R5 added CisaKevFeed with `refresh()` + `is_exploited()` but vulture found
    # 0 callers across the entire codebase → SCP has no awareness of in-the-wild
    # CVE exploitation despite the predictor.py docstring claiming it does. The
    # fix has two parts:
    #   1. Public `is_in_kev()` + `refresh_feed()` aliases (canonical names that
    #      match the bug spec — keeps the existing is_exploited/refresh methods
    #      working as thin wrappers for backward-compat).
    #   2. Wire-in TODO for the predictor (parent-owned).
    #
    # TODO(parent — scp/security/predictor.py owner): the predictor's
    # `cisa_kev_match_recent` should be implemented as:
    #     from scp.security.cisa_kev import CisaKevFeed
    #     _kev_feed = CisaKevFeed()
    #     _kev_feed.refresh_feed()  # cached + TTL — safe to call every time
    #     if _kev_feed.is_in_kev(cve_id):
    #         # boost severity / mark as actively exploited
    # Until the predictor wires this in, callers can use the API directly.
    def is_in_kev(self, cve_id: str) -> bool:
        """Public alias for `is_exploited` — check if a CVE is in the CISA KEV
        catalog (i.e., actively exploited in the wild).

        Args:
            cve_id: CVE identifier (e.g., "CVE-2026-20963"). Case-insensitive.

        Returns:
            True if the CVE appears in the most recently fetched CISA KEV
            catalog. Returns False if the feed has not been refreshed yet
            (call `refresh_feed()` first) or if the CVE is not in the catalog.
        """
        return self.is_exploited(cve_id)

    def refresh_feed(self, force: bool = False) -> dict:
        """Public alias for `refresh` — fetch the latest CISA Known Exploited
        Vulnerabilities catalog with caching + TTL.

        Source URL:
            https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
        (Note: the actual fetch uses a GitHub mirror as primary because CISA
        blocks direct access via 403 Akamai — see CISA_KEV_URL at top of file.
        Both URLs serve the same catalog.)

        Caching:
            - Local cache file at `data/cisa_kev.json` survives restarts.
            - TTL: 6 hours (CISA updates multiple times per week).
            - Pass `force=True` to bypass the TTL.

        Args:
            force: If True, ignore cache TTL and fetch fresh.

        Returns:
            Summary dict:
                {"action": "refreshed"|"skipped"|"failed",
                 "count": int,
                 "catalog_version": str (if refreshed),
                 "error": str (if failed),
                 "reason": str (if skipped)}
        """
        return self.refresh(force=force)
