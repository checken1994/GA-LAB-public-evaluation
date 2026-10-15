"""
SCP - Viet Nam | Self-Correcting Pipeline
 CybersecurityDataSource - Data source cho An ninh mạng
"""

import logging
import os
import re as _re
from typing import Any

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.interfaces.data_source import IDataSource, shared_health_ping

logger = logging.getLogger(__name__)
# [V104.32 #13] word-boundary matching for short keys

# [V5.8-API] CVE ID regex (e.g., CVE-2024-12345, CVE-2023-30768)
_CVE_PATTERN = _re.compile(r'CVE-\d{4}-\d{4,7}', _re.IGNORECASE)


class CybersecurityDataSource(IDataSource):
    """
    Data source cho các câu hỏi An ninh mạng.
    Hỗ trợ: attack types, vulnerabilities, best practices, CVE lookups.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        # [V5.8-API] NVD API key (optional, raises rate-limit when absent)
        self._nvd_api_key = os.environ.get("NVD_API_KEY", "").strip()

        # Common attacks
        self._attacks = {
            "phishing": "Lừa đảo qua email/website giả mạo",
            "DDoS": "Tấn công từ chối dịch vụ phân tán",
            "SQL injection": "Chèn mã SQL độc hại vào input",
            "XSS": "Cross-Site Scripting - chèn script vào web",
            "MITM": "Man-in-the-Middle - chen giữa 2 bên giao tiếp",
            "ransomware": "Mã hóa dữ liệu đòi tiền chuộc",
            "brute force": "Thử tất cả password có thể",
            "social engineering": "Thao túng con người để lấy thông tin",
        }

        # Password recommendations
        self._password_tips = {
            "minimum length": 12,
            "use upper and lower": True,
            "use numbers": True,
            "use symbols": True,
            "avoid dictionary words": True,
            "use unique for each": True,
            "use password manager": True,
        }

        # Encryption standards
        self._encryption = {
            "AES-128": "128-bit key, deprecated for sensitive",
            "AES-256": "256-bit key, current standard",
            "RSA-2048": "2048-bit key, for asymmetric",
            "RSA-4096": "4096-bit key, high security",
            "SHA-256": "256-bit hash, current standard",
            "bcrypt": "adaptive hash, password storage",
        }


    @property
    def name(self) -> str:
        return "CybersecurityDataSource"

    @property
    def priority(self) -> int:
        return 5

    @property
    def ttl(self) -> int:
        return 86400

    def get_supported_intents(self) -> list[str]:
        return ["lookup", "query", "fact"]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        return True

    def fetch(self, intent: str, entity: str, **kwargs):
        result = self.query(entity or intent)
        if result.get("found"):
            return {"value": result.get("answer", ""), "source": "Cybersecurity", "metadata": result}
        return None

    def health_check(self) -> bool:
        """[AUDIT-FIX low-4] Fail-closed: ping CIRCL CVE search API (endpoint
        công khai `api/dbinfo`, không cần key). Trước đây hardcode
        `return True` — fail-open, không có bằng chứng. Bất kỳ HTTP response
        nào chứng minh service sống; exception (egress denied, DNS, timeout)
        → False. Local CVE/attack knowledge không được OR vào kết quả —
        degraded chỉ báo qua log.

        [V104.32] Kết quả ping đi qua shared negative-result cache
        cross-instance (`shared_health_ping`): trong TTL
        (SCP_HEALTH_NEG_CACHE_TTL, default 60s) các lần gọi sau trả lại quan
        sát gần nhất — kể cả False (đó là reality gần nhất, không fake health)
        — mà KHÔNG re-ping."""
        import time
        healthy = shared_health_ping(type(self).__name__, self._live_ping)
        self._cache['_health_cache'] = healthy
        self._cache['_health_cache_ts'] = time.time()
        return healthy

    def _live_ping(self) -> bool:
        """[V104.32] Ping thật (1 network round-trip) — chỉ gọi qua
        shared_health_ping để được dedupe theo TTL."""
        api_ok = False
        try:
            from scp.security.url_safety import safe_urlopen  # [AUDIT-FIX low-4]
            # [SSRF-S1] safe_urlopen cho health ping (URL cố định).
            with safe_urlopen("https://cve.circl.lu/api/dbinfo", timeout=3):
                api_ok = True
        except Exception as e:
            logger.warning(f"[Cybersecurity] health ping failed: {e}", exc_info=True)
        if not api_ok:
            logger.warning(
                "[Cybersecurity] health_check: CVE API unreachable — báo unhealthy "
                "(fail-closed); local knowledge vẫn trả lời được query (degraded)"
            )
        return api_ok

    def query(self, question: str) -> dict[str, Any]:
        """Query cybersecurity data."""
        q = question.lower().strip()

        if q in self._cache:
            return self._cache[q]

        result = {"found": False, "answer": None, "confidence": 0.0}

        # Check attacks
        for attack, description in self._attacks.items():
            if attack.lower() in q:  # [V104.32 #13] was: uppercase attack never matched lowercased q:
                result = {
                    "found": True,
                    "answer": f"{attack}: {description}",
                    "confidence": 1.0,
                    "source": "Cybersecurity Database"
                }
                break

        # Check encryption
        for standard, info in self._encryption.items():
            if standard in q:
                result = {
                    "found": True,
                    "answer": f"{standard}: {info}",
                    "confidence": 1.0,
                    "source": "Encryption Standards"
                }
                break

        # [V5.8-API] Local DB miss → try CVE/NVD APIs.
        # Two paths:
        #  (a) Question contains an explicit CVE ID (e.g. "CVE-2024-1234")
        #      → call circl.lu for that specific CVE.
        #  (b) Question is a keyword (e.g. "log4j", "openssl vulnerability")
        #      → call NVD keywordSearch endpoint.
        if not result.get("found"):
            api_result = self._fetch_from_cve_api(question)
            if api_result:
                result = api_result

        self._cache[q] = result
        return result

    # [V5.8-API] CVE / NVD integration
    def _fetch_from_cve_api(self, question: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Fetch vulnerability data from public CVE APIs.
        - circl.lu: lookup by CVE ID (free, no key)
        - NVD: keyword search (free, optional api_key raises rate-limit)
        Returns dict or None.
        """
        if not question or not question.strip():
            return None
        text = question.strip()

        # Path (a): explicit CVE ID present
        cve_match = _CVE_PATTERN.search(text)
        if cve_match:
            cve_id = cve_match.group(0).upper()
            return self._fetch_circl(cve_id)

        # Path (b): keyword search via NVD
        # Strip common English/Vietnamese stop words to build a clean keyword
        cleaned = _re.sub(
            r'\b(what|is|the|a|an|of|for|on|about|là|gì|của|về|tìm|thông\s+tin)\b',
            ' ', text, flags=_re.IGNORECASE,
        ).strip()
        keyword = _re.sub(r'\s+', ' ', cleaned).strip()
        if len(keyword) < 3:
            return None
        return self._fetch_nvd_keyword(keyword)

    def _fetch_circl(self, cve_id: str) -> dict[str, Any] | None:
        """[V5.8-API] circl.lu CVE lookup by ID.
        Handles BOTH the legacy schema (id/summary/cvss) and the CVE 5.0
        record schema (cveMetadata / containers.cna.descriptions).
        """
        url = f"https://cve.circl.lu/api/cve/{cve_id}"
        try:
            data = fetch_with_retry(url, headers={"User-Agent": "SCP/1.0"}, timeout=5)
            if not data or not isinstance(data, dict):
                return None

            summary = ''
            cvss = ''

            # Path A: legacy schema (id / summary / cvss at top level)
            summary = data.get('summary') or data.get('description') or ''
            cvss = data.get('cvss') or data.get('cvss-vector') or ''

            # Path B: CVE 5.0 record schema (cveMetadata + containers.cna)
            if not summary:
                cna = (data.get('containers') or {}).get('cna') or {}
                # descriptions: list of {lang, value}
                for d in cna.get('descriptions', []) or []:
                    if d.get('lang') == 'en' and d.get('value'):
                        summary = d['value']
                        break
                # metrics: list of dicts containing cvssV3_1 / cvssV3_0 / cvssV2
                if not cvss:
                    for m in cna.get('metrics', []) or []:
                        for k in ('cvssV3_1', 'cvssV3_0', 'cvssV2'):
                            v = m.get(k)
                            if isinstance(v, dict):
                                score = v.get('baseScore')
                                vec = v.get('vectorString', '')
                                if score is not None:
                                    cvss = f"{k} baseScore={score} {vec}".strip()
                                    break
                        if cvss:
                            break

            if not summary and not cvss:
                return None
            answer_parts = [f"{cve_id}:"]
            if summary:
                answer_parts.append(f"  {summary[:500]}")
            if cvss:
                answer_parts.append(f"  CVSS: {cvss}")
            return {
                "found": True,
                "answer": "\n".join(answer_parts),
                "confidence": 0.9,
                "source": "CVE circl.lu API",
                "cve_id": cve_id,
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] circl.lu CVE fetch failed for {cve_id}: {e}", exc_info=True)
            return None

    def _fetch_nvd_keyword(self, keyword: str) -> dict[str, Any] | None:
        """[V5.8-API] NVD CVE keyword search."""
        from urllib.parse import quote
        api_key_param = f"&apiKey={self._nvd_api_key}" if self._nvd_api_key else ""
        url = (
            f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            f"?keywordSearch={quote(keyword)}&resultsPerPage=3{api_key_param}"
        )
        try:
            data = fetch_with_retry(url, headers={"User-Agent": "SCP/1.0"}, timeout=8)
            if not data:
                return None
            vulns = data.get('vulnerabilities', [])
            if not vulns:
                return None
            cve_entries = []
            for v in vulns[:3]:
                cve = v.get('cve', {})
                cve_id = cve.get('id', '')
                descriptions = cve.get('descriptions', [])
                desc = next((d['value'] for d in descriptions if d.get('lang') == 'en'), '')
                if cve_id and desc:
                    cve_entries.append(f"{cve_id}: {desc[:300]}")
            if not cve_entries:
                return None
            return {
                "found": True,
                "answer": "\n".join(cve_entries),
                "confidence": 0.85,
                "source": "NVD CVE API (keyword)",
                "keyword": keyword,
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] NVD keyword search failed for '{keyword}': {e}", exc_info=True)
            return None
