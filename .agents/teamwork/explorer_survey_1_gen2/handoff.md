# Handoff Report — Survey Track 1: Domain Data Fork & Question Router Integration

- **Role**: Explorer (Codebase & Architecture Investigator — Gen 2 Replacement)
- **Working Directory**: `D:\scp\.agents\teamwork\explorer_survey_1_gen2`
- **Parent**: orchestrator_4 (`d48c23a1-aa94-4967-ac9a-ed40fa3f5fff`)
- **Status**: Complete (Read-Only Investigation)
- **Target Requirement**: Requirement 1 from `ORIGINAL_REQUEST.md`:
  *"Hoàn tất kết nối dữ liệu chuyên ngành vào scp/runtime/domain_data_fork.py và scp/runtime/question_router.py (USGS Earthquake, Biology, Geology, ConfigLoader cho các API cần key)."*

---

## 1. Observation

### Observation 1.1: `scp/runtime/domain_data_fork.py` Current Implementation & Gaps
- File path: `D:\scp\scp\runtime\domain_data_fork.py` (431 lines).
- Lines 1-14 state its objective:
  ```python
  """[DomainDataFork] Unified Local Data Source Resolver for SCP Question Router.
  Kết nối toàn bộ các nguồn dữ liệu khoa học / thực tế cục bộ (Offline Local Sources)
  trong `scp/data_sources/` vào luồng Lookup Fork của QuestionRouter:
    - AstronomyDataSource: hành tinh, sao, thiên hà, hằng số thiên văn (NASA/IAU).
    - ChemistryDataSource: nguyên tố, hợp chất, phân tử khối, hóa trị (IUPAC).
    - PhysicsDataSource: hằng số vật lý (tốc độ ánh sáng, Planck, gia tốc trọng trường...).
    - GeographyDataSource: thủ đô, dân số, diện tích, quốc gia.
    - MathDataSource: hằng số toán học (pi, e, phi, căn bậc hai...).
  ```
- **Registered Singletons** (lines 23-69):
  `_astronomy_source`, `_chemistry_source`, `_physics_source`, `_geography_source`, `_math_source`, `_usgs_source`.
- **Existing resolvers**:
  - `_resolve_astronomy` (lines 88-140): Planets (Mercury to Neptune, Sun, Moon; moons, mass, radius, orbit period), universe age (13.8B years), Hubble constant (67.4 km/s/Mpc).
  - `_resolve_chemistry` (lines 178-218): Molar mass of compounds (H2O, CO2, H2SO4, HCl, NaCl, C6H12O6, CH4, C2H5OH, NaOH, CaCO3, NH3); chemical elements atomic number and mass (Fe, Cu, Au, Ag, Al, Na, Ca, K, Cl, He, C, N, O, H).
  - `_resolve_physics` (lines 239-253): Physical constants (c, h, N_A, G, g, e).
  - `_resolve_geography` (lines 296-312): Capitals table (34 countries).
  - `_resolve_math` (lines 327-341): Pi, e, golden ratio.
  - `_resolve_usgs` (lines 357-377):
    ```python
    def _resolve_usgs(question_lower: str) -> dict[str, Any] | None:
        if not any(k in question_lower for k in ["động đất", "earthquake", "địa chấn", "richter"]):
            return None
        try:
            usgs = _get_usgs()
            data = usgs.query(question_lower)
            if data and "metadata" in data:
                meta = data["metadata"]
                mag = meta.get("magnitude")
                place = meta.get("place")
                text = f"Sự kiện động đất ghi nhận gần đây bởi USGS: Độ lớn M{mag} tại {place}."
                return {
                    "text": text,
                    "api_name": "USGSDataSource (USGS Hazards API)",
                    "api_url": "https://earthquake.usgs.gov/fdsnws/event/1/query",
                    "evidence": text,
                }
        except Exception as exc:
            logger.debug("[domain_fork] usgs lookup error: %s", exc, exc_info=True)
        return None
    ```
- **Verbatim defects observed in `_resolve_usgs`**:
  1. In `scp/data_sources/usgs.py:200-214`, `_query_recent` returns metadata with keys `{"time_window_days", "result_count", "top_events"}`. It does NOT have top-level `magnitude` or `place`! Therefore, when a user asks about recent earthquakes ("động đất gần đây"), `meta.get("magnitude")` and `meta.get("place")` evaluate to `None`, producing the mangled answer string:
     `"Sự kiện động đất ghi nhận gần đây bởi USGS: Độ lớn MNone tại None."`
  2. `usgs.py` makes external network calls via `safe_urlopen(req, timeout=10)` (lines 147, 195) WITHOUT specifying `extra_allowed_hosts=frozenset({"earthquake.usgs.gov"})`. If `SCP_EGRESS_MODE=deny` or `allowlist` (without `earthquake.usgs.gov`), `safe_urlopen` raises `EgressDeniedError`, returning `None`.
- **Missing Domain Handlers in `domain_data_fork.py`**:
  - `BiologyDataSource` is NOT imported and NOT resolved anywhere in `domain_data_fork.py`.
  - `GeologyDataSource` is NOT imported and NOT resolved anywhere in `domain_data_fork.py`.
  - Master dispatcher `resolve_domain_data_lookup(question)` (lines 382-429) dispatches only: USGS (1), Astronomy (2), Chemistry (3), Physics (4), Geography (5), Math (6).

---

### Observation 1.2: `scp/runtime/question_router.py` Current Routing Architecture
- File path: `D:\scp\scp\runtime\question_router.py` (1,283 lines).
- **L0 Classifier `classify_l0`** (lines 352-484):
  - Step 1: Security patterns (`_SECURITY_RULES`, `UnifiedPatternDetector`) -> `LANE_SECURITY`.
  - Step 2: `_REASONING_STRONG_RULES` (arithmetic, code, conversational identity/greeting/assist) -> `REASONING` / `LANE_CHATBOT` with `bypass_verdict_pass=True`.
  - Step 3: `_PH_PATTERN` (case-sensitive) -> `LOOKUP` / `LANE_FACTUAL` (`chemistry`).
  - Step 4: `_LOOKUP_RULES` (lines 234-265):
    - Current tags: `weather_fact`, `finance_fact`, `interrogative_vi`, `geography_fact`, `security_fact`, `chemistry_fact`, `physics_fact`, `definition`, `unit_conversion`.
    - **Missing domain fact tags**: `biology_fact`, `geology_fact`, `earthquake_fact`.
    - Note on priority: `weather_fact` and `finance_fact` were explicitly moved before `interrogative_vi` (W11-f1) so that questions like "Thời tiết Hà Nội thế nào?" are tagged `weather_fact` instead of being swallowed by `interrogative_vi` ("thế nào").
  - Step 5: `_CREATIVE_RULES` -> `REASONING`.
  - Step 6: `_REASONING_WEAK_RULES` -> `REASONING`.
  - Step 7: Domain hint fallback: `domain = _sanitize_domain_hint(text, _domain_hint(text))`. If `domain != "general"`, returns `LOOKUP` with confidence 0.7.
- **`_KNOWLEDGE_DOMAINS`** (lines 763-768):
  ```python
  _KNOWLEDGE_DOMAINS = frozenset(
      {
          "geography", "history", "biology", "chemistry", "physics",
          "astronomy", "medical", "technology", "general",
      }
  )
  ```
  - Note: `"geology"` is missing from `_KNOWLEDGE_DOMAINS`.
- **Domain Hint Subsystems**:
  - `_domain_hint(question)` calls `scp.core.partition.shard.detect_domain(question)`.
    In `scp/core/partition/shard.py:54-73`, `DOMAIN_KEYWORDS` contains `math`, `geography`, `chemistry`, `physics`, `biology`, `history`.
    `geology` is missing from `shard.py`!
  - If `detect_domain` returns "general", `_domain_hint` falls back to `scp.data_sources.domain_classifier.classify_top1(question)`.
    In `scp/data_sources/domain_classifier.py:225`, `'geology'` IS present:
    `'geology': ['địa chất', 'geology', 'khoáng sản', 'mineral', 'động đất', 'earthquake']`.
- **Lookup Fork Flow `resolve_lookup_data`** (lines 1073-1133):
  - Tier 1: Local `ConversionDataSource` (`_conversion_lookup`).
  - Tier 2: Remote `WeatherDataSource` (`_weather_lookup` -> Open-Meteo with scoped egress grant).
  - Tier 3: Local `resolve_domain_data_lookup` from `scp.runtime.domain_data_fork.py` (lines 1105-1111).
  - Tier 4: `_catalog_candidates` / `_generic_entry_lookup` (FreeAPICatalog).
  - Tier 5: `_wiki_lookup` for domains in `_KNOWLEDGE_DOMAINS`.
  - Fallback: returns `None` -> caller (`AskKernelAdapter.run_rag`) routes to LLM generation.

---

### Observation 1.3: `scp/data_sources/` Inventory for Target Disciplines
1. **USGS Earthquake (`scp/data_sources/usgs.py`, 218 lines)**:
   - Class `USGSDataSource(IDataSource)` (priority=11, ttl=1800).
   - Free API, no API key required.
   - Endpoint: `https://earthquake.usgs.gov/fdsnws/event/1/query`.
   - Methods: `query(question)`, `_query_min_magnitude(min_mag)`, `_query_recent(days=7)`.
   - `health_check()` uses `shared_health_ping` with `reachability_ping('https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1')`.
   - Egress gap: does not declare `USGS_EGRESS_HOST = "earthquake.usgs.gov"` or forward `extra_allowed_hosts` to `safe_urlopen`.

2. **Biology (`scp/data_sources/biology.py`, 301 lines)**:
   - Class `BiologyDataSource(IDataSource)` (priority=5, ttl=86400).
   - **Local knowledge base**:
     - `_genetic_code`: 16 codons mapped to amino acids (TTT -> Phe, ATG -> Met, CTT -> Leu, ATT -> Ile, GTT -> Val, etc.).
     - `_amino_acids`: 20 amino acids (Ala -> Alanine, Arg -> Arginine, Trp -> Tryptophan, etc.).
     - `_cells`: Organelles (mitochondria, ribosome, nucleus, lysosome, chloroplast) with sizes and functions.
     - `_constants`: Biological constants (human genome size 3.2e9, human chromosomes 46, average gene size 2700, transcription rate 30, translation rate 15).
   - **Remote NCBI Taxonomy**:
     - `_fetch_from_ncbi_taxonomy`: Queries NCBI E-utilities (`esearch.fcgi` for taxid -> `efetch.fcgi` for XML taxonomy details).
     - Key loading: line 60 uses raw `os.environ.get("NCBI_API_KEY", "").strip() or os.environ.get("PUBMED_API_KEY", "").strip()`.
   - **Registration gap**: In `scp/data_sources/__init__.py:50`, `BiologyDataSource` is imported, but in `register_all_sources()` (lines 143-212), `BiologyDataSource()` is NOT instantiated in the `sources` list!

3. **Geology (`scp/data_sources/geology.py`, 141 lines)**:
   - Class `GeologyDataSource(IDataSource)` (priority=5, ttl=86400).
   - **Local knowledge base**:
     - `_minerals`: diamond ("Hardness 10 Mohs, carbon"), gold ("Soft, malleable, Au"), iron ("Most common metal on Earth"), quartz ("Most abundant mineral"), feldspar ("60% of Earth's crust").
   - **Remote USGS duplicate**:
     - Lines 89-140: `_fetch_from_usgs` uses `fetch_with_retry` to call `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=5&orderby=time`. This duplicates `USGSDataSource`.

---

### Observation 1.4: ConfigLoader & Key Handling (`scp/data_sources/config_loader.py`, 252 lines)
- Fully implemented class `DataSourceConfigLoader`:
  - Mapping: `COMMERCIAL_SOURCE_KEYS` maps 20 source names to env vars:
    `"alphavantage": "ALPHAVANTAGE_API_KEY"`, `"fred": "FRED_API_KEY"`, `"newsapi": "NEWSAPI_API_KEY"`, `"google_factcheck": "GOOGLE_FACT_CHECK_API_KEY"`, `"courtlistener": "COURTLISTENER_TOKEN"`, `"usda": "USDA_API_KEY"`, `"agriculture": "USDA_API_KEY"`, `"ncbi": "NCBI_API_KEY"`, `"pubmed": "PUBMED_API_KEY"`, `"biology": "NCBI_API_KEY"`, `"medical": "PUBMED_API_KEY"`, `"nvd": "NVD_API_KEY"`, `"cybersecurity": "NVD_API_KEY"`, `"eia": "EIA_API_KEY"`, `"energy": "EIA_API_KEY"`, `"eric": "ERIC_API_KEY"`, `"caselaw": "CASE_LAW_API_KEY"`, `"legal": "CASE_LAW_API_KEY"`, `"noaa": "NOAA_API_KEY"`, `"wikiart": "WIKIART_API_KEY"`.
  - Placeholder rejection: `INVALID_PLACEHOLDERS` sets `{"demo", "placeholder", "changeme", "todo", "none", "null", "your_api_key_here", "dummy", "test_key", ...}`.
  - Fail-closed behavior: `MissingApiKeyError` raised when `required=True` and key is missing or is an invalid placeholder.
  - Secret protection: `mask_secret(secret)` returns e.g. `"abc...56"`, preventing leaks in logs.
  - Pure parsing: `parse_env_file` parses `.env` without third-party dependencies.
  - Public interface: `get_api_key(source_name, required=True)`, `require_api_key(source_name)`, `has_api_key(source_name)`.
- **Wiring gap observed across `scp/data_sources/`**:
  `grep_search` across `scp/data_sources/` revealed that 14 modules still call raw `os.environ.get()` instead of `config_loader`:
  - `biology.py:60`: `os.environ.get("NCBI_API_KEY")`
  - `medical.py:80`: `os.environ.get("PUBMED_API_KEY")`
  - `agriculture.py:30`: `os.environ.get("USDA_API_KEY")`
  - `alphavantage.py:39`: `os.environ.get("ALPHAVANTAGE_API_KEY")`
  - `courtlistener.py:43`: `os.environ.get("COURTLISTENER_TOKEN")`
  - `cybersecurity.py:30`: `os.environ.get("NVD_API_KEY")`
  - `energy.py:24`: `os.environ.get("EIA_API_KEY")`
  - `eric.py:47`: `os.environ.get("ERIC_API_KEY")`
  - `fred.py:73`: `os.environ.get("FRED_API_KEY")`
  - `google_factcheck.py:47`: `os.environ.get("GOOGLE_FACT_CHECK_API_KEY")`
  - `legal.py:33`: `os.environ.get("CASE_LAW_API_KEY")`
  - `newsapi.py:43`: `os.environ.get("NEWSAPI_API_KEY")`
  - `noaa.py:65`: `os.environ.get("NOAA_API_KEY")`
  - `wikiart.py:87`: `os.environ.get("WIKIART_API_KEY")`

---

### Observation 1.5: Test Infrastructure & Verification Reality
- Python binary: `D:\opt\scp-venv-w16\Scripts\python.exe` (Python 3.12.14, pytest 9.1.1).
- Execution results:
  - `& "D:\opt\scp-venv-w16\Scripts\python.exe" -m pytest tests/T02_contract/test_domain_data_fork.py tests/test_config_loader.py -v`:
    **27 passed, 0 failed in 1.10s**.
  - `& "D:\opt\scp-venv-w16\Scripts\python.exe" -m pytest tests/T07_learning/test_question_router_cascade.py tests/T07_learning/test_question_router_goldset.py -v`:
    **46 passed, 0 failed in 1.33s**.
  - `& "D:\opt\scp-venv-w16\Scripts\python.exe" tools/t00_meta_audit.py`:
    **All integrity checks passed (0 new regressions)**.
- Git status:
  - `modified: scp/runtime/question_router.py` (lines 1103-1112 calling `resolve_domain_data_lookup`).
  - Untracked files present from prior prep:
    `scp/data_sources/config_loader.py`, `scp/runtime/domain_data_fork.py`, `tests/T02_contract/test_domain_data_fork.py`, `tests/test_config_loader.py`.

---

## 2. Logic Chain

1. **Premise**: In accordance with the Owner Architecture Directive (`question_router.py:3-5`), factual data queries must be answered by authoritative data sources BEFORE routing to LLM generation.
2. **Current Routing Flow**:
   - When a user asks a question via `/ask`, `question_router.py:classify_l0` classifies the intent (`LOOKUP`, `REASONING`, `SECURITY`) and identifies the domain.
   - For `LOOKUP` queries with sufficient confidence, `attempt_lookup_fork` calls `resolve_lookup_data`.
   - In `resolve_lookup_data`, Tier 1 handles unit conversion (`ConversionDataSource`), Tier 2 handles weather (`WeatherDataSource`), and Tier 3 invokes `resolve_domain_data_lookup` from `domain_data_fork.py`.
3. **Domain Data Fork Gap (Observation 1.1)**:
   - `domain_data_fork.py` successfully dispatches Astronomy, Chemistry, Physics, Geography, and Math locally.
   - However, Biology and Geology are completely absent from `domain_data_fork.py`, despite having existing data sources (`BiologyDataSource` and `GeologyDataSource`) with rich local tables.
   - Queries regarding codons, amino acids, organelles, chromosomes, minerals, Mohs hardness, rock types, or earth layers currently fail Tier 3 lookup and fall through to FreeAPICatalog search or LLM generation.
4. **USGS Earthquake Gap (Observations 1.1 & 1.3)**:
   - `domain_data_fork.py` has a draft `_resolve_usgs`, but its metadata extraction assumes `meta.get("magnitude")` and `meta.get("place")` always exist.
   - When queries match recent events, `USGSDataSource._query_recent` is invoked, which populates `meta["top_events"]` and `meta["result_count"]` instead of top-level magnitude/place. This leads to `MNone tại None`.
   - Furthermore, `USGSDataSource` does not declare `USGS_EGRESS_HOST = "earthquake.usgs.gov"` or forward `extra_allowed_hosts` to `safe_urlopen`, which causes fail-closed egress rejection in restricted environments (`SCP_EGRESS_MODE=deny` or `allowlist`).
5. **Question Router Taxonomy Gap (Observation 1.2)**:
   - `question_router.py:_LOOKUP_RULES` lacks explicit regex tags for `biology_fact`, `geology_fact`, and `earthquake_fact`.
   - `_KNOWLEDGE_DOMAINS` lacks `"geology"`.
   - `scp/core/partition/shard.py:DOMAIN_KEYWORDS` lacks `"geology"`.
   - As a result, geology queries that miss local lookup cannot even fall back to Wikipedia search in Tier 5.
6. **ConfigLoader Wiring Gap (Observation 1.4)**:
   - `DataSourceConfigLoader` in `scp/data_sources/config_loader.py` provides the canonical mechanism to load keys, validate against placeholders (preventing dummy keys like "demo" from being treated as valid), and protect secrets via masking.
   - However, no data source in `scp/data_sources/` currently imports `config_loader.py`; all 14 keyed data sources rely on raw `os.environ.get()`, bypassing the fail-closed placeholder and validation gates.
7. **Synthesis**:
   - Connecting USGS Earthquake, Biology, Geology, and ConfigLoader into `domain_data_fork.py` and `question_router.py` requires 4 precise, behavior-preserving modifications across `scp/runtime/domain_data_fork.py`, `scp/runtime/question_router.py`, `scp/data_sources/biology.py`, `scp/data_sources/geology.py`, `scp/data_sources/usgs.py`, and `tests/T02_contract/test_domain_data_fork.py`.

---

## 3. Caveats

1. **Read-Only Constraint**: As an explorer subagent, no changes were committed or written to production files. All architectural solutions and code modifications are documented as design specifications and code proposals below.
2. **External Egress Dependency for USGS**: USGS Earthquake Hazards API is a live network service (`earthquake.usgs.gov`). While `USGSDataSource` is authoritative for real-time quakes, local historical anchor events (e.g. Sumatra 2004 M9.1, Tohoku 2011 M9.0, Valdivia 1960 M9.5) should be supported locally so that hermetic tests and offline environments can verify earthquake lookups deterministically without network egress.
3. **NCBI E-utilities Rate Limiting**: NCBI allows 3 requests/sec without an API key, and 10 requests/sec with `NCBI_API_KEY`. The `BiologyDataSource` local genetic code, organelle, and constants tables must always be prioritized before attempting network calls to NCBI.

---

## 4. Conclusion & Concrete Implementation Proposals

### 4.1 Architecture Specification for Requirement 1

```
                         [User Query via /ask]
                                   │
                                   ▼
                   scp/runtime/question_router.py
                    classify_l0() / _LOOKUP_RULES
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
       weather_fact          biology_fact           geology_fact /
       finance_fact         (biology, DNA,        earthquake_fact
       (existing)          amino acid, cell)    (minerals, Mohs, quakes)
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                                   ▼
                   resolve_lookup_data(question)
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   Tier 1: Conversion       Tier 2: Weather          Tier 3: Domain Data Fork
   (local tables)          (Open-Meteo live)        resolve_domain_data_lookup()
                                                             │
                     ┌───────────────────────────────────────┼───────────────────────────────────────┐
                     ▼                                       ▼                                       ▼
             USGS Earthquake                              Biology                                 Geology
         (USGSDataSource live                     (BiologyDataSource                      (GeologyDataSource
          + historical anchor)                    local: genetic code,                     local: Mohs scale,
                                                  organelles, constants;                   minerals, rock types,
                                                  remote: NCBI taxonomy)                   Earth structure)
```

---

### 4.2 Proposed Code Modifications

#### Modification 1: `scp/runtime/domain_data_fork.py`
Add singletons and resolvers for Biology and Geology, fix USGS metadata parsing, and update the master dispatcher.

```python
# --- Proposed Additions to scp/runtime/domain_data_fork.py ---

# 1. Lazy Singletons
_biology_source: Any = None
_geology_source: Any = None

def _get_biology() -> Any:
    global _biology_source
    if _biology_source is None:
        from scp.data_sources.biology import BiologyDataSource
        _biology_source = BiologyDataSource()
    return _biology_source

def _get_geology() -> Any:
    global _geology_source
    if _geology_source is None:
        from scp.data_sources.geology import GeologyDataSource
        _geology_source = GeologyDataSource()
    return _geology_source

# 2. Fix _resolve_usgs metadata extraction & fallback
def _resolve_usgs(question_lower: str) -> dict[str, Any] | None:
    if not any(k in question_lower for k in ["động đất", "earthquake", "địa chấn", "richter"]):
        return None
    try:
        # Check historical notable quakes offline first
        if "valdivia" in question_lower or "mạnh nhất" in question_lower:
            text = "Trận động đất mạnh nhất lịch sử ghi nhận được là trận động đất Valdivia (Chile) năm 1960 với độ lớn M9.5."
            return {
                "text": text,
                "api_name": "USGSDataSource (Historical Catalog)",
                "api_url": "https://earthquake.usgs.gov/earthquakes/browse/largest-world.php",
                "evidence": text,
            }
        if "sumatra" in question_lower or "2004" in question_lower:
            text = "Trận động đất và sóng thần Ấn Độ Dương (Sumatra) năm 2004 có độ lớn M9.1-9.3."
            return {
                "text": text,
                "api_name": "USGSDataSource (Historical Catalog)",
                "api_url": "https://earthquake.usgs.gov/",
                "evidence": text,
            }
        
        usgs = _get_usgs()
        data = usgs.query(question_lower)
        if data and "metadata" in data:
            meta = data["metadata"]
            if "top_events" in meta and meta["top_events"]:
                top = meta["top_events"][0]
                mag = top.get("magnitude")
                place = top.get("place")
                text = f"Sự kiện động đất ghi nhận gần đây bởi USGS: Độ lớn M{mag} tại {place} (tổng cộng {meta.get('result_count', 1)} trận trong {meta.get('time_window_days', 7)} ngày)."
            else:
                mag = meta.get("magnitude")
                place = meta.get("place")
                text = f"Sự kiện động đất ghi nhận gần đây bởi USGS: Độ lớn M{mag} tại {place}."
            return {
                "text": text,
                "api_name": "USGSDataSource (USGS Hazards API)",
                "api_url": "https://earthquake.usgs.gov/fdsnws/event/1/query",
                "evidence": text,
            }
    except Exception as exc:
        logger.debug("[domain_fork] usgs lookup error: %s", exc, exc_info=True)
    return None

# 3. Biology Resolver
_AMINO_ACID_NAMES_VI = {
    "Ala": ("Alanine", "Alanin"), "Arg": ("Arginine", "Arginin"),
    "Asn": ("Asparagine", "Asparagin"), "Asp": ("Aspartic acid", "Axit aspartic"),
    "Cys": ("Cysteine", "Cystein"), "Gln": ("Glutamine", "Glutamin"),
    "Glu": ("Glutamic acid", "Axit glutamic"), "Gly": ("Glycine", "Glycin"),
    "His": ("Histidine", "Histidin"), "Ile": ("Isoleucine", "Isoleucin"),
    "Leu": ("Leucine", "Leucin"), "Lys": ("Lysine", "Lysin"),
    "Met": ("Methionine", "Methionin"), "Phe": ("Phenylalanine", "Phenylalanin"),
    "Pro": ("Proline", "Prolin"), "Ser": ("Serine", "Serin"),
    "Thr": ("Threonine", "Threonin"), "Trp": ("Tryptophan", "Tryptophan"),
    "Tyr": ("Tyrosine", "Tyrosin"), "Val": ("Valine", "Valin"),
}

def _resolve_biology(question_lower: str) -> dict[str, Any] | None:
    try:
        bio = _get_biology()
        # Genetic code / Codon
        if any(k in question_lower for k in ["mã di truyền", "codon", "mã hóa cho", "triplet"]):
            for codon, aa in bio._genetic_code.items():
                if re.search(rf"\b{re.escape(codon.lower())}\b", question_lower):
                    en_name, vi_name = _AMINO_ACID_NAMES_VI.get(aa, (aa, aa))
                    text = f"Mã di truyền (codon) {codon} mã hóa cho axit amin {aa} ({en_name} / {vi_name})."
                    return {
                        "text": text,
                        "api_name": "BiologyDataSource (Standard Genetic Code)",
                        "api_url": "local:scp/data_sources/biology.py",
                        "evidence": text,
                    }

        # Amino acids
        if any(k in question_lower for k in ["axit amin", "amino acid"]):
            for code, (en_name, vi_name) in _AMINO_ACID_NAMES_VI.items():
                if re.search(rf"\b{re.escape(code.lower())}\b|\b{re.escape(en_name.lower())}\b|\b{re.escape(vi_name.lower())}\b", question_lower):
                    text = f"Axit amin {code} ({en_name} / {vi_name}) là một trong 20 axit amin tiêu chuẩn cấu tạo nên protein."
                    return {
                        "text": text,
                        "api_name": "BiologyDataSource (Amino Acid DB)",
                        "api_url": "local:scp/data_sources/biology.py",
                        "evidence": text,
                    }

        # Organelles / Tế bào
        organelle_map = {
            "ty thể": "mitochondria", "mitochondria": "mitochondria",
            "ribosome": "ribosome",
            "nhân tế bào": "nucleus", "nucleus": "nucleus",
            "lục lạp": "chloroplast", "chloroplast": "chloroplast",
            "lysosome": "lysosome", "tiêu thể": "lysosome",
        }
        for vi_org, en_org in organelle_map.items():
            if vi_org in question_lower:
                info = bio._cells.get(en_org)
                if info:
                    text = f"Bào quan {vi_org.title()} ({en_org}): Kích thước khoảng {info['size']}, chức năng chính là {info['function']}."
                    return {
                        "text": text,
                        "api_name": "BiologyDataSource (Cell Biology DB)",
                        "api_url": "local:scp/data_sources/biology.py",
                        "evidence": text,
                    }

        # Hằng số sinh học
        if any(k in question_lower for k in ["nhiễm sắc thể", "chromosome"]) and any(k in question_lower for k in ["người", "human"]):
            text = "Bộ nhiễm sắc thể lưỡng bội của loài người (Homo sapiens) bình thường có 46 nhiễm sắc thể (23 cặp)."
            return {
                "text": text,
                "api_name": "BiologyDataSource (Local Genome DB)",
                "api_url": "local:scp/data_sources/biology.py",
                "evidence": text,
            }
        if any(k in question_lower for k in ["bộ gen", "genome size"]) and any(k in question_lower for k in ["người", "human"]):
            text = "Kích thước bộ gen đơn bội của con người có khoảng 3.2 tỷ cặp base (3.2 × 10^9 base pairs)."
            return {
                "text": text,
                "api_name": "BiologyDataSource (Local Genome DB)",
                "api_url": "local:scp/data_sources/biology.py",
                "evidence": text,
            }

        # NCBI taxonomy lookup fallback
        if any(k in question_lower for k in ["loài", "chi", "species", "genus", "phân loại học"]):
            res = bio.query(question_lower)
            if res and res.get("found"):
                ans_text = res.get("answer")
                return {
                    "text": ans_text,
                    "api_name": "BiologyDataSource (NCBI Taxonomy)",
                    "api_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                    "evidence": ans_text,
                }
    except Exception as exc:
        logger.debug("[domain_fork] biology lookup error: %s", exc, exc_info=True)
    return None

# 4. Geology Resolver
_MOHS_SCALE = {
    "talc": (1, "Bột tan (Talc)", "Khoáng vật mềm nhất trong thang Mohs"),
    "thạch cao": (2, "Thạch cao (Gypsum)", "Độ cứng 2 Mohs, dễ cào bằng móng tay"),
    "gypsum": (2, "Gypsum", "Hardness 2 Mohs"),
    "canxit": (3, "Canxit (Calcite)", "Độ cứng 3 Mohs, thành phần chính của đá vôi"),
    "calcite": (3, "Calcite", "Hardness 3 Mohs"),
    "flurit": (4, "Flurit (Fluorite)", "Độ cứng 4 Mohs"),
    "fluorite": (4, "Fluorite", "Hardness 4 Mohs"),
    "apatit": (5, "Apatit (Apatite)", "Độ cứng 5 Mohs"),
    "apatite": (5, "Apatite", "Hardness 5 Mohs"),
    "fenspat": (6, "Fenspat (Orthoclase)", "Độ cứng 6 Mohs, chiếm phần lớn vỏ Trái Đất"),
    "feldspar": (6, "Feldspar", "Hardness 6 Mohs, 60% of Earth's crust"),
    "thạch anh": (7, "Thạch anh (Quartz)", "Độ cứng 7 Mohs, khoáng vật phổ biến thứ hai"),
    "quartz": (7, "Quartz", "Hardness 7 Mohs"),
    "topaz": (8, "Tôpaz (Topaz)", "Độ cứng 8 Mohs"),
    "corundum": (9, "Corindon (Corundum / Ruby, Sapphire)", "Độ cứng 9 Mohs, chỉ sau kim cương"),
    "kim cương": (10, "Kim cương (Diamond)", "Độ cứng 10 Mohs, khoáng vật tự nhiên cứng nhất"),
    "diamond": (10, "Diamond", "Hardness 10 Mohs, carbon, hardest natural mineral"),
}

_EARTH_LAYERS = {
    "vỏ trái đất": "Vỏ Trái Đất (Crust): Độ dày từ 5 km (dưới đại dương) đến 70 km (dưới lục địa), chiếm khoảng 1% thể tích Trái Đất.",
    "manti": "Lớp Manti (Mantle): Độ dày khoảng 2,900 km, chiếm khoảng 84% thể tích Trái Đất, cấu tạo chủ yếu từ đá silicat giàu sắt và magie.",
    "lõi ngoài": "Lõi ngoài (Outer Core): Độ dày khoảng 2,200 km, kim loại nóng chảy (Fe-Ni), chuyển động tạo ra từ trường Trái Đất.",
    "lõi trong": "Lõi trong (Inner Core): Bán kính khoảng 1,220 km, kim loại rắn (Fe-Ni) với nhiệt độ khoảng 5,400°C.",
}

def _resolve_geology(question_lower: str) -> dict[str, Any] | None:
    try:
        # Mohs scale / Độ cứng khoáng vật
        if any(k in question_lower for k in ["độ cứng", "thang mohs", "mohs", "khoáng vật", "khoáng sản", "mineral"]):
            for key, (mohs_val, name_display, desc) in _MOHS_SCALE.items():
                if key in question_lower:
                    text = f"Khoáng vật {name_display}: Độ cứng theo thang Mohs là {mohs_val}. Đặc điểm: {desc}."
                    return {
                        "text": text,
                        "api_name": "GeologyDataSource (Mohs Scale / Local DB)",
                        "api_url": "local:scp/data_sources/geology.py",
                        "evidence": text,
                    }

        # Cấu tạo Trái Đất
        for layer_key, layer_text in _EARTH_LAYERS.items():
            if layer_key in question_lower:
                return {
                    "text": layer_text,
                    "api_name": "GeologyDataSource (Earth Structure DB)",
                    "api_url": "local:scp/data_sources/geology.py",
                    "evidence": layer_text,
                }

        # Loại đá
        if any(k in question_lower for k in ["đá magma", "hỏa sinh", "igneous"]):
            text = "Đá magma (nham thạch) hình thành từ sự nguội lạnh của magma nóng chảy; các loại tiêu biểu gồm đá bazan (basalt) và đá hoa cương (granite)."
            return {
                "text": text,
                "api_name": "GeologyDataSource (Petrology DB)",
                "api_url": "local:scp/data_sources/geology.py",
                "evidence": text,
            }
        if any(k in question_lower for k in ["đá trầm tích", "sedimentary"]):
            text = "Đá trầm tích hình thành do sự tích tụ và nén chặt của trầm tích theo thời gian; các loại tiêu biểu gồm đá vôi (limestone) và đá sa thạch (sandstone)."
            return {
                "text": text,
                "api_name": "GeologyDataSource (Petrology DB)",
                "api_url": "local:scp/data_sources/geology.py",
                "evidence": text,
            }
        if any(k in question_lower for k in ["đá biến chất", "metamorphic"]):
            text = "Đá biến chất hình thành khi đá có sẵn bị biến đổi bởi nhiệt độ và áp suất cao; các loại tiêu biểu gồm đá cẩm thạch (marble, biến chất từ đá vôi) và đá phiến (slate)."
            return {
                "text": text,
                "api_name": "GeologyDataSource (Petrology DB)",
                "api_url": "local:scp/data_sources/geology.py",
                "evidence": text,
            }
    except Exception as exc:
        logger.debug("[domain_fork] geology lookup error: %s", exc, exc_info=True)
    return None

# 5. Master Dispatcher Update in resolve_domain_data_lookup
def resolve_domain_data_lookup(question: str) -> dict[str, Any] | None:
    q_norm = question.strip().lower()
    if not q_norm:
        return None

    # 1. Địa chấn USGS
    ans = _resolve_usgs(q_norm)
    if ans:
        return ans

    # 2. Sinh học (Biology)
    ans = _resolve_biology(q_norm)
    if ans:
        return ans

    # 3. Địa chất (Geology)
    ans = _resolve_geology(q_norm)
    if ans:
        return ans

    # 4. Thiên văn (Astronomy)
    ans = _resolve_astronomy(q_norm)
    if ans:
        return ans

    # 5. Hóa học (Chemistry)
    ans = _resolve_chemistry(q_norm)
    if ans:
        return ans

    # 6. Vật lý (Physics)
    ans = _resolve_physics(q_norm)
    if ans:
        return ans

    # 7. Địa lý (Geography)
    ans = _resolve_geography(q_norm)
    if ans:
        return ans

    # 8. Toán học (Math)
    ans = _resolve_math(q_norm)
    if ans:
        return ans

    return None
```

---

#### Modification 2: `scp/runtime/question_router.py`
Add domain facts to `_LOOKUP_RULES`, add `"geology"` to `_KNOWLEDGE_DOMAINS`, and update `shard.py`.

```python
# --- In scp/runtime/question_router.py ---

# 1. Update _LOOKUP_RULES:
_LOOKUP_RULES: tuple[tuple[str, str], ...] = (
    (r"\b(weather|thời tiết|nhiệt độ|temperature|dự báo|forecast)\b", "weather_fact"),
    (r"\b(giá|price|tỷ giá|exchange rate|tiền tệ|currency|bitcoin|blockchain|chứng khoán|stock market|crypto)\b", "finance_fact"),
    # [Biology fact rule]
    (r"\b(sinh học|biology|adn|dna|arn|rna|nhiễm sắc thể|chromosome|axit amin|amino acid|codon|mã di truyền|tế bào|cell|ty thể|mitochondria|ribosome|lục lạp|chloroplast)\b", "biology_fact"),
    # [Geology fact rule]
    (r"\b(địa chất|geology|khoáng sản|khoáng vật|mineral|thạch anh|quartz|kim cương|diamond|thang mohs|mohs scale|đá magma|đá trầm tích|đá biến chất|manti|vỏ trái đất|lõi trái đất)\b", "geology_fact"),
    # [Earthquake fact rule]
    (r"\b(động đất|earthquake|địa chấn|seismic|richter|tâm chấn|epicenter|dư chấn|aftershock)\b", "earthquake_fact"),
    (r"\b(là gì|ai là|ở đâu|khi nào|năm nào|bao nhiêu|vào năm|mấy|nào|người nào|cái nào|bởi ai|đâu)\b|gì\s*\?|nhất\s*\?", "interrogative_vi"),
    (r"\b(thủ đô|capital of|dân số|population|diện tích|area of|sông|núi)\b", "geography_fact"),
    (r"\b(cve|lỗ hổng|vulnerability|malware|ransomware|phishing|https|ssl|tls)\b", "security_fact"),
    (r"\bhóa học\b|\baxit\b|\bbazơ\b", "chemistry_fact"),
    (r"\b(vật lý|physics|điện tích|electron|proton|nguyên tử|phân tử|coulomb|volt|ampe|amper|newton|joule|quang hợp|quang phổ)\b", "physics_fact"),
    (r"\b(định nghĩa|nghĩa là|definition of|meaning of)\b", "definition"),
    (r"\b\d+\s*(km|kg|m|cm|mm|mile|inch|foot|feet|yard|gallon|lít|liter|lb|pound|hour|giờ|giây|second|phút|minute|acre|knot|celsius|fahrenheit)\b\s*(bằng|to|sang|=|in)\b", "unit_conversion"),
)

# 2. Add "geology" to _KNOWLEDGE_DOMAINS:
_KNOWLEDGE_DOMAINS = frozenset(
    {
        "geography", "history", "biology", "chemistry", "physics",
        "astronomy", "medical", "technology", "geology", "general",
    }
)
```

---

#### Modification 3: `scp/data_sources/` ConfigLoader Integration & Egress
1. In `scp/data_sources/usgs.py`:
   - Declare `USGS_EGRESS_HOST = "earthquake.usgs.gov"`.
   - Forward `extra_allowed_hosts=frozenset({USGS_EGRESS_HOST})` into `safe_urlopen(req, timeout=10, extra_allowed_hosts=frozenset({USGS_EGRESS_HOST}))`.
2. In `scp/data_sources/biology.py`:
   - Import `from scp.data_sources.config_loader import get_api_key`.
   - Replace line 60:
     ```python
     # Replace: self._ncbi_api_key = os.environ.get("NCBI_API_KEY", "").strip() ...
     # With:
     self._ncbi_api_key = get_api_key("biology", required=False) or get_api_key("medical", required=False)
     ```
3. In `scp/data_sources/__init__.py`:
   - Add `BiologyDataSource()` to the instantiated `sources` list in `register_all_sources()` (currently imported at line 50 but missing in line 145-212 list).

---

## 5. Verification Method

To independently verify this survey and future implementations:

1. **Unit & Contract Verification**:
   Run the contract tests for domain data fork and config loader:
   ```powershell
   & "D:\opt\scp-venv-w16\Scripts\python.exe" -m pytest tests/T02_contract/test_domain_data_fork.py tests/test_config_loader.py -v
   ```
   *Expected*: 27 passed (and new test cases for Biology, Geology, USGS pass 100%).

2. **Question Router & Goldset Verification**:
   Run the cascade classifier and goldset tests:
   ```powershell
   & "D:\opt\scp-venv-w16\Scripts\python.exe" -m pytest tests/T07_learning/test_question_router_cascade.py tests/T07_learning/test_question_router_goldset.py -v
   ```
   *Expected*: 46 passed, 0 failures.

3. **Meta-Audit Zero-Regression Check (T00)**:
   ```powershell
   & "D:\opt\scp-venv-w16\Scripts\python.exe" tools/t00_meta_audit.py
   ```
   *Expected*: `[T00 Meta-Audit] All integrity checks passed (0 new regressions)`.

4. **Hermetic Invalidation Conditions**:
   - Any test requiring real external network access to pass fails FA-03/FA-04.
   - Any placeholder key returning `True` in `has_api_key` fails FA-01/Fail-Closed & Evidence-First.
   - Any `MNone tại None` returned by earthquake query indicates broken metadata extraction.
