# SCP CIRCUIT: M12 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M12-closure.json)
"""
[Task 8-A] NASA APOD source handler — extracted from why_engine.py

TẠI SAO: WhyEngine._query_nasa() was 13 LOC inline. Extracted as standalone
function for modularity. Backward-compatible — WhyEngine delegates.
"""
from __future__ import annotations

import json as _json
import logging
import os
import urllib.request
from urllib.parse import urlencode

from scp.core.api_utils import redact_query_secrets  # [AUDIT-FIX low-8]
from scp.security.url_safety import safe_urlopen, validate_url

logger = logging.getLogger("scp.why.sources.nasa")

# [GLM-AUDIT-FIX] Read NASA API key from environment; DEMO_KEY is public fallback
_NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
_NASA_DEFAULT_BASE = "https://api.nasa.gov"


def _validate_nasa_base(base: str, *, allow_internal: bool) -> str:
    """[Mimosa residual 2026-09-30] Validate + chuẩn hoá base URL NASA API
    trước khi nối chuỗi thành URL request.

    `base` bắt nguồn từ biến môi trường (SCP_WHY_NASA_BASE) — nguồn mà
    scanner đánh dấu là taint vào SSRF sink (safe_urlopen → server-side
    request). Ranh giới được khai báo tại đây bằng validate_url (scheme
    allowlist + chặn IP private/loopback trừ khi allow_internal=True cho
    override loopback của test/dev), sau đó URL được dựng LẠI từ các thành
    phần ĐÃ validate (scheme://netloc + path) thay vì dùng chuỗi env thô.
    Raises ValueError trên base không hợp lệ (fail-closed; caller đã có
    try/except log-redact sẵn). LƯU Ý: chỉ flow env-override đi qua hàm
    này — default base là hằng số tin cậy trong code (không phải env), đúng
    shape đã được chứng minh sạch ở _call_openrouter.py
    (env → _validate_* → f-string → safe_urlopen).
    """
    parsed = validate_url(base, allow_internal=allow_internal)
    _path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{_path}"


def query_nasa(target: str) -> str | None:
    """Query NASA APOD."""
    try:
        # [M12-FIX PF-5] Endpoint seam (same trust level as OPENAI_BASE_URL):
        # SCP_WHY_NASA_BASE redirects the API host (default unchanged:
        # https://api.nasa.gov). When overridden, loopback/private targets are
        # explicitly allowed; default path keeps SSRF protection.
        _base_override = os.environ.get("SCP_WHY_NASA_BASE")
        _allow_internal = bool(_base_override)
        _nasa_base = (
            _validate_nasa_base(_base_override, allow_internal=True)
            if _base_override
            else _NASA_DEFAULT_BASE
        )
        # [Mimosa residual 2026-09-30] api_key (env-derived) không còn được
        # nội suy thô vào URL: đi qua urlencode() — ranh giới encode mà
        # scanner nhận diện, đồng thời percent-encode đúng chuẩn cho giá trị
        # key bất kỳ. URL đích (scheme+host) đã được validate ở trên; mọi log
        # /exception path vẫn qua redact_query_secrets như [AUDIT-FIX low-8].
        _query = urlencode({"api_key": _NASA_API_KEY})
        url = f"{_nasa_base}/planetary/apod?{_query}"
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-WHY/1.0"})
        with safe_urlopen(req, timeout=8, allow_internal=_allow_internal) as resp:
            data = _json.loads(resp.read().decode('utf-8'))
            return data.get("title", "") + ": " + data.get("explanation", "")[:100]
        return None
    except Exception as e:  # [RC-7 FIX Task 6-B] silent swallow → log context
        # [AUDIT-FIX low-8] URL chứa api_key → exception (vd: ValueError
        # "unparseable URL ..." từ url_safety) có thể nhúng cả URL vào message.
        # Mọi text chạm log phải qua redact_query_secrets.
        logger.warning(
            "[why_sources.nasa] failed for target='%s': %s",
            target, redact_query_secrets(str(e)),
        exc_info=True)
        return None

