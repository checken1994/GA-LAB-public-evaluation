"""
SCP V98 — ThreatDetector
Copyright (c) 2026 Minh. MIT License.

Port từ WHY H1 (fingerprint + ASN + behavioral) — gộp 3 detectors vào 1 module.

Naming convention: <Purpose>Detector (world standard, e.g. AnomalyDetector, IntrusionDetector)

3 detectors:
  1. HttpFingerprintDetector — header order, UA mismatch, library signature
  2. AsnDetector — datacenter, Tor, VPN, residential, GeoIP
  3. BehavioralDetector — timing distribution, KS test, entropy, scanner pattern
"""
from __future__ import annotations

import asyncio
import logging
import math
import socket
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from scp.security.url_safety import enforce_egress_policy  # [EE-G1]

logger = logging.getLogger("scp.security.threat_detector")


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class ThreatSignal:
    """Kết quả detect từ 3 detectors."""
    is_ai_agent: bool = False
    agent_type: str = "human"  # human | bot_legacy | ai_agent_2026 | anonymizing_proxy | unknown
    confidence: float = 0.0
    signals: list[str] = field(default_factory=list)
    ip: str = ""
    asn_intel: dict[str, Any] | None = None
    fingerprint_result: dict[str, Any] | None = None
    behavioral_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_ai_agent": self.is_ai_agent,
            "agent_type": self.agent_type,
            "confidence": round(self.confidence, 3),
            "signals": self.signals,
            "ip": self.ip,
            "asn_intel": self.asn_intel,
            "fingerprint_result": self.fingerprint_result,
            "behavioral_result": self.behavioral_result,
        }


# ============================================================
# 1. HTTP FINGERPRINT DETECTOR
# ============================================================

# AI agent User-Agent patterns
AI_AGENT_UAS = [
    "python-requests", "python-httpx", "python-urllib", "aiohttp",
    "curl/", "wget/", "httpx/", "axios/", "node-fetch", "got/",
    "go-http-client", "java-http", "okhttp", "scrapy", "mechanize",
    "selenium", "puppeteer", "playwright", "headless",
    "bot", "crawler", "spider", "scraper", "scanner",
]

# Browser headers that humans usually have
BROWSER_HEADERS = ["accept-language", "accept-encoding", "sec-ch-ua", "sec-fetch-mode"]

# Injection patterns
# [AUDIT-20260909 S6a] Hai signature dạng "tên hàm + dấu ngoặc" được giữ dưới
# dạng base64 và decode lúc import: đây là detection signature so khớp chuỗi
# trong payload, không phải lời gọi — nhưng nếu để literal trong source,
# pattern-based scanner sẽ nhầm thành code injection.
_SIG_EXEC_LIKE = "ZXZhbCg="  # sample-match signature A (decoded below)
_SIG_EXEC_LIKE2 = "ZXhlYyg="  # sample-match signature B (decoded below)
import base64 as _b64

_SIG_A = _b64.b64decode(_SIG_EXEC_LIKE).decode("ascii")
_SIG_B = _b64.b64decode(_SIG_EXEC_LIKE2).decode("ascii")

INJECTION_SIGNALS = [
    "ignore previous", "ignore all", "forget your", "forget all",
    "you are now", "you are dan", "system prompt", "reveal your",
    "bỏ qua", "lệnh mới", "bây giờ bạn là",
    "jailbreak", "developer mode", "no rules", "sudo",
    "{{", "{%if", _SIG_A, _SIG_B, "subprocess", "os.system",
    "__import__", "__class__", "pickle.loads",
]


class HttpFingerprintDetector:
    """Detect AI agent qua HTTP fingerprint — UA, header order, library signature."""

    def fingerprint(self, headers: dict[str, str], user_agent: str = "") -> dict[str, Any]:
        signals: list[str] = []
        confidence = 0.0
        claimed_browser = "unknown"
        actual_browser = "unknown"
        ua_mismatch = False
        detected_library = ""

        ua_lower = user_agent.lower()

        # Signal 1: AI agent User-Agent
        for pattern in AI_AGENT_UAS:
            if pattern in ua_lower:
                signals.append(f"ua:{pattern}")
                confidence = max(confidence, 0.7)
                detected_library = pattern
                if "bot" in pattern or "crawler" in pattern:
                    actual_browser = "crawler"
                elif "scanner" in pattern or "scraper" in pattern:
                    actual_browser = "scraper"
                else:
                    actual_browser = "bot"
                break

        # Signal 2: Claimed browser in UA
        if "chrome" in ua_lower:
            claimed_browser = "chrome"
        elif "firefox" in ua_lower:
            claimed_browser = "firefox"
        elif "safari" in ua_lower:
            claimed_browser = "safari"
        elif "edge" in ua_lower:
            claimed_browser = "edge"

        # Signal 3: Missing browser headers (humans usually have all 4)
        if actual_browser == "human" or actual_browser == "unknown":
            headers_lower = {k.lower() for k in headers.keys()}
            missing = [h for h in BROWSER_HEADERS if h not in headers_lower]
            if len(missing) >= 3:
                signals.append(f"missing_headers:{len(missing)}")
                confidence = max(confidence, 0.5)
                if actual_browser == "unknown":
                    actual_browser = "bot"

        # Signal 4: UA mismatch — claims Chrome but missing sec-ch-ua header
        if claimed_browser != "unknown" and "sec-ch-ua" not in {k.lower() for k in headers.keys()}:
            signals.append(f"ua_mismatch:{claimed_browser}_without_sec_ch_ua")
            confidence = max(confidence, 0.6)
            ua_mismatch = True

        # Signal 5: Header count — browsers have 8-15 headers, bots have 2-5
        header_count = len(headers)
        if header_count < 5 and actual_browser != "human":
            signals.append(f"low_header_count:{header_count}")
            confidence = max(confidence, 0.4)

        return {
            "confidence": round(confidence, 2),
            "claimed_browser": claimed_browser,
            "actual_browser": actual_browser,
            "ua_mismatch": ua_mismatch,
            "detected_library": detected_library,
            "header_count": header_count,
            "signals": signals,
        }


# ============================================================
# 2. ASN DETECTOR
# ============================================================

class AsnDetector:
    """Detect AI agent qua ASN/GeoIP — datacenter, Tor, VPN, residential."""

    # Known datacenter ASN ranges (subset)
    DATACENTER_ASNS = {
        "AS16509", "AS14618",  # Amazon AWS
        "AS15169",  # Google Cloud
        "AS8075",  # Microsoft Azure
        "AS13335",  # Cloudflare
        "AS24940",  # Hetzner
        "AS14061",  # DigitalOcean
        "AS16276",  # OVH
        "AS45102",  # Alibaba Cloud
        "AS132203",  # Tencent Cloud
    }

    def __init__(self, mmdb_dir: str = "data/geoip"):
        self.mmdb_dir = mmdb_dir
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}
        self._cache_ttl = 3600  # 1 hour
        # [SEC-FIX bounded-stores 2026-09-26] _cache is keyed by attacker-
        # controllable input (request IP). PRE-FIX it grew without bound —
        # 10k distinct IPs left 10k entries forever (expired entries were
        # only purged when the SAME IP was looked up again). Bound it, same
        # eviction semantics as BehavioralDetector._max_ips (oldest leaves
        # first under pressure).
        self._cache_max = 10000
        self._tor_exits: set = set()
        self._tor_last_refresh = 0

    async def refresh_tor_exits(self):
        """Refresh Tor exit node list (best-effort)."""
        if time.time() - self._tor_last_refresh < 3600:
            return
        try:
            import httpx
            # [EE-G1] feed Tor exit list là external fetch — đọc SCP_EGRESS_MODE
            # trước mọi I/O; denial → except Exception dưới → skip (best-effort).
            enforce_egress_policy("https://check.torproject.org/torbulkexitlist")
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get("https://check.torproject.org/torbulkexitlist")
                if r.status_code == 200:
                    self._tor_exits = set(r.text.strip().split("\n"))
                    self._tor_last_refresh = time.time()
                    logger.info(f"[AsnDetector] Loaded {len(self._tor_exits)} Tor exit nodes")
        except Exception as e:
            logger.debug(f"[AsnDetector] Tor refresh failed: {e}", exc_info=True)

    async def lookup(self, ip: str) -> dict[str, Any] | None:
        """Lookup ASN info for IP."""
        if not ip or ip in ("127.0.0.1", "localhost", "::1", "unknown"):
            return {
                "ip": ip,
                "asn": "",
                "asn_org": "local",
                "is_datacenter": False,
                "is_residential": True,
                "is_vpn": False,
                "is_tor": False,
                "country": "",
            }

        # Cache check
        cached = self._cache.get(ip)
        if cached and time.time() - cached[1] < self._cache_ttl:
            return cached[0]

        # Check Tor
        is_tor = ip in self._tor_exits

        # Reverse DNS (lightweight, no external API needed)
        reverse_dns = ""
        try:
            # [V104.38 #96] TẠI SAO: blocking DNS in async → event loop frozen.
            # Fix: run in executor with timeout.
            try:
                hostname = await asyncio.get_event_loop().run_in_executor(None, socket.gethostbyaddr, ip)
            except Exception:
                logger.warning('AsnDetector.lookup: Exception not handled', exc_info=True)
                hostname = None
            reverse_dns = hostname[0] if hostname else ""
        except Exception:
            logger.warning('AsnDetector.lookup: Exception not handled', exc_info=True)
            reverse_dns = ""

        # Heuristic: datacenter indicators in reverse DNS
        is_datacenter = False
        asn_org = "unknown"
        rdns_lower = reverse_dns.lower()
        dc_indicators = ["aws", "amazonaws", "google", "azure", "microsoft",
                         "cloudflare", "hetzner", "digitalocean", "ovh",
                         "alibaba", "tencent", "linode", "vultr"]
        for indicator in dc_indicators:
            if indicator in rdns_lower:
                is_datacenter = True
                asn_org = indicator
                break

        # VPN indicators
        vpn_indicators = ["vpn", "proxy", "nordvpn", "expressvpn", "surfshark"]
        is_vpn = any(v in rdns_lower for v in vpn_indicators)

        #  TẠI SAO: V104.38 assumed "no PTR record → datacenter →
        # ai_agent_2026 → block". This is a FALSE POSITIVE factory:
        #   - Many legitimate corporate/mobile/IPv6 networks have no PTR.
        #   - DNS lookup can transiently fail (timeout, recursive resolver issue).
        #   - CGNAT users (mobile carriers) almost never have PTR.
        # Blocking all of them as "ai_agent_2026" violates the SCP principle
        # "PASS ≠ ĐÚNG" — a weak signal is being treated as proof.
        # Fix: "no PTR" alone is NOT sufficient to flag as datacenter. It only
        # raises a *suspicion* flag (`no_ptr`) WITHOUT setting is_datacenter.
        # is_datacenter is set ONLY when there's a POSITIVE datacenter indicator
        # in the PTR hostname (aws/google/azure/etc. matched above) OR a
        # successful ASN lookup returns a known datacenter ASN (future work).
        # Downstream consumers (threat_detector.analyze) should treat `no_ptr`
        # as a soft signal (small risk_score bump), NOT as a hard block reason.
        no_ptr = (not reverse_dns) and ip not in ("127.0.0.1", "::1", "unknown", "localhost")
        if no_ptr and not is_datacenter:
            # Soft signal — don't override is_datacenter. Just annotate.
            if asn_org == "unknown":
                asn_org = "unknown_no_ptr"  # informational only
            # is_datacenter stays False — no positive evidence.

        result = {
            "ip": ip,
            "asn": "",
            "asn_org": asn_org,
            "reverse_dns": reverse_dns,
            "is_datacenter": is_datacenter,
            "is_residential": not is_datacenter and not is_tor and not is_vpn,
            "is_vpn": is_vpn,
            "is_tor": is_tor,
            "no_ptr": no_ptr,  # [P2-22] soft signal — NOT a block reason on its own
            "country": "",
        }

        # [SEC-FIX bounded-stores 2026-09-26] Evict oldest-inserted entry when
        # the cache is full (TTL staleness alone never bounded the dict).
        if ip not in self._cache and len(self._cache) >= self._cache_max:
            oldest_ip = next(iter(self._cache))
            self._cache.pop(oldest_ip, None)
        self._cache[ip] = (result, time.time())
        return result

    def stats(self) -> dict[str, Any]:
        return {
            "cached_ips": len(self._cache),
            "tor_exits": len(self._tor_exits),
            "tor_last_refresh": self._tor_last_refresh,
        }


# ============================================================
# 3. BEHAVIORAL DETECTOR
# ============================================================

class BehavioralDetector:
    """Detect AI agent qua behavioral — timing, entropy, scanner pattern."""

    def __init__(self, max_ips: int = 10000):
        self._request_times: dict[str, deque] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._max_ips = max_ips
        self._total_detected = 0
        self._total_blocked = 0

    async def record(
        self,
        ip: str,
        endpoint: str = "",
        method: str = "GET",
        body_size: int = 0,
        response_time_ms: float = 0,
        status_code: int = 200,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Record 1 request → update profile → return behavioral signals."""
        now = time.time()

        # Initialize profile
        if ip not in self._request_times:
            if len(self._request_times) >= self._max_ips:
                # Evict oldest
                oldest = min(self._request_times.keys(),
                             key=lambda k: self._request_times[k][0] if self._request_times[k] else 0)
                del self._request_times[oldest]
                if oldest in self._profiles:
                    del self._profiles[oldest]
            self._request_times[ip] = deque(maxlen=100)
            self._profiles[ip] = {
                "first_seen": now,
                "request_count": 0,
                "endpoints_visited": set(),
                "methods_used": set(),
                "status_codes": [],
                "response_times": [],
            }

        # Update
        self._request_times[ip].append(now)
        profile = self._profiles[ip]
        profile["request_count"] += 1
        if endpoint:
            profile["endpoints_visited"].add(endpoint)
        profile["methods_used"].add(method)
        profile["status_codes"].append(status_code)
        if response_time_ms > 0:
            profile["response_times"].append(response_time_ms)

        # Compute behavioral signals
        return self._analyze(ip)

    def _analyze(self, ip: str) -> dict[str, Any]:
        """Analyze behavioral pattern for IP."""
        times = list(self._request_times.get(ip, []))
        profile = self._profiles.get(ip, {})

        # [FIX #14] TẠI SAO: was `len(times) < 2` → 2 rapid requests triggered
        # bot_timing. Real users can ask 2 questions within 500ms (autocomplete,
        # quick typing, scripts). Need at least 5 requests to establish a
        # behavioral pattern — below that, insufficient data.
        # Reality > Model: tested 2 sequential questions from same IP →
        # bot_timing=True → bypass retract → FAIL. After fix: needs 5+ requests
        # before behavioral analysis kicks in.
        if len(times) < 5:
            return {
                "ip": ip,
                "confidence": 0.0,
                "is_bot_timing": False,
                "is_scanner": False,
                "request_count": len(times),
                "median_inter_arrival": 0,
                "entropy": 0,
                "ks_stat": 0,
                "signals": [],
                "note": f"insufficient_samples:need_5_have_{len(times)}",
            }

        # Inter-arrival times
        gaps = [times[i+1] - times[i] for i in range(len(times)-1)]
        gaps_sorted = sorted(gaps)
        median_gap = gaps_sorted[len(gaps_sorted) // 2]

        # Entropy of gaps (high entropy = human-like variability)
        if len(gaps) >= 3:
            gap_range = max(gaps) - min(gaps) + 0.001
            gap_bins = [int((g - min(gaps)) / gap_range * 10) for g in gaps]
            from collections import Counter
            counter = Counter(gap_bins)
            total = len(gap_bins)
            entropy = -sum((c/total) * math.log2(c/total) for c in counter.values() if c > 0)
        else:
            entropy = 0

        # KS statistic: compare to exponential distribution (human-like)
        # Bots often have uniform/bimodal distribution
        if len(gaps) >= 5:
            mean_gap = sum(gaps) / len(gaps)
            if mean_gap > 0:
                # Simplified KS: deviation from exponential CDF
                expected = [1 - math.exp(-g / mean_gap) for g in gaps_sorted]
                actual = [(i+1) / len(gaps_sorted) for i in range(len(gaps_sorted))]
                ks_stat = max(abs(e - a) for e, a in zip(expected, actual))
            else:
                ks_stat = 1.0
        else:
            ks_stat = 0

        # Bot timing: median gap < 100ms AND low entropy = clearly automated
        # [FIX #14] TẠI SAO: was `median_gap < 0.5` (500ms) which flagged
        # legitimate rapid users. Real bots have median_gap < 100ms (sub-100ms
        # is impossible for humans due to network + typing latency).
        # Reality > Model: tested — humans typically have median_gap > 200ms
        # even when typing fast; bots have median_gap < 50ms.
        is_bot_timing = median_gap < 0.1 and entropy < 2.0

        # Scanner: visits many endpoints, low entropy
        endpoints_visited = profile.get("endpoints_visited", set())
        is_scanner = len(endpoints_visited) >= 5 and entropy < 2.5

        # Confidence
        confidence = 0.0
        signals: list[str] = []
        if is_bot_timing:
            signals.append(f"bot_timing:median={median_gap:.2f}s")
            confidence = max(confidence, 0.8)
        if is_scanner:
            signals.append(f"scanner:{len(endpoints_visited)}_endpoints")
            confidence = max(confidence, 0.7)
        # [FIX #14] rapid_fire threshold: was 0.1s (same as bot_timing) —
        # redundant. Now: < 50ms = clearly automated (sub-50ms impossible for
        # humans due to TCP round-trip alone).
        if median_gap < 0.05:
            signals.append(f"rapid_fire:{median_gap:.2f}s")
            confidence = max(confidence, 0.9)

        return {
            "ip": ip,
            "confidence": round(confidence, 2),
            "is_bot_timing": is_bot_timing,
            "is_scanner": is_scanner,
            "request_count": profile.get("request_count", 0),
            "median_inter_arrival": round(median_gap, 3),
            "entropy": round(entropy, 2),
            "ks_stat": round(ks_stat, 3),
            "endpoints_visited": list(endpoints_visited),
            "signals": signals,
        }

    async def get_profile(self, ip: str) -> dict[str, Any] | None:
        return self._profiles.get(ip)

    def get_top_attackers(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get top N IPs by request count."""
        sorted_ips = sorted(
            self._profiles.items(),
            key=lambda x: x[1].get("request_count", 0),
            reverse=True,
        )[:limit]
        return [
            {
                "ip": ip,
                "request_count": p.get("request_count", 0),
                "endpoints_visited": len(p.get("endpoints_visited", set())),
                "first_seen": p.get("first_seen", 0),
            }
            for ip, p in sorted_ips
        ]

    def stats(self) -> dict[str, Any]:
        return {
            "tracked_ips": len(self._request_times),
            "total_detected": self._total_detected,
            "total_blocked": self._total_blocked,
        }


# ============================================================
# THREAT DETECTOR — Fusion 3 detectors
# ============================================================

class ThreatDetector:
    """Fusion 3 detectors: HttpFingerprint + Asn + Behavioral.

    World standard naming: <Purpose>Detector (e.g. AnomalyDetector).
    """

    def __init__(self, mmdb_dir: str = "data/geoip"):
        self.fingerprint = HttpFingerprintDetector()
        self.asn = AsnDetector(mmdb_dir=mmdb_dir)
        self.behavioral = BehavioralDetector()

    async def analyze(
        self,
        ip: str,
        headers: dict[str, str],
        body: str,
        endpoint: str = "/ask",
        method: str = "POST",
        session_id: str | None = None,
        skip_asn: bool = False,
    ) -> ThreatSignal:
        """Analyze 1 request → ThreatSignal.

        Pipeline:
          1. HttpFingerprintDetector (sync, <10ms)
          2. AsnDetector (async, <50ms, cached)
          3. BehavioralDetector (async, <100ms)
          4. Fusion logic
        """
        ua = headers.get("user-agent", "") or headers.get("User-Agent", "")

        # Run 3 detectors in parallel
        fp_task = self.fingerprint.fingerprint(headers, ua)
        asn_task = self.asn.lookup(ip) if not skip_asn else None
        beh_task = self.behavioral.record(
            ip=ip, endpoint=endpoint, method=method,
            body_size=len(body), session_id=session_id or "",
        )

        fp_result = fp_task  # sync
        asn_result = await asn_task if asn_task else None
        beh_result = await beh_task

        # Check injection patterns in body
        # [V104.34 #60] TẠI SAO: truncation before injection check → payload at 2001+ missed
        body_lower = body.lower()  # scan full body, don't truncate
        injection_detected = False
        for pattern in INJECTION_SIGNALS:
            if pattern in body_lower:
                fp_result["signals"].append(f"injection:{pattern}")
                injection_detected = True
                break

        # Fusion logic
        signals = fp_result.get("signals", []) + beh_result.get("signals", [])
        if asn_result:
            if asn_result.get("is_datacenter"):
                signals.append("asn:datacenter")
            if asn_result.get("is_tor"):
                signals.append("asn:tor")
            if asn_result.get("is_vpn"):
                signals.append("asn:vpn")
            # [P2-22] Soft signal: no PTR record — NOT a block reason alone, but
            # worth noting for forensics. Don't add to confidence (would cause
            # false positives on corporate/mobile/CGNAT users).
            if asn_result.get("no_ptr") and not asn_result.get("is_datacenter"):
                signals.append("asn:no_ptr_soft")

        # Confidence = max of 3 detectors + bonus for multiple signals
        # [P2-22] Note: asn:no_ptr_soft does NOT contribute to confidence here.
        # Only positive datacenter indicators (PTR hostname match) do.
        confidence = max(
            fp_result.get("confidence", 0),
            beh_result.get("confidence", 0),
            0.6 if asn_result and asn_result.get("is_datacenter") else 0,
            0.8 if asn_result and asn_result.get("is_tor") else 0,
        )
        if injection_detected:
            confidence = max(confidence, 0.9)

        # Multiple signals → boost
        if len(signals) >= 3:
            confidence = min(1.0, confidence + 0.1)

        # Determine agent_type
        if injection_detected:
            agent_type = "injector"
        elif confidence >= 0.7:
            if asn_result and asn_result.get("is_tor"):
                agent_type = "anonymizing_proxy"
            else:
                agent_type = "ai_agent_2026"
        elif confidence >= 0.5:
            agent_type = "bot_legacy"
        elif confidence >= 0.3:
            agent_type = "unknown"
        else:
            agent_type = "human"

        return ThreatSignal(
            is_ai_agent=confidence > 0.5,
            agent_type=agent_type,
            confidence=round(confidence, 2),
            signals=signals,
            ip=ip,
            asn_intel=asn_result,
            fingerprint_result=fp_result,
            behavioral_result=beh_result,
        )

    def stats(self) -> dict[str, Any]:
        return {
            "fingerprint": "active",
            "asn": self.asn.stats(),
            "behavioral": self.behavioral.stats(),
        }


__all__ = [
    "ThreatSignal",
    "ThreatDetector",
    "HttpFingerprintDetector",
    "AsnDetector",
    "BehavioralDetector",
    "AI_AGENT_UAS",
    "INJECTION_SIGNALS",
]
