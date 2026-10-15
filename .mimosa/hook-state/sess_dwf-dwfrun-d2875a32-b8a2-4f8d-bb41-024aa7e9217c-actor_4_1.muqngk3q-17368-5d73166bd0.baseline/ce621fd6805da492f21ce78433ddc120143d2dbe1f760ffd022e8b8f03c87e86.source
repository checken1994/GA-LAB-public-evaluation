"""
[S26 expert-unification 2026-09-13] URL builders — single source of truth.

Nguồn gốc: các builder được port VERBATIM (giữ nguyên behavior, không đổi
logic encode/validate) từ cây cũ đang bị xóa:
  - scp/runtime/slms_parts/foodslm.py          → build_mealdb_search_url,
    build_cocktaildb_search_url, build_fruityvice_url
  - scp/runtime/slms_parts/misc_slms2.py       → build_holiday_url,
    build_city_search_url, build_bible_url
  - scp/runtime/slms_parts/entertainmentslm.py → build_swapi_url,
    build_tvmaze_url

TẠI SAO: cây cũ (slms.py + slm_impls/ + slms_parts/) là thế hệ SLM thứ 2
đã bị thế hệ mới (scp/runtime/experts/, cây mà judge.py tự discovery) thay
thế. Toàn bộ tree cũ là dead code trừ các pure builder này — chúng là SSRF
gate (AUDIT-20260909 S2/MACH2-BUG3): chặn/encode input xấu TRƯỚC khi có bất
kỳ fetch nào; host luôn là literal cố định trong builder — caller không thể
đổi host. Consumer: scp/runtime/experts/lifestyle.py + tests/T03_capability/
test_ssrf_sweep_s2.py + tests/T02_contract/test_flow_02_ask_chat_scp_standard.py.

Mọi builder là pure function (không network, không I/O).
"""
from __future__ import annotations

import re
import urllib.parse

_HOLIDAY_COUNTRY_CODE_RE = re.compile(r"^[A-Za-z]{2}$")
_SWAPI_TYPE_RE = re.compile(r"^[a-z0-9_]{1,32}$")


# ============================================================
# food builders (port verbatim từ slms_parts/foodslm.py)
# ============================================================
def build_mealdb_search_url(term: str) -> str:
    """TheMealDB search URL — term được urlencode thành query value.

    Mọi ký tự đặc biệt (kể cả '../', '?', '&') nằm trọn trong MỘT query
    value nên không thể đổi host/path."""
    query = urllib.parse.urlencode({"s": str(term or "")})
    return f"https://www.themealdb.com/api/json/v1/1/search.php?{query}"


def build_cocktaildb_search_url(name: str) -> str:
    """TheCocktailDB search URL — name được urlencode thành query value."""
    query = urllib.parse.urlencode({"s": str(name or "")})
    return f"https://www.thecocktaildb.com/api/json/v1/1/search.php?{query}"


def build_fruityvice_url(fruit: str) -> str:
    """Fruityvice URL — fruit quote(safe='') → '/' và '..' không thể tạo
    path traversal (luôn nằm trong MỘT path segment đã encode)."""
    quoted = urllib.parse.quote(str(fruit or ""), safe="")
    return f"https://www.fruityvice.com/api/fruit/{quoted}"


# ============================================================
# misc builders (port verbatim từ slms_parts/misc_slms2.py)
# ============================================================
def build_holiday_url(year: int, country_code: str) -> str:
    """date.nager.at URL — country_code PHẢI là đúng 2 chữ cái ISO alpha-2.

    Raises ValueError trên input xấu (vd '../', 'X', script) TRƯỚC KHI fetch —
    fail-closed, không bao giờ ghép input chưa validate vào URL.
    """
    code = str(country_code or "").strip()
    if not _HOLIDAY_COUNTRY_CODE_RE.fullmatch(code):
        raise ValueError(f"invalid_country_code:{code[:32]!r}")
    return f"https://date.nager.at/api/v3/PublicHolidays/{int(year)}/{code}"


def build_city_search_url(city: str) -> str:
    """Open-Meteo geocoding URL — city được percent-encode via urlencode.

    Host cố định; mọi ký tự đặc biệt (kể cả '../', '?', '&') bị encode thành
    giá trị query nên không thể đổi host/path.
    """
    query = urllib.parse.urlencode({
        "name": str(city or ""),
        "count": 1,
        "language": "en",
        "format": "json",
    })
    return f"https://geocoding-api.open-meteo.com/v1/search?{query}"


def build_bible_url(ref: str) -> str:
    """bible-api.com URL — ref được quote(safe='') → '/' và '..' không thể
    tạo path traversal (luôn nằm trong MỘT path segment đã encode)."""
    quoted = urllib.parse.quote(str(ref or ""), safe="")
    return f"https://bible-api.com/{quoted}?translation=kjv"


# ============================================================
# entertainment builders (port verbatim từ slms_parts/entertainmentslm.py)
# ============================================================
def build_swapi_url(api_type: str, name: str) -> str:
    """SWAPI search URL — api_type PHẢI fullmatch ^[a-z0-9_]{1,32}$ (không
    chứa '/', '?', ':', scheme-override); name quote(safe='') nên luôn nằm
    trong MỘT query value đã encode.

    Raises ValueError trên input xấu TRƯỚC KHI fetch — fail-closed."""
    t = str(api_type or "").strip().lower()
    if not _SWAPI_TYPE_RE.fullmatch(t):
        raise ValueError(f"invalid_swapi_type:{t[:32]!r}")
    quoted = urllib.parse.quote(str(name or ""), safe="")
    return f"https://swapi.dev/api/{t}/?search={quoted}"


def build_tvmaze_url(show_name: str) -> str:
    """TVMaze singlesearch URL — show_name được urlencode thành query value."""
    query = urllib.parse.urlencode({"q": str(show_name or "")})
    return f"https://api.tvmaze.com/singlesearch/shows?{query}"
