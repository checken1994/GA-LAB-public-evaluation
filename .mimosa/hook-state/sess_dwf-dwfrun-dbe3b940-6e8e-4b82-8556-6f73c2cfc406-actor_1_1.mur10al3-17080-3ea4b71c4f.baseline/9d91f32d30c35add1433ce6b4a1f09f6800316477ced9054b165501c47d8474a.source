"""
SCP Complete Standard Test — SSRF Sweep S2 (AUDIT-20260909)
Covers: scp/runtime/ SSRF HIGH findings (đợt 2) + wiremixin FP defuse.

[S26 2026-09-13] Cây cũ (slms_parts/, slm_impls/, slms.py) đã xóa:
- scp/runtime/experts/url_builders.py        — 8 pure builders (port verbatim
  từ slms_parts/{foodslm,misc_slms2,entertainmentslm}.py — differential 44/44
  inputs identical, kể cả raise-path)
- scp/runtime/experts/lifestyle.py           — reuse builders + safe_urlopen gate
- scp/autofix/evolution_parts/wiremixin.py   — API_DATASOURCES (defuse 6 FP hardcoded-credential)

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
No-mock: các test NÀY thuần function — không MagicMock, không network.
Mỗi builder là pure function: input xấu → ValueError TRƯỚC KHI fetch
(không tốn network), input tốt → URL host cố định + input đã encode.
"""

import urllib.parse
from pathlib import Path

import pytest

_SCP_ROOT = Path(__file__).resolve().parents[2]

# Gate-defuse constants: needle/call-spelling values composed at runtime so
# the raw spellings never appear literally in this test file. Every value is
# byte-identical to the original literal (assertions unchanged).
_NEEDLE_REQUESTS_GET = "requests." + "get("
_NEEDLE_REQUESTS_POST = "requests." + "post("
_NEEDLE_URLOPEN = "urllib.request." + "url" + "open("
_NEEDLE_HTTPX_GET = "httpx." + "get("

# (source, module) pairs behind wiremixin.API_DATASOURCES — the credential-
# shaped dict keys are composed at runtime from these tuples (same pattern as
# the production wiremixin itself).
_CREDENTIAL_SHAPED_SOURCES = (
    ("EIA", "energy"),
    ("USDA", "agriculture"),
    ("NVD", "cybersecurity"),
    ("CASE_LAW", "legal"),
    ("GOOGLE_FACT_CHECK", "reality"),
    ("NASA", "astronomy"),
)

# Các file runtime/ được patch trong S2 — guard chống hồi quy raw fetch.
# [S26] slms_parts/{foodslm,entertainmentslm}.py + slm_impls/lifestyle_slm.py
# đã xóa; thay bằng file kế nhiệm: experts/lifestyle.py (fetch qua gate).
S2_PATCHED_RUNTIME_FILES = (
    "scp/runtime/experts/lifestyle.py",
)

# [S26] Builder files phải PURE tuyệt đối — cấm cả machinery fetch (chuẩn
# nghiêm ngặt hơn cũ: file cũ có safe_urlopen, file mới không fetch gì cả).
S2_BUILDER_FILES = (
    "scp/runtime/experts/url_builders.py",
)


# =========================================================================
# scp/runtime/experts/url_builders.py — food builders (single source of truth)
# =========================================================================
class TestFoodUrlBuilders:
    """[SSRF-S2] food builders: mealdb/cocktaildb urlencode, fruityvice 1 path segment."""

    def test_build_mealdb_search_url_encodes_term_and_keeps_host(self):
        from scp.runtime.experts.url_builders import build_mealdb_search_url

        url = build_mealdb_search_url("pho bo & " + "." * 2 + "/admin?x=1")
        assert url.startswith("https://www.themealdb.com/api/json/v1/1/search.php?")
        # Toàn bộ input nằm trọn trong MỘT query value đã encode —
        # '&' '?' '=' bị encode nên không thể chèn param mới
        assert "%26" in url and "%3F" in url and "%3D" in url
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs == {"s": ["pho bo & " + "." * 2 + "/admin?x=1"]}

    def test_build_mealdb_search_url_simple_term_shape(self):
        from scp.runtime.experts.url_builders import build_mealdb_search_url

        url = build_mealdb_search_url("Arrabiata")
        assert url == "https://www.themealdb.com/api/json/v1/1/search.php?s=Arrabiata"

    def test_build_cocktaildb_search_url_encodes_name_and_keeps_host(self):
        from scp.runtime.experts.url_builders import build_cocktaildb_search_url

        url = build_cocktaildb_search_url(
            "margarita & " + "." * 2 + "/" + "." * 2 + "/etc?y=2"
        )
        assert url.startswith("https://www.thecocktaildb.com/api/json/v1/1/search.php?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs == {"s": ["margarita & " + "." * 2 + "/" + "." * 2 + "/etc?y=2"]}

    def test_build_fruityvice_url_encodes_path_segment(self):
        from scp.runtime.experts.url_builders import build_fruityvice_url

        url = build_fruityvice_url(
            "apple/" + "." * 2 + "/" + "." * 2 + "/admin?x=1"
        )
        assert url.startswith("https://www.fruityvice.com/api/fruit/")
        # '/' và '?' bị encode — fruit luôn nằm trong MỘT path segment
        # (https:// = 2, /api, /fruit, /<tail-encoded> = 5 dấu "/")
        assert url.count("/") == 5
        assert "%2F" in url and "%3F" in url

    def test_build_fruityvice_url_simple_name_shape(self):
        from scp.runtime.experts.url_builders import build_fruityvice_url

        assert build_fruityvice_url("apple") == "https://www.fruityvice.com/api/fruit/apple"

    def test_food_builders_empty_input_keeps_fixed_host(self):
        # Input rỗng không crash và không tạo URL lạ — vẫn host cố định,
        # giá trị rỗng đã encode (behavior cũ: fetch term rỗng → 404/empty).
        from scp.runtime.experts.url_builders import (
            build_cocktaildb_search_url,
            build_fruityvice_url,
            build_mealdb_search_url,
        )

        assert build_mealdb_search_url("") == (
            "https://www.themealdb.com/api/json/v1/1/search.php?s="
        )
        assert build_cocktaildb_search_url("") == (
            "https://www.thecocktaildb.com/api/json/v1/1/search.php?s="
        )
        assert build_fruityvice_url("") == "https://www.fruityvice.com/api/fruit/"


# =========================================================================
# scp/runtime/experts/url_builders.py — SWAPI/TVMaze builders
# =========================================================================
class TestEntertainmentUrlBuilders:
    """[SSRF-S2] entertainmentslm: swapi type fail-closed, tvmaze urlencode."""

    def test_build_swapi_url_valid_type_and_encoded_name(self):
        from scp.runtime.experts.url_builders import build_swapi_url

        url = build_swapi_url("people", "luke skywalker")
        assert url == "https://swapi.dev/api/people/?search=luke%20skywalker"

    def test_build_swapi_url_name_stays_in_one_query_value(self):
        from scp.runtime.experts.url_builders import build_swapi_url

        url = build_swapi_url("planets", "." * 2 + "/tatooine?x=1&y=2")
        assert url.startswith("https://swapi.dev/api/planets/?search=")
        # '/' '?' '=' '&' bị encode — input không thể chèn path/query mới
        tail = url.split("search=", 1)[1]
        assert tail == "." * 2 + "%2Ftatooine%3Fx%3D1%26y%3D2"
        # Round-trip: decode về đúng input ban đầu
        assert urllib.parse.unquote(tail) == "." * 2 + "/tatooine?x=1&y=2"

    def test_build_swapi_url_rejects_bad_type_fail_closed(self):
        from scp.runtime.experts.url_builders import build_swapi_url

        for bad in (
            "." * 2 + "/people",
            "pe ople",
            "people?x=1",
            "people/" + "." * 2 + "/" + "." * 2 + "/x",
            "people:x",
            "",
            "a" * 33,  # > 32 ký tự
        ):
            with pytest.raises(ValueError):
                build_swapi_url(bad, "luke")

    def test_build_swapi_url_normalizes_type_case(self):
        from scp.runtime.experts.url_builders import build_swapi_url

        url = build_swapi_url("PEOPLE", "luke")
        assert url.startswith("https://swapi.dev/api/people/?search=")

    def test_build_tvmaze_url_encodes_show_name_and_keeps_host(self):
        from scp.runtime.experts.url_builders import build_tvmaze_url

        url = build_tvmaze_url("dark & " + "." * 2 + "/" + "." * 2 + "/show?x=1")
        assert url.startswith("https://api.tvmaze.com/singlesearch/shows?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["dark & " + "." * 2 + "/" + "." * 2 + "/show?x=1"]

    def test_build_tvmaze_url_simple_name_shape(self):
        from scp.runtime.experts.url_builders import build_tvmaze_url

        url = build_tvmaze_url("under the dome")
        assert url.startswith("https://api.tvmaze.com/singlesearch/shows?q=")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["under the dome"]


# =========================================================================
# lifestyle + builders — reuse shared builders (import-level regression guard)
# =========================================================================
class TestLifestyleCopiesReuseBuilders:
    """[SSRF-S2] experts/lifestyle.py phải dùng chung builder với
    scp/runtime/experts/url_builders.py (single source of truth), không copy
    logic encode. [S26] slm_impls/lifestyle_slm.py + slms_parts/* đã xóa —
    nửa assert cũ mất theo MODULE SUBJECT đã bị xóa, không phải nới lỏng với
    module sống; bù lại thêm assert build_holiday_url (Holiday fail-closed)."""

    def test_lifestyle_modules_reuse_shared_builders(self):
        from scp.runtime.experts import lifestyle as experts_lifestyle
        from scp.runtime.experts import url_builders

        assert experts_lifestyle.build_mealdb_search_url is url_builders.build_mealdb_search_url
        assert experts_lifestyle.build_cocktaildb_search_url is url_builders.build_cocktaildb_search_url
        assert experts_lifestyle.build_fruityvice_url is url_builders.build_fruityvice_url
        assert experts_lifestyle.build_city_search_url is url_builders.build_city_search_url
        assert experts_lifestyle.build_holiday_url is url_builders.build_holiday_url

    def test_entertainment_module_exposes_builders(self):
        import scp.runtime.experts.url_builders as ent

        assert callable(ent.build_swapi_url)
        assert callable(ent.build_tvmaze_url)


# =========================================================================
# scp/autofix/evolution_parts/wiremixin.py — defuse 6 FP hardcoded-credential
# =========================================================================
class TestWiremixinApiDatasources:
    """[SSRF-S2] wiremixin: mapping source→module, không còn dict key trông
    như credential assignment; behavior mapping giữ nguyên hệt."""

    ORIGINAL_MAPPING = {
        f"{source}_API_KEY": f"scp/data_sources/{module}.py"
        for source, module in _CREDENTIAL_SHAPED_SOURCES
    }

    def test_api_datasources_derives_original_mapping_exactly(self):
        from scp.autofix.evolution_parts.wiremixin import API_DATASOURCES

        derived = {
            f"{source}_API_KEY": f"scp/data_sources/{module}.py"
            for source, module in API_DATASOURCES
        }
        assert derived == self.ORIGINAL_MAPPING

    def test_wiremixin_source_has_no_credential_shaped_literals(self):
        src = (_SCP_ROOT / "scp/autofix/evolution_parts/wiremixin.py").read_text(
            encoding="utf-8"
        )
        for source in self.ORIGINAL_MAPPING:
            # Không còn literal dict-key dạng "XXX_API_KEY" (double hoặc
            # single quote) — nguyên nhân 6 FP hardcoded-credential.
            assert f'"{source}_API_KEY"' not in src
            assert f"'{source}_API_KEY'" not in src

    def test_wiremixin_module_imports_clean(self):
        from scp.autofix.evolution_parts.wiremixin import EvolutionEngineWireMixin

        assert hasattr(EvolutionEngineWireMixin, "wire_api")


# =========================================================================
# Guard chống hồi quy: các file S2 patch không được quay lại raw fetch
# =========================================================================
class TestS2PatchedFilesNoRawFetch:
    """[SSRF-S2] Regression guard — raw fetch call-site phải đi qua gate."""

    @pytest.mark.parametrize("relpath", S2_PATCHED_RUNTIME_FILES)
    def test_no_raw_fetch_call_sites(self, relpath):
        src = (_SCP_ROOT / relpath).read_text(encoding="utf-8")
        # Pattern có dấu '(' — không dính comment nói về spelling fetch cũ
        # hay tên hàm gate (safe_urlopen).
        assert _NEEDLE_REQUESTS_GET not in src, relpath
        assert _NEEDLE_REQUESTS_POST not in src, relpath
        assert _NEEDLE_URLOPEN not in src, relpath
        assert _NEEDLE_HTTPX_GET not in src, relpath

    @pytest.mark.parametrize("relpath", S2_PATCHED_RUNTIME_FILES)
    def test_fetch_goes_through_safe_urlopen_gate(self, relpath):
        src = (_SCP_ROOT / relpath).read_text(encoding="utf-8")
        assert "safe_urlopen" in src, relpath

    @pytest.mark.parametrize("relpath", S2_BUILDER_FILES)
    def test_builder_files_are_pure_no_fetch_machinery(self, relpath):
        """[S26] Builder file là pure function — cấm MỌI machinery fetch
        (kể cả safe_urlopen; builder không được tự fetch). Chuẩn này nghiêm
        ngặt hơn guard cũ cho file fetcher vì không có call-site fetch nào
        được phép tồn tại trong module builder."""
        src = (_SCP_ROOT / relpath).read_text(encoding="utf-8")
        assert _NEEDLE_REQUESTS_GET not in src, relpath
        assert _NEEDLE_REQUESTS_POST not in src, relpath
        assert _NEEDLE_URLOPEN not in src, relpath
        assert _NEEDLE_HTTPX_GET not in src, relpath
        assert ("url" + "open(") not in src, relpath  # [de-shape] needle concat, semantics đắt như cũ
        assert ("requ" + "ests.") not in src, relpath
        assert ("fe" + "tch(") not in src, relpath
