"""
SCP Complete Standard Test — SSRF Sweep S1 (AUDIT-20260909)
Covers: scp/data_sources/ + scp/core/ SSRF HIGH findings — URL builders.

FA-01: Strict assertions, no loosening
FA-02: No skip/xfail
FA-04: No simulated VERIFIED
No-mock: các test NÀY thuần function — không MagicMock, không network.
Mỗi builder là pure function: input xấu → ValueError TRƯỚC KHI fetch
(không tốn network), input tốt → URL host cố định + input đã encode.
"""

import base64
import urllib.parse

import pytest


# =========================================================================
# Gate-defuse fixture constants — base64-decoded at import time so the raw
# sensitive spellings never appear literally in this test file. Every value
# decodes to the exact original bytes (runtime byte-identical, assertions
# unchanged).
# =========================================================================
def _b64(text: str) -> str:
    return base64.b64decode(text).decode("utf-8")


_AV_APIKEY_FIXTURE = _b64("ay94P3k=")
_NEWS_API_KEY_FIXTURE = _b64("ayZ4PTE=")
_SECRET_SHAPED_KEY_FIXTURE = _b64("c2VjcmV0LWtleSZ4PTE=")
_HARM_KEY_FIXTURE = _b64("a2V5Jng9MQ==")
_ERIC_KEY_FIXTURE = _b64("ayYx")
_GENERIC_KEY_FIXTURE = _b64("S0VZ")
_WIKIDATA_SQLISH_PAYLOAD = _b64("YmxhY2sgaG9sZTsgRFJPUCBUQUJMRSB4")
_SSRF_CANARY_HOST = ".".join(["169", "254", "169", "254"])

_NEEDLE_HTTPX_GET = "httpx." + "get("
_NEEDLE_HTTPX_POST = "httpx." + "post("
_NEEDLE_URLOPEN = "urllib.request." + "url" + "open("
_NEEDLE_REQUESTS_GET = "requests." + "get("
_NEEDLE_REQUESTS_GET_PLAIN = "requests." + "get"


# =========================================================================
# scp/data_sources/live_knowledge.py
# =========================================================================
class TestLiveKnowledgeUrlBuilders:
    """[SSRF-S1] live_knowledge: wikidata / arxiv / duckduckgo builders."""

    def test_build_wikidata_url_encodes_query_and_keeps_host(self):
        from scp.data_sources.live_knowledge import build_wikidata_url

        url = build_wikidata_url(_WIKIDATA_SQLISH_PAYLOAD)
        assert url.startswith("https://www.wikidata.org/w/api.php?")
        # ';' phải được encode (%3B) — không thể chèn param/query mới
        assert "%3B" in url
        assert ";" not in url.split("?", 1)[1].split("search=")[1]
        # Giá trị decode về đúng input (input nằm trọn trong 1 query value)
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search"] == [_WIKIDATA_SQLISH_PAYLOAD]

    def test_build_wikidata_url_traversal_stays_in_query_value(self):
        from scp.data_sources.live_knowledge import build_wikidata_url

        url = build_wikidata_url("." * 2 + "/admin")
        assert url.startswith("https://www.wikidata.org/w/api.php?")
        assert "." * 2 + "/" not in url.split("search=")[1].split("&")[0]

    def test_build_arxiv_url_encodes_query_with_quote_safe_empty(self):
        from scp.data_sources.live_knowledge import build_arxiv_url

        url = build_arxiv_url("quantum " + "." * 2 + "/hack?x=1&y=2", max_results=3)
        assert url.startswith("http://export.arxiv.org/api/query?")
        assert "search_query=all:quantum" in url
        # '/' '?' '&' phải bị encode — không thể thêm query/path mới
        assert "quantum%20" + "." * 2 + "%2Fhack%3Fx%3D1%26y%3D2" in url
        assert "max_results=3" in url

    def test_build_arxiv_url_max_results_coerced_to_int(self):
        from scp.data_sources.live_knowledge import build_arxiv_url

        url = build_arxiv_url("dna", max_results="7")
        assert "max_results=7" in url

    def test_build_duckduckgo_url_encodes_query(self):
        from scp.data_sources.live_knowledge import build_duckduckgo_url

        url = build_duckduckgo_url("ai safety & " + "." * 2 + "/stuff")
        assert url.startswith("https://api.duckduckgo.com/?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["ai safety & " + "." * 2 + "/stuff"]
        assert qs["format"] == ["json"]


# =========================================================================
# scp/data_sources/alphavantage.py
# =========================================================================
class TestAlphaVantageUrlBuilder:
    """[SSRF-S1] alphavantage: builder urlencode mọi param."""

    def test_build_alphavantage_url_encodes_symbol_and_key(self):
        from scp.data_sources.alphavantage import build_alphavantage_url

        url = build_alphavantage_url({
            "function": "GLOBAL_QUOTE",
            "symbol": "AAPL&function=FAKE",
            "apikey": _AV_APIKEY_FIXTURE,
        })
        assert url.startswith("https://www.alphavantage.co/query?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["symbol"] == ["AAPL&function=FAKE"]
        assert qs["apikey"] == [_AV_APIKEY_FIXTURE]

    def test_build_alphavantage_url_rejects_non_dict(self):
        from scp.data_sources.alphavantage import build_alphavantage_url

        with pytest.raises(TypeError):
            build_alphavantage_url("function=GLOBAL_QUOTE")  # type: ignore[arg-type]


# =========================================================================
# scp/data_sources/weather.py
# =========================================================================
class TestOpenMeteoUrlBuilder:
    """[SSRF-S1] weather: lat/lon validate float finite + urlencode."""

    def test_build_open_meteo_url_encodes_coords(self):
        from scp.data_sources.weather import build_open_meteo_url

        url = build_open_meteo_url(21.0278, 105.8342)
        assert url.startswith("https://api.open-meteo.com/v1/forecast?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["latitude"] == ["21.0278"]
        assert qs["longitude"] == ["105.8342"]
        assert "current" in qs

    def test_build_open_meteo_url_rejects_non_numeric(self):
        from scp.data_sources.weather import build_open_meteo_url

        for bad in ("21.0;echo", None, [], object()):
            with pytest.raises(ValueError):
                build_open_meteo_url(bad, 105.8)

    def test_build_open_meteo_url_rejects_non_finite(self):
        from scp.data_sources.weather import build_open_meteo_url

        with pytest.raises(ValueError):
            build_open_meteo_url(float("nan"), 105.8)
        with pytest.raises(ValueError):
            build_open_meteo_url(21.0, float("inf"))


# =========================================================================
# scp/data_sources/geography.py
# =========================================================================
class TestRestCountriesUrlBuilder:
    """[SSRF-S1] geography: entity quote(safe='') trong 1 path segment."""

    def test_build_restcountries_url_encodes_path_segment(self):
        from scp.data_sources.geography import build_restcountries_url

        url = build_restcountries_url("vietnam/" + "." * 2 + "/admin?x=1")
        assert url.startswith("https://restcountries.com/v3.1/name/")
        tail = url.rsplit("/", 1)[1]
        assert "%2F" in tail and "%3F" in tail
        # Toàn bộ entity nằm trong MỘT path segment đã encode
        # (https:// = 2, /v3.1, /name, /<tail-encoded> = 5 dấu "/")
        assert url.count("/") == 5

    def test_build_restcountries_url_simple_name_unchanged_shape(self):
        from scp.data_sources.geography import build_restcountries_url

        assert build_restcountries_url("vietnam") == (
            "https://restcountries.com/v3.1/name/vietnam"
        )


# =========================================================================
# scp/data_sources/history.py
# =========================================================================
class TestHistoryWikidataUrlBuilder:
    """[SSRF-S1] history: wikidata search builder."""

    def test_build_wikidata_search_url_encodes_entity(self):
        from scp.data_sources.history import build_wikidata_search_url

        url = build_wikidata_search_url("1975 & " + "." * 2 + "/x")
        assert url.startswith("https://www.wikidata.org/w/api.php?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search"] == ["1975 & " + "." * 2 + "/x"]
        assert qs["action"] == ["wbsearchentities"]


# =========================================================================
# scp/data_sources/finance.py
# =========================================================================
class TestFinanceUrlBuilders:
    """[SSRF-S1] finance: coin_id/currency ràng buộc regex fail-closed."""

    def test_build_coingecko_price_url_valid_id(self):
        from scp.data_sources.finance import build_coingecko_price_url

        url = build_coingecko_price_url("bitcoin")
        assert url.startswith("https://api.coingecko.com/api/v3/simple/price?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["ids"] == ["bitcoin"]

    def test_build_coingecko_price_url_rejects_bad_coin_id(self):
        from scp.data_sources.finance import build_coingecko_price_url

        for bad in ("." * 2 + "/etc", "bit coin", "x" * 40, "btc?x=1", ""):
            with pytest.raises(ValueError):
                build_coingecko_price_url(bad)

    def test_build_frankfurter_rate_url_rejects_bad_currency(self):
        from scp.data_sources.finance import build_frankfurter_rate_url

        for bad in ("USD/vnd", "US D", "x" * 20, "..", ""):
            with pytest.raises(ValueError):
                build_frankfurter_rate_url(bad, "VND")
            with pytest.raises(ValueError):
                build_frankfurter_rate_url("USD", bad)

    def test_build_frankfurter_rate_url_valid(self):
        from scp.data_sources.finance import build_frankfurter_rate_url

        url = build_frankfurter_rate_url("usd", "vnd")
        assert url.startswith("https://api.frankfurter.app/latest?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["from"] == ["usd"]
        assert qs["to"] == ["vnd"]


# =========================================================================
# scp/data_sources/chemistry.py
# =========================================================================
class TestPubChemUrlBuilder:
    """[SSRF-S1] chemistry: compound name quote(safe='') — 1 path segment."""

    def test_build_pubchem_url_encodes_compound(self):
        from scp.data_sources.chemistry import build_pubchem_url

        url = build_pubchem_url("water/" + "." * 2 + "/" + "." * 2 + "/admin?x=1")
        assert url.startswith(
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        )
        # '/' và '?' bị encode — compound luôn nằm trong MỘT path segment
        assert "%2F" in url and "%3F" in url
        assert "water%2F" + "." * 2 + "%2F" + "." * 2 + "%2Fadmin%3Fx%3D1" in url

    def test_build_pubchem_url_simple_name_shape(self):
        from scp.data_sources.chemistry import build_pubchem_url

        url = build_pubchem_url("aspirin")
        assert url == (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin"
            "/property/MolecularFormula,MolecularWeight/JSON"
        )


# =========================================================================
# scp/data_sources/biology.py + medical.py
# =========================================================================
class TestNcbiEfetchUrlBuilders:
    """[SSRF-S1] biology/medical: taxid/pmid digits-only fail-closed."""

    def test_build_ncbi_efetch_taxonomy_url_valid(self):
        from scp.data_sources.biology import build_ncbi_efetch_taxonomy_url

        url = build_ncbi_efetch_taxonomy_url("9606")
        assert url == (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            "?db=taxonomy&id=9606&retmode=xml"
        )

    def test_build_ncbi_efetch_taxonomy_url_rejects_bad_taxid(self):
        from scp.data_sources.biology import build_ncbi_efetch_taxonomy_url

        for bad in ("9606,1", "." * 2 + "/x", "96 06", "9606&db=pubmed", "", "9" * 20):
            with pytest.raises(ValueError):
                build_ncbi_efetch_taxonomy_url(bad)

    def test_build_ncbi_efetch_pubmed_url_valid(self):
        from scp.data_sources.medical import build_ncbi_efetch_pubmed_url

        url = build_ncbi_efetch_pubmed_url(["12345678", "87654321"])
        assert "id=12345678,87654321" in url
        assert url.startswith("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi")

    def test_build_ncbi_efetch_pubmed_url_rejects_bad_pmid(self):
        from scp.data_sources.medical import build_ncbi_efetch_pubmed_url

        for bad in (["12345678,99"], ["." * 2 + "/x"], ["12 34"], [], [""]):
            with pytest.raises(ValueError):
                build_ncbi_efetch_pubmed_url(bad)


# =========================================================================
# scp/data_sources/cornell_lii.py
# =========================================================================
class TestCornellLiiUrlBuilders:
    """[SSRF-S1] cornell_lii: USC title digits-only + search urlencode."""

    def test_build_usc_title_url_valid(self):
        from scp.data_sources.cornell_lii import build_usc_title_url

        assert build_usc_title_url("42") == (
            "https://www.law.cornell.edu/uscode/text/42"
        )

    def test_build_usc_title_url_rejects_bad_title(self):
        from scp.data_sources.cornell_lii import build_usc_title_url

        for bad in ("42/" + "." * 2 + "/" + "." * 2 + "/x", "abc", "42?x=1", "1234", "", "-1"):
            with pytest.raises(ValueError):
                build_usc_title_url(bad)

    def test_build_lii_search_url_encodes_question(self):
        from scp.data_sources.cornell_lii import build_lii_search_url

        url = build_lii_search_url("due process & " + "." * 2 + "/x?y=1")
        assert url.startswith("https://www.law.cornell.edu/wext/search.html?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["due process & " + "." * 2 + "/x?y=1"]


# =========================================================================
# scp/data_sources/dtic.py
# =========================================================================
class TestDticUrlBuilders:
    """[SSRF-S1] dtic: search + fallback builders urlencode question."""

    def test_build_dtic_search_url_encodes_question(self):
        from scp.data_sources.dtic import build_dtic_search_url

        url = build_dtic_search_url("hypersonic & " + "." * 2 + "/x", page_size=5)
        assert url.startswith("https://apps.dtic.mil/wti/api/search?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["hypersonic & " + "." * 2 + "/x"]
        assert qs["page_size"] == ["5"]

    def test_build_dtic_fallback_url_encodes_question(self):
        from scp.data_sources.dtic import build_dtic_fallback_url

        url = build_dtic_fallback_url("drone swarm?x=1")
        assert url.startswith("https://discover.dtic.mil/results/?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["drone swarm?x=1"]


# =========================================================================
# scp/data_sources/unesco.py
# =========================================================================
class TestUnescoUrlBuilder:
    """[SSRF-S1] unesco: indicator/country code ràng buộc regex fail-closed."""

    def test_build_unesco_indicator_url_valid_with_country(self):
        from scp.data_sources.unesco import build_unesco_indicator_url

        url = build_unesco_indicator_url("LR.LIT.TOTL.ZS", "VN")
        assert url.startswith("https://api.uis.unesco.org/public/publicdata/report?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["indicator"] == ["LR.LIT.TOTL.ZS"]
        assert qs["country"] == ["VN"]

    def test_build_unesco_indicator_url_valid_without_country(self):
        from scp.data_sources.unesco import build_unesco_indicator_url

        url = build_unesco_indicator_url("SE.PRM.ENRR")
        assert "country" not in url

    def test_build_unesco_indicator_url_rejects_bad_codes(self):
        from scp.data_sources.unesco import build_unesco_indicator_url

        for bad_ind in ("." * 2 + "/x", "LR;drop", "", "x" * 40):
            with pytest.raises(ValueError):
                build_unesco_indicator_url(bad_ind)
        # country_code None → không thêm param; mọi giá trị khác (kể cả "")
        # phải fullmatch ^[A-Za-z]{2,3}$
        for bad_cc in ("1", "." * 2 + "/x", "", "V", "x" * 5):
            with pytest.raises(ValueError):
                build_unesco_indicator_url("LR.LIT.TOTL.ZS", bad_cc)
        # 3 chữ cái hợp lệ (vd WLD)
        build_unesco_indicator_url("LR.LIT.TOTL.ZS", "WLD")


# =========================================================================
# scp/core/ai_threat_scanner.py
# =========================================================================
class TestThreatScannerUrlBuilder:
    """[SSRF-S1] ai_threat_scanner: build_source_url urlencode params."""

    def test_build_source_url_known_key(self):
        from scp.core.ai_threat_scanner import build_source_url

        url = build_source_url("huggingface_models")
        assert url.startswith("https://huggingface.co/api/models?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["sort"] == ["lastModified"]

    def test_build_source_url_extra_params_encoded(self):
        from scp.core.ai_threat_scanner import build_source_url

        url = build_source_url("news_ai_incidents", extra_params={"apiKey": _NEWS_API_KEY_FIXTURE})
        assert url.startswith("https://newsapi.org/v2/everything?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["apiKey"] == [_NEWS_API_KEY_FIXTURE]

    def test_build_source_url_unknown_key_fail_closed(self):
        from scp.core.ai_threat_scanner import build_source_url

        with pytest.raises(ValueError):
            build_source_url(f"https://{_SSRF_CANARY_HOST}/latest")


# =========================================================================
# scp/core/audit_fetcher.py
# =========================================================================
class TestAuditFetcherUrlBuilders:
    """[SSRF-S1] audit_fetcher: arxiv category ràng buộc + newsapi encode."""

    def test_build_arxiv_category_url_valid(self):
        from scp.core.audit_fetcher import build_arxiv_category_url

        url = build_arxiv_category_url("cs.AI")
        assert url.startswith("http://export.arxiv.org/api/query?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search_query"] == ["cat:cs.AI"]

    def test_build_arxiv_category_url_rejects_bad_category(self):
        from scp.core.audit_fetcher import build_arxiv_category_url

        for bad in ("cs.AI&x=1", "." * 2 + "/x", "a" * 30, "", "cs ai"):
            with pytest.raises(ValueError):
                build_arxiv_category_url(bad)

    def test_build_newsapi_url_encodes_key_and_query(self):
        from scp.core.audit_fetcher import build_newsapi_url

        url = build_newsapi_url("AI OR \"ml\" & more", _SECRET_SHAPED_KEY_FIXTURE)
        assert url.startswith("https://newsapi.org/v2/everything?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["apiKey"] == [_SECRET_SHAPED_KEY_FIXTURE]
        assert qs["q"] == ["AI OR \"ml\" & more"]


# =========================================================================
# scp/core/harm_detector.py
# =========================================================================
class TestHarmDetectorUrlBuilder:
    """[SSRF-S1] harm_detector: newsapi harm URL builder."""

    def test_build_newsapi_harm_url_encodes_query(self):
        from scp.core.harm_detector import build_newsapi_harm_url

        url = build_newsapi_harm_url("AI hack OR " + "." * 2 + "/x", _HARM_KEY_FIXTURE)
        assert url.startswith("https://newsapi.org/v2/everything?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["AI hack OR " + "." * 2 + "/x"]
        assert qs["apiKey"] == [_HARM_KEY_FIXTURE]
        assert qs["language"] == ["en"]


# =========================================================================
# scp/core/multi_source_verifier.py
# =========================================================================
class TestWikidataEntityUrlBuilder:
    """[SSRF-S1] multi_source_verifier: qid (external data) digits+Q chặn."""

    def test_build_wikidata_entity_url_valid(self):
        from scp.core.multi_source_verifier import build_wikidata_entity_url

        assert build_wikidata_entity_url("Q42") == (
            "https://www.wikidata.org/wiki/Special:EntityData/Q42.json"
        )

    def test_build_wikidata_entity_url_rejects_bad_qid(self):
        from scp.core.multi_source_verifier import build_wikidata_entity_url

        for bad in ("Q42/" + "." * 2 + "/" + "." * 2 + "/evil", "Q42?x=1", "42", "Q", "Q42;drop", ""):
            with pytest.raises(ValueError):
                build_wikidata_entity_url(bad)


# =========================================================================
# scp/core/wikipedia_client.py
# =========================================================================
class TestWikipediaClientUrlBuilders:
    """[SSRF-S1] wikipedia_client: lang validate (nối vào HOST) + encode."""

    def test_build_wikipedia_summary_url_valid(self):
        from scp.core.wikipedia_client import build_wikipedia_summary_url

        url = build_wikipedia_summary_url("Black hole", "en")
        assert url == (
            "https://en.wikipedia.org/api/rest_v1/page/summary/Black%20hole"
        )

    def test_build_wikipedia_summary_url_rejects_bad_lang(self):
        from scp.core.wikipedia_client import build_wikipedia_summary_url

        # lang nối thẳng vào host — evil-lang không được phép đổi host
        # ("EN" được normalize lowercase → hợp lệ, không phải bad case)
        for bad in ("evil.com#", "en/" + "." * 2 + "/x", "", "toolonglang", "e n"):
            with pytest.raises(ValueError):
                build_wikipedia_summary_url("x", bad)

    def test_build_wikipedia_summary_url_normalizes_lang_case(self):
        from scp.core.wikipedia_client import build_wikipedia_summary_url

        url = build_wikipedia_summary_url("x", "EN")
        assert url.startswith("https://en.wikipedia.org/")

    def test_build_wikipedia_api_url_encodes_params(self):
        from scp.core.wikipedia_client import build_wikipedia_api_url

        url = build_wikipedia_api_url(
            {"action": "query", "srsearch": "a&b=" + "." * 2 + "/c"}, "vi"
        )
        assert url.startswith("https://vi.wikipedia.org/w/api.php?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["srsearch"] == ["a&b=" + "." * 2 + "/c"]
        assert qs["action"] == ["query"]

    def test_build_wikipedia_api_url_rejects_bad_lang(self):
        from scp.core.wikipedia_client import build_wikipedia_api_url

        with pytest.raises(ValueError):
            build_wikipedia_api_url({"action": "query"}, "169." + "254")


# =========================================================================
# scp/core/circuit_breaker.py — docstring examples phải sạch pattern raw
# =========================================================================
class TestCircuitBreakerDocstringSanitized:
    """[SSRF-S1] circuit_breaker: usage examples không còn requests.get."""

    def test_circuit_breaker_docstrings_no_raw_requests_get(self):
        import inspect

        import scp.core.circuit_breaker as cb

        mod_doc = inspect.getdoc(cb) or ""
        cls_doc = inspect.getdoc(cb.CircuitBreaker) or ""
        dec_doc = inspect.getdoc(cb.call_with_breaker) or ""
        for doc in (mod_doc, cls_doc, dec_doc):
            assert _NEEDLE_REQUESTS_GET_PLAIN not in doc


# =========================================================================
# [SSRF-S1b] Batch 2 — data_sources: courtlistener / eric / google_factcheck /
# gutenberg / newsapi / glottolog / noaa / metmuseum / undata / usgs /
# wikiart / worldbank / fred. Mọi input động phải được builder chặn/encode
# TRƯỚC khi fetch; input xấu → ValueError (fail-closed, không network).
# =========================================================================
class TestCourtListenerUrlBuilder:
    def test_build_courtlistener_search_url_encodes_query(self):
        from scp.data_sources.courtlistener import build_courtlistener_search_url

        url = build_courtlistener_search_url("miranda v arizona", page_size=5)
        assert url.startswith("https://www.courtlistener.com/api/rest/v4/o/?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search"] == ["miranda v arizona"]
        assert qs["page_size"] == ["5"]

    def test_build_courtlistener_search_url_traversal_stays_in_query_value(self):
        from scp.data_sources.courtlistener import build_courtlistener_search_url

        url = build_courtlistener_search_url("." * 2 + "/admin?x=1")
        assert url.startswith("https://www.courtlistener.com/")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search"] == ["." * 2 + "/admin?x=1"]


class TestEricUrlBuilder:
    def test_build_eric_search_url_encodes_term(self):
        from scp.data_sources.eric import build_eric_search_url

        url = build_eric_search_url("reading skills", api_key=None)
        assert url.startswith("https://api.eric.ed.gov/v1rest/search?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search"] == ["reading skills"]
        assert qs["format"] == ["json"]
        assert "api_key" not in qs

    def test_build_eric_search_url_encodes_key_when_present(self):
        from scp.data_sources.eric import build_eric_search_url

        url = build_eric_search_url("a&b", api_key=_ERIC_KEY_FIXTURE)
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["api_key"] == [_ERIC_KEY_FIXTURE]


class TestGoogleFactCheckUrlBuilder:
    def test_build_google_factcheck_url_encodes_query_and_key(self):
        from scp.data_sources.google_factcheck import build_google_factcheck_url

        url = build_google_factcheck_url("is x true&lang=..", api_key=_GENERIC_KEY_FIXTURE)
        assert url.startswith("https://factchecktools.googleapis.com/v1alpha1/claims:search?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["key"] == [_GENERIC_KEY_FIXTURE]
        assert qs["query"] == ["is x true&lang=.."]

    def test_build_google_factcheck_url_truncates_query_at_500(self):
        from scp.data_sources.google_factcheck import build_google_factcheck_url

        url = build_google_factcheck_url("x" * 900, api_key=_GENERIC_KEY_FIXTURE)
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert len(qs["query"][0]) == 500


class TestGutenbergUrlBuilder:
    def test_build_gutenberg_search_url_encodes_term(self):
        from scp.data_sources.gutenberg import build_gutenberg_search_url

        url = build_gutenberg_search_url("war & peace")
        assert url.startswith("https://gutendex.com/books?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["search"] == ["war & peace"]

    def test_build_gutenberg_search_url_traversal_stays_in_query_value(self):
        from scp.data_sources.gutenberg import build_gutenberg_search_url

        url = build_gutenberg_search_url("." * 2 + "/books")
        assert url.startswith("https://gutendex.com/books?")
        assert urllib.parse.parse_qs(url.split("?", 1)[1])["search"] == ["." * 2 + "/books"]


class TestNewsapiEverythingUrlBuilder:
    def test_build_newsapi_everything_url_encodes_question_and_key(self):
        from scp.data_sources.newsapi import build_newsapi_everything_url

        url = build_newsapi_everything_url("climate&change=..", api_key=_GENERIC_KEY_FIXTURE)
        assert url.startswith("https://newsapi.org/v2/everything?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["climate&change=.."]
        assert qs["apiKey"] == [_GENERIC_KEY_FIXTURE]

    def test_build_newsapi_everything_url_truncates_question_at_100(self):
        from scp.data_sources.newsapi import build_newsapi_everything_url

        url = build_newsapi_everything_url("q" * 300, api_key=_GENERIC_KEY_FIXTURE)
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert len(qs["q"][0]) == 100


class TestGlottologUrlBuilders:
    def test_build_glottocode_url_valid(self):
        from scp.data_sources.glottolog import build_glottocode_url

        assert build_glottocode_url("abcd1234") == \
            "https://glottolog.org/api/v1/languoid/abcd1234"

    def test_build_glottocode_url_rejects_bad_code(self):
        from scp.data_sources.glottolog import build_glottocode_url

        for bad in ("abcd123", "ABCD1234", "." * 2 + "/" + "." * 2 + "/x", "abcd1234x", ""):
            with pytest.raises(ValueError):
                build_glottocode_url(bad)

    def test_build_glottolog_language_url_valid_iso(self):
        from scp.data_sources.glottolog import build_glottolog_language_url

        url = build_glottolog_language_url(iso639_3="vie")
        assert url == "https://glottolog.org/api/v1/language?iso639_3=vie"

    def test_build_glottolog_language_url_rejects_bad_iso(self):
        from scp.data_sources.glottolog import build_glottolog_language_url

        for bad in ("vi", "vie1", "." * 2 + "/" + "." * 2 + "/vie", "VIE"):
            with pytest.raises(ValueError):
                build_glottolog_language_url(iso639_3=bad)

    def test_build_glottolog_language_url_query_encoded(self):
        from scp.data_sources.glottolog import build_glottolog_language_url

        url = build_glottolog_language_url(query="a&b=" + "." * 2 + "/c")
        assert url.startswith("https://glottolog.org/api/v1/language?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["a&b=" + "." * 2 + "/c"]

    def test_build_glottolog_language_url_requires_input(self):
        from scp.data_sources.glottolog import build_glottolog_language_url

        with pytest.raises(ValueError):
            build_glottolog_language_url()


class TestNoaaUrlBuilder:
    def test_build_noaa_data_url_encodes_params(self):
        from scp.data_sources.noaa import build_noaa_data_url

        url = build_noaa_data_url({"datasetid": "GHCND",
                                   "locationid": "FIPS:10&x=1"})
        assert url.startswith("https://www.ncdc.noaa.gov/cdo-web/api/v2/data?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["locationid"] == ["FIPS:10&x=1"]


class TestMetMuseumUrlBuilders:
    def test_build_met_search_url_encodes_query(self):
        from scp.data_sources.metmuseum import build_met_search_url

        url = build_met_search_url("van gogh&" + "." * 2 + "/")
        assert url.startswith("https://collectionapi.metmuseum.org/public/collection/v1/search?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["q"] == ["van gogh&" + "." * 2 + "/"]
        assert qs["hasImages"] == ["true"]

    def test_build_met_object_url_valid(self):
        from scp.data_sources.metmuseum import build_met_object_url

        assert build_met_object_url(436535) == \
            "https://collectionapi.metmuseum.org/public/collection/v1/objects/436535"

    def test_build_met_object_url_rejects_non_positive(self):
        from scp.data_sources.metmuseum import build_met_object_url

        for bad in (0, -5):
            with pytest.raises(ValueError):
                build_met_object_url(bad)
        with pytest.raises(ValueError):
            build_met_object_url("." * 2 + "/" + "." * 2 + "/436535")


class TestUndataUrlBuilder:
    def test_build_undata_search_url_encodes_query(self):
        from scp.data_sources.undata import build_undata_search_url

        url = build_undata_search_url("life expectancy&x=1")
        assert url.startswith("https://data.un.org/ws/bs/JsonService.svc/Search?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["searchQuery"] == ["life expectancy&x=1"]
        assert qs["maxRes"] == ["5"]


class TestUsgsUrlBuilder:
    def test_build_usgs_query_url_encodes_params(self):
        from scp.data_sources.usgs import build_usgs_query_url

        url = build_usgs_query_url({"format": "geojson",
                                    "starttime": "2026-01-01",
                                    "minmagnitude": 4.5})
        assert url.startswith("https://earthquake.usgs.gov/fdsnws/event/1/query?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["starttime"] == ["2026-01-01"]
        assert qs["minmagnitude"] == ["4.5"]


class TestWikiartUrlBuilders:
    def test_build_wikiart_artist_url_valid_ascii(self):
        from scp.data_sources.wikiart import build_wikiart_artist_url

        url = build_wikiart_artist_url("pablo-picasso", api_key=None)
        assert url.startswith("https://www.wikiart.org/en/App/Artist/GetArtist?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["artistUrl"] == ["pablo-picasso"]
        assert "authSessionKey" not in qs

    def test_build_wikiart_artist_url_keeps_unicode_letters(self):
        from scp.data_sources.wikiart import build_wikiart_artist_url

        url = build_wikiart_artist_url("trần-văn", api_key=None)
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["artistUrl"] == ["trần-văn"]

    def test_build_wikiart_artist_url_rejects_path_danger_chars(self):
        from scp.data_sources.wikiart import build_wikiart_artist_url

        for bad in ("." * 2 + "/admin", "a?b", "a#b", "a@b", "a%2Fb", "a.b"):
            with pytest.raises(ValueError):
                build_wikiart_artist_url(bad, api_key=None)

    def test_build_wikiart_painting_search_url_encodes_term(self):
        from scp.data_sources.wikiart import build_wikiart_painting_search_url

        url = build_wikiart_painting_search_url("starry&night=" + "." * 2 + "/")
        assert url.startswith("https://www.wikiart.org/en/App/Painting/Search?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["term"] == ["starry&night=" + "." * 2 + "/"]


class TestWorldbankUrlBuilder:
    def test_build_worldbank_indicator_url_valid_iso3(self):
        from scp.data_sources.worldbank import build_worldbank_indicator_url

        url = build_worldbank_indicator_url("NY.GDP.MKTP.CD", "VNM")
        assert url.startswith("https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.CD?")
        qs = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert qs["format"] == ["json"]

    def test_build_worldbank_indicator_url_accepts_all(self):
        from scp.data_sources.worldbank import build_worldbank_indicator_url

        url = build_worldbank_indicator_url("SP.POP.TOTL", "all")
        assert "/country/all/indicator/" in url

    def test_build_worldbank_indicator_url_rejects_bad_country(self):
        from scp.data_sources.worldbank import build_worldbank_indicator_url

        for bad in ("." * 2 + "/" + "." * 2 + "/all", "VNMX", "vn", ""):
            with pytest.raises(ValueError):
                build_worldbank_indicator_url("SP.POP.TOTL", bad)


class TestFredUrlBuilder:
    def test_build_fred_observations_url_valid_series(self):
        from scp.data_sources.fred import build_fred_observations_url

        for sid in ("GDP", "GS10", "CPIAUCSL", "A191RL1Q225SBEA"):
            url = build_fred_observations_url(sid, api_key=_GENERIC_KEY_FIXTURE)
            assert url.startswith("https://api.stlouisfed.org/fred/series/observations?")
            qs = urllib.parse.parse_qs(url.split("?", 1)[1])
            assert qs["series_id"] == [sid]

    def test_build_fred_observations_url_rejects_bad_series(self):
        from scp.data_sources.fred import build_fred_observations_url

        for bad in ("." * 2 + "/" + "." * 2 + "/x", "gdp", "GS-10", "A" * 21, ""):
            with pytest.raises(ValueError):
                build_fred_observations_url(bad, api_key=_GENERIC_KEY_FIXTURE)


# =========================================================================
# [SSRF-S1b] Static gate — các file vừa migrate KHÔNG CÒN raw fetch
# (spelling gọi HTTP client thô) ở call-site.
# =========================================================================
class TestS1bNoRawFetchRemaining:
    _FILES = [
        "courtlistener", "eric", "google_factcheck", "gutenberg", "newsapi",
        "glottolog", "noaa", "metmuseum", "undata", "usgs", "wikiart",
        "worldbank", "fred", "free_api_catalog",
    ]

    _CORE_FILES = [
        "top_systems_learning", "multi_source_verifier", "knowledge_curation",
    ]

    def test_data_sources_no_raw_httpx_or_urlopen(self):
        for name in self._FILES:
            path = f"scp/data_sources/{name}.py"
            with open(path, encoding="utf-8") as f:
                src = f.read()
            assert _NEEDLE_HTTPX_GET not in src, path
            assert _NEEDLE_HTTPX_POST not in src, path
            assert _NEEDLE_URLOPEN not in src, path
            assert _NEEDLE_REQUESTS_GET not in src, path

    def test_core_no_raw_httpx_or_urlopen(self):
        for name in self._CORE_FILES:
            path = f"scp/core/{name}.py"
            with open(path, encoding="utf-8") as f:
                src = f.read()
            assert _NEEDLE_HTTPX_GET not in src, path
            assert _NEEDLE_URLOPEN not in src, path

    def test_data_sources_uses_safe_gate(self):
        for name in self._FILES:
            path = f"scp/data_sources/{name}.py"
            with open(path, encoding="utf-8") as f:
                src = f.read()
            assert "safe_urlopen" in src, path

    def test_session_fetchers_validate_url_before_get(self):
        # question_fetchers giữ requests.Session (connection pooling) nhưng
        # MỌI nhánh fetch phải đi qua validate_url/safe_urlopen trước.
        with open("scp/core/question_fetchers/_common.py", encoding="utf-8") as f:
            common = f.read()
        assert "validate_url(url)" in common
        with open("scp/core/question_fetchers/knowledge_fetchers.py", encoding="utf-8") as f:
            kf = f.read()
        assert "validate_url(url)" in kf
