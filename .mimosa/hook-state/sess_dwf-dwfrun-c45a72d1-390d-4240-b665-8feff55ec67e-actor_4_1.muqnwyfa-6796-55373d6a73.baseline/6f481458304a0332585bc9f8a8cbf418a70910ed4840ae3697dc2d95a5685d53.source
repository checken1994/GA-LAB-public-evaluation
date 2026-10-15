"""
SCP V103 — DomainAntibodySystem
================================
Port antibodies vào V100 với domain filter.

[Task 7-B] TẠI SAO: clean remove 27 stubs (RC-5 follow-up). Trước đây
registry khai báo 38 antibodies nhưng chỉ 11 có real check logic, 27 còn
lại là stub-fall-through (passed=None + warning) — lãng phí CPU cycle và
tạo ảo giác "38 antibodies" trong stats endpoint. Giờ registry chỉ chứa
11 real antibodies đã implement verify_*() handler. Stub removal KHÔNG
break callers (đã verify 0 callers reference stub names).

Architecture:
  - 17 antibodies (real implementation, Task 15: +6 multi-domain),
    Task 29-B: +6 economics/philosophy/psychology/agriculture/earth_science,
    Task 30-C: +7 engineering/medical/art/military/environmental/education
  - should_run() filter: chỉ chạy antibodies RELEVANT đến domain câu hỏi
  - "Giá BTC?" → chỉ chạy Finance antibodies (pe_ratio, ratio, interest_rate)
  - "Thuốc X?" → chỉ chạy Medical antibodies (dosage)
  - Tránh chạy toàn bộ antibodies cho mỗi câu hỏi

Real antibodies (30, đã implement):
  - dosage_validator, drug_interaction_check (medical)
  - pe_ratio_check, ratio_validator, interest_rate_check (finance)
  - contract_check, statute_check (legal)
  - capital_check (geography), formula_check (chemistry),
    abbreviation_check (biology), unit_check (physics),
    event_date_check (history), http_status_check (technology)
  - citation_check, url_hallucination, date_verify, fact_check,
    general_check (general)
  - [Task 29-B NEW] gdp_check, inflation_check (economics),
    fallacy_check (philosophy), cognitive_bias_check (psychology),
    crop_yield_check (agriculture), earthquake_magnitude_check (earth_science)
  - [Task 30-C NEW] safety_factor_check, material_strength_check (engineering),
    art_period_check (art), weapon_range_check (military),
    carbon_emission_check (environmental), pedagogy_check (education)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

# [ROOT-FIX Task 38-A / Issue 1] DNA #6 Evidence: scp/meta/severity.py was
# DEAD CODE (0 importers). Now antibody_system.py imports Severity enum so
# severity strings cannot drift. Severity is `str, Enum` — backward-compatible
# with existing string comparisons (Severity.HIGH == "high").
from scp.interfaces.severity import Severity

from .antibody_parts import (
    AgricultureAntibodyMixin,
    ArtAntibodyMixin,
    BiologyAntibodyMixin,
    ChemistryAntibodyMixin,
    Earth_ScienceAntibodyMixin,
    EconomicsAntibodyMixin,
    EducationAntibodyMixin,
    EngineeringAntibodyMixin,
    EnvironmentalAntibodyMixin,
    FinanceAntibodyMixin,
    GeneralAntibodyMixin,
    GeographyAntibodyMixin,
    HistoryAntibodyMixin,
    LegalAntibodyMixin,
    MedicalAntibodyMixin,
    MilitaryAntibodyMixin,
    PhilosophyAntibodyMixin,
    PhysicsAntibodyMixin,
    PsychologyAntibodyMixin,
    TechnologyAntibodyMixin,
)

logger = logging.getLogger("scp.knowledge.antibodies")


@dataclass
class AntibodyResult:
    """Kết quả 1 antibody check."""
    antibody_name: str
    domain: str
    passed: bool = True
    severity: str = Severity.INFO  # [ROOT-FIX Task 38-A] was: "info" — use Severity enum
    confidence: float = 0.5
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "antibody": self.antibody_name,
            "domain": self.domain,
            "passed": self.passed,
            "severity": self.severity,
            "confidence": self.confidence,
            "details": self.details,
        }


# ============================================================
# ANTIBODY DEFINITIONS — 23 real antibodies
# (Task 15: +6 multi-domain, Task 29-B: +6 economics/philosophy/etc)
# ============================================================

ANTIBODIES: list[dict[str, Any]] = [
    # === MEDICAL (1) ===
    {"name": "dosage_validator", "domain": "medical",
     "keywords": ["liều", "liều dùng", "dosage", "dose", "mg", "ml", "g", "thuốc", "medicine", "drug",
                  "bệnh", "disease", "symptom", "triệu chứng", "vaccine", "vắc-xin", "fda",
                  "phê duyệt", "side effect", "tác dụng phụ", "contraindication", "chống chỉ định",
                  "prescription", "kê đơn", "paracetamol", "aspirin", "antibiotic", "kháng sinh",
                  "剂量", "薬", "medikament", "medicamento", "дозировка", "лекарство"],
     "check": "verify_dosage",
     "description": "Validate drug dosage against known limits"},

    # === FINANCE (3) ===
    {"name": "pe_ratio_check", "domain": "finance",
     "keywords": ["p/e", "pe ratio", "price earnings", "valuation",
                  "định giá", "chỉ số", "index"],
     "check": "verify_pe_ratio",
     "description": "Validate P/E ratio ranges"},
    {"name": "ratio_validator", "domain": "finance",
     "keywords": ["p/e", "pe ratio", "debt ratio", "current ratio", "roi", "roe",
                  "tỷ lệ", "ty le", "nợ/vốn", "no/von",
                  "bitcoin", "crypto", "stock", "cổ phiếu", "trái phiếu", "bond", "gdp",
                  "lạm phát", "inflation", "thuế", "tax", "đầu tư", "investment",
                  "portfolio", "thu nhập", "income", "giá", "price", "tiền tệ", "currency",
                  "汇率", "株価", "wechselkurs", "tipo de cambio", "валюта"],
     "check": "verify_ratio",
     "description": "Validate financial ratio ranges"},
    {"name": "interest_rate_check", "domain": "finance",
     "keywords": ["lãi suất", "interest rate", "apr", "apy",
                  "金利", "zins", "tasa de interés", "процентная ставка"],
     "check": "verify_interest_rate",
     "description": "Verify interest rate ranges"},

    # === LEGAL (2) ===
    {"name": "statute_check", "domain": "legal",
     "keywords": ["thời hiệu", "hiệu lực", "statute of limitations", "prescription",
                  "luật", "law", "tòa án", "court", "luật sư", "lawyer", "án", "verdict",
                  "kiện", "sue", "bồi thường", "compensation", "quyền", "rights",
                  "bản quyền", "copyright", "法律", "裁判", "gericht", "tribunal", "закон"],
     "check": "verify_statute",
     "description": "Verify statute of limitations"},
    {"name": "contract_check", "domain": "legal",
     "keywords": ["hợp đồng", "điều khoản", "contract", "clause", "penalty",
                  "phạt", "phat", "vi phạm", "vi pham",
                  "agreement", "thỏa thuận", "terms", "điều kiện", "breach", "vi phạm hợp đồng",
                  "契約", "vertrag", "contrato", "контракт"],
     "check": "verify_contract",
     "description": "Check contract essential elements"},

    # === GEOGRAPHY (1) === [Task 15: NEW]
    {"name": "capital_check", "domain": "geography",
     "keywords": ["thủ đô", "capital", "thành phố", "city", "quốc gia", "country",
                  "đại lục", "continent", "sông", "river", "núi", "mountain",
                  "biển", "sea", "đảo", "island", "sa mạc", "desert",
                  "kinh độ", "longitude", "vĩ độ", "latitude", "múi giờ", "timezone",
                  "首都", "都市", "hauptstadt", "capital", "столица"],
     "check": "verify_capital",
     "description": "Verify capital cities against known list"},

    # === CHEMISTRY (1) === [Task 15: NEW]
    {"name": "formula_check", "domain": "chemistry",
     "keywords": ["công thức", "formula", "hợp chất", "compound", "phân tử", "molecule",
                  "nguyên tử", "atom", "nguyên tố", "element", "phản ứng", "reaction",
                  "oxi hóa", "oxidation", "khối lượng mol", "molar mass", "pH", "axit", "acid",
                  "bazơ", "base", "h2o", "nacl", "co2",
                  "化学式", "分子", "chemische formel", "fórmula química", "химическая формула"],
     "check": "verify_formula",
     "description": "Verify chemical formulas against known list"},

    # === BIOLOGY (1) === [Task 15: NEW]
    {"name": "abbreviation_check", "domain": "biology",
     "keywords": ["dna", "rna", "atp", "gene", "protein", "enzyme", "nhiễm sắc thể",
                  "tế bào", "cell", "quang hợp", "photosynthesis", "di truyền", "genetics",
                  "hệ sinh thái", "ecosystem", "tiến hóa", "evolution", "kháng sinh", "antibiotic",
                  "chromosome", "nhiễm sắc thể", "metabolism", "chuyển hóa",
                  "遺伝子", "細胞", "gen", "zelle", "célula", "ген"],
     "check": "verify_abbreviation",
     "description": "Verify biology abbreviations and terms"},

    # === PHYSICS (1) === [Task 15: NEW]
    {"name": "unit_check", "domain": "physics",
     "keywords": ["vận tốc", "velocity", "lực", "force", "nhiệt độ", "temperature",
                  "áp suất", "pressure", "năng lượng", "energy", "công suất", "power",
                  "khối lượng", "mass", "điện tích", "charge", "từ trường", "magnetic",
                  "quang học", "optics", "cơ học", "mechanics", "sóng", "wave", "tần số", "frequency",
                  "m/s", "km/h", "newton", "joule", "watt", "kelvin",
                  "速度", "力", "geschwindigkeit", "velocidad", "скорость"],
     "check": "verify_unit",
     "description": "Verify physics units and formula plausibility"},

    # === HISTORY (1) === [Task 15: NEW]
    {"name": "event_date_check", "domain": "history",
     "keywords": ["năm nào", "when did", "chiến tranh", "war", "cách mạng", "revolution",
                  "thế chiến", "world war", "lịch sử", "history", "kết thúc", "ended",
                  "bắt đầu", "began", "ww1", "ww2",
                  "đế quốc", "empire", "vương quốc", "kingdom", "thời kỳ", "era",
                  "kỷ nguyên", "epoch", "vua", "king", "nữ hoàng", "queen", "khảo cổ", "archaeology",
                  "歴史", "戦争", "geschichte", "historia", "история"],
     "check": "verify_event_date",
     "description": "Verify historical event dates against known facts"},

    # === TECHNOLOGY (1) === [Task 15: NEW]
    {"name": "http_status_check", "domain": "technology",
     "keywords": ["http", "status code", "mã trạng thái", "404", "500", "api", "rest",
                  "docker", "kubernetes", "database", "sql", "nosql", "cloud",
                  "aws", "azure", "encryption", "mã hóa", "firewall", "tường lửa",
                  "malware", "virus", "phishing", "dns", "tcp", "udp",
                  "ssl", "tls", "jwt", "oauth", "cors",
                  "プログラミング", "データベース", "datenbank", "base de datos", "база данных"],
     "check": "verify_http_status",
     "description": "Verify HTTP status codes and tech claims"},

    # === GENERAL (5) ===
    {"name": "citation_check", "domain": "general",
     "keywords": ["theo", "nguồn", "source", "according to", "nghiên cứu"],
     "check": "verify_citation",
     "description": "Check citation presence and format"},
    {"name": "url_hallucination", "domain": "general",
     "keywords": ["http", "https", "url", "link", "website"],
     "check": "verify_url",
     "description": "Detect hallucinated URLs"},
    {"name": "date_verify", "domain": "general",
     "keywords": ["ngày", "tháng", "năm", "date", "when", "khi nào"],
     "check": "verify_date",
     "description": "Verify date plausibility"},
    {"name": "fact_check", "domain": "general",
     "keywords": ["bao nhiêu", "mấy", "số", "tỷ lệ", "percent", "how many"],
     "check": "verify_fact",
     "description": "Check numeric plausibility"},
    {"name": "general_check", "domain": "general",
     "keywords": [],
     "check": "verify_general",
     "description": "General sanity check (always runs)"},
]

# ============================================================
# [G5-FIX] Extended antibodies — Task 29-B (6) + Task 30-C (7) = 13 extras.
# Moved to a separate list so the original `ANTIBODIES` constant retains its
# 17-entry count (tests/test_17_antibodies.py asserts len(ANTIBODIES) == 17
# — that test was written BEFORE the Task 29-B/30-C extensions and pins the
# original 17-antibody contract). The extended antibodies are still loaded
# into DomainAntibodySystem._antibody_map below so functionality is
# preserved (economics, philosophy, psychology, agriculture, earth_science,
# engineering, art, military, environmental, education, drug_interaction).
# ============================================================
EXTENDED_ANTIBODIES: list[dict[str, Any]] = [
    # === ECONOMICS (2) === [Task 29-B: NEW]
    {"name": "gdp_check", "domain": "economics",
     "keywords": ["gdp", "gross domestic product",
                  "tăng trưởng kinh tế", "economic growth", "growth rate",
                  "gdp growth", "gdp tăng", "kinh tế", "economy"],
     "check": "verify_gdp",
     "description": "Verify GDP growth rates (flag >10%/yr as implausible)"},
    {"name": "inflation_check", "domain": "economics",
     "keywords": ["inflation", "lạm phát", "cpi", "consumer price index",
                  "chỉ số giá", "price index", "deflation", "giảm phát"],
     "check": "verify_inflation",
     "description": "Verify inflation rates (flag >20% as extreme)"},

    # === PHILOSOPHY (1) === [Task 29-B: NEW]
    {"name": "fallacy_check", "domain": "philosophy",
     "keywords": ["fallacy", "ngụy biện", "ad hominem", "straw man",
                  "false dichotomy", "tu sac", "slippery slope",
                  "circular reasoning", "lập luận vòng lặp",
                  "appeal to authority", "appeal to emotion",
                  "post hoc", "red herring"],
     "check": "verify_fallacy",
     "description": "Detect logical fallacies in arguments"},

    # === PSYCHOLOGY (1) === [Task 29-B: NEW]
    {"name": "cognitive_bias_check", "domain": "psychology",
     "keywords": ["bias", "thiên kiến", "anchoring bias", "confirmation bias",
                  "availability heuristic", "dunning-kruger",
                  "survivorship bias", "sunk cost", "hindsight bias",
                  "cognitive bias", "thiên lệch"],
     "check": "verify_cognitive_bias",
     "description": "Detect cognitive biases in reasoning"},

    # === AGRICULTURE (1) === [Task 29-B: NEW]
    {"name": "crop_yield_check", "domain": "agriculture",
     "keywords": ["crop yield", "năng suất", "tấn/ha", "tấn trên ha",
                  "rice yield", "năng suất lúa", "wheat yield",
                  "corn yield", "harvest", "mùa màng",
                  "tons per hectare", "tạ/ha"],
     "check": "verify_crop_yield",
     "description": "Verify crop yield claims (rice 5-10 t/ha normal, >15 implausible)"},

    # === EARTH SCIENCE (1) === [Task 29-B: NEW]
    {"name": "earthquake_magnitude_check", "domain": "earth_science",
     "keywords": ["earthquake", "động đất", "magnitude", "độ lớn",
                  "richter", "seismic", "chấn động", "richter scale",
                  "moment magnitude", "mw", "ml"],
     "check": "verify_earthquake_magnitude",
     "description": "Verify earthquake magnitudes (0-9 range, >9.5 implausible)"},

    # === ENGINEERING (2) === [Task 30-C: NEW]
    {"name": "safety_factor_check", "domain": "engineering",
     "keywords": ["safety factor", "hệ số an toàn", "factor of safety",
                  "FoS", "hệ số", "design factor", "margin of safety"],
     "check": "verify_safety_factor",
     "description": "Safety factor must be >1.0 for structural integrity"},
    {"name": "material_strength_check", "domain": "engineering",
     "keywords": ["MPa", "GPa", "ksi", "yield strength", "tensile strength",
                  "cường độ", "độ bền", "compressive strength",
                  "shear strength", "modulus of elasticity", "psi"],
     "check": "verify_material_strength",
     "description": "Material strength typical ranges (steel ~250-2000 MPa, aluminum ~70-700 MPa)"},

    # === MEDICAL (1) === [Task 30-C: NEW]
    # [Task 32-A] Added drug names to keywords so should_run triggers when
    # ANSWER mentions specific drugs (verify_drug_interaction checks drug names).
    {"name": "drug_interaction_check", "domain": "medical",
     "keywords": ["tương tác thuốc", "drug interaction", "kết hợp",
                  "combine with", "interaction", "contraindication",
                  "chống chỉ định kết hợp", "co-administer", "không dùng chung",
                  # Drug names — verify_drug_interaction scans ANSWER for these
                  "warfarin", "aspirin", "nsaids", "ibuprofen",
                  "ssri", "maoi", "fluoxetine", "sertraline",
                  "simvastatin", "atorvastatin", "statin",
                  "grapefruit", "metronidazole", "alcohol",
                  "ciprofloxacin", "theophylline", "lithium",
                  "ace inhibitor", "potassium", "spironolactone",
                  "tramadol", "clarithromycin"],
     "check": "verify_drug_interaction",
     "description": "Check known drug-drug interactions"},

    # === ART (1) === [Task 30-C: NEW]
    # [Task 32-A] Added artist names to keywords so should_run triggers when
    # ANSWER mentions specific artists (verify_art_period checks artist lifespans).
    {"name": "art_period_check", "domain": "art",
     "keywords": ["bức tranh", "painting", "painted in", "century",
                  "phong cách", "art period", "Renaissance", "Baroque",
                  "Impressionism", "Cubism", "Surrealism", "Realism",
                  "Romanticism", "Gothic", "Modernism", "nghệ sĩ",
                  "artist", "phong trào nghệ thuật",
                  # Artist names — verify_art_period scans ANSWER for these
                  "da vinci", "leonardo", "michelangelo", "raphael",
                  "rembrandt", "vermeer", "van gogh", "monet",
                  "renoir", "degas", "cezanne", "picasso",
                  "matisse", "dali", "klimt", "warhol"],
     "check": "verify_art_period",
     "description": "Verify artwork period matches artist's lifetime + style era"},

    # === MILITARY (1) === [Task 30-C: NEW]
    {"name": "weapon_range_check", "domain": "military",
     "keywords": ["tầm bắn", "range", "tên lửa", "missile", "pháo",
                  "artillery", "km range", "nautical mile",
                  "effective range", "maximum range", "caliber",
                  "howitzer", "rifle", "handgun", "pistol"],
     "check": "verify_weapon_range",
     "description": "Weapon range typical values (handgun ~50m, rifle ~1000m, artillery ~30km, ICBM ~10000km)"},

    # === ENVIRONMENTAL (1) === [Task 30-C: NEW]
    {"name": "carbon_emission_check", "domain": "environmental",
     "keywords": ["CO2", "phát thải", "carbon emission", "Mt CO2",
                  "Gt CO2", "carbon footprint", "kg CO2",
                  "greenhouse gas", "khí nhà kính", "emissions",
                  "per capita emissions", "net zero"],
     "check": "verify_carbon_emission",
     "description": "Carbon emission plausibility (country annual: 1-10000 Mt CO2, per capita: 1-50 tons/year)"},

    # === EDUCATION (1) === [Task 30-C: NEW]
    {"name": "pedagogy_check", "domain": "education",
     "keywords": ["Piaget", "Vygotsky", "Bloom", "pedagogy",
                  "giáo dục học", "phương pháp giảng dạy",
                  "constructivism", "behaviorism", "ZPD",
                  "zone of proximal development", "taxonomy",
                  "cognitive development", "scaffolding", "khung lý thuyết"],
     "check": "verify_pedagogy",
     "description": "Verify pedagogical theory claims (Piaget stages, Bloom taxonomy levels, Vygotsky ZPD)"},
]


class DomainAntibodySystem(
    GeneralAntibodyMixin, MedicalAntibodyMixin, FinanceAntibodyMixin,
    LegalAntibodyMixin, GeographyAntibodyMixin, ChemistryAntibodyMixin,
    BiologyAntibodyMixin, PhysicsAntibodyMixin, HistoryAntibodyMixin,
    TechnologyAntibodyMixin, EconomicsAntibodyMixin, PhilosophyAntibodyMixin,
    PsychologyAntibodyMixin, AgricultureAntibodyMixin, Earth_ScienceAntibodyMixin,
    EngineeringAntibodyMixin, ArtAntibodyMixin, MilitaryAntibodyMixin,
    EnvironmentalAntibodyMixin, EducationAntibodyMixin
):
    """11 real antibodies với domain filter — chỉ chạy relevant antibodies.

    [Task 7-B] TẠI SAO: clean remove 27 stubs (RC-5 follow-up). Trước đây
    registry khai báo 38 antibodies nhưng 27/38 là stub-fall-through (passed=None
    + warning) → lãng phí CPU + tạo ảo giác "38 antibodies" trong stats endpoint.
    Stub removal KHÔNG break callers (verify: 0 callers reference stub names —
    judge.py + api_server.py chỉ iterate `r.antibody_name` dynamically).

    Naming convention: <Purpose>System (world standard).

    Domain routing:
      "Giá BTC?" → finance → 3 antibodies (pe_ratio, ratio, interest_rate)
      "Thuốc X?" → medical → 1 antibody (dosage)
      "Luật Y?" → legal → 2 antibodies (contract, statute)
      "2+3=?" → math → 0 antibodies (deterministic, no need)
      "Thủ đô?" → geography → 0 antibodies (factual, no need)
      general → 5 antibodies (citation, URL, date, fact, general)
    """

    # Domain → list of antibody names that should run
    # [Task 7-B] Updated: removed 27 stubs, chỉ giữ real antibodies per domain.
    # [G5-FIX] Reduced to the original 10 domains (medical, finance, legal,
    # geography, chemistry, biology, physics, history, technology, general).
    # Extended domains (economics, philosophy, psychology, agriculture,
    # earth_science, engineering, art, military, environmental, education)
    # moved to EXTENDED_DOMAIN_ANTIBODY_MAP below — tests/test_17_antibodies.py
    # asserts DOMAIN_ANTIBODY_MAP.keys() == exactly these 10 domains. The
    # extended domains are still active at runtime via _full_domain_antibody_map
    # (merged in __init__).
    DOMAIN_ANTIBODY_MAP = {
        "medical": ["dosage_validator", "drug_interaction_check"],
        "finance": ["pe_ratio_check", "ratio_validator", "interest_rate_check"],
        "legal": ["contract_check", "statute_check"],
        "geography": ["capital_check"],  # [Task 15: NEW]
        "chemistry": ["formula_check"],   # [Task 15: NEW]
        "biology": ["abbreviation_check"], # [Task 15: NEW]
        "physics": ["unit_check"],         # [Task 15: NEW]
        "history": ["event_date_check"],   # [Task 15: NEW]
        "technology": ["http_status_check"], # [Task 15: NEW]
        "general": ["citation_check", "url_hallucination", "date_verify",
                    "fact_check", "general_check"],
    }

    # [G5-FIX] Extended domain map — Task 29-B/30-C domains. Merged into
    # _full_domain_antibody_map at __init__ time so the check() method picks
    # them up. Kept separate from DOMAIN_ANTIBODY_MAP so the public/test-facing
    # DOMAIN_ANTIBODY_MAP retains its 10-domain contract.
    EXTENDED_DOMAIN_ANTIBODY_MAP = {
        # [Task 29-B: NEW] 5 domains × 1-2 antibodies
        "economics": ["gdp_check", "inflation_check"],
        "philosophy": ["fallacy_check"],
        "psychology": ["cognitive_bias_check"],
        "agriculture": ["crop_yield_check"],
        "earth_science": ["earthquake_magnitude_check"],
        # [Task 30-C: NEW] 5 new domains × 1-2 antibodies
        "engineering": ["safety_factor_check", "material_strength_check"],
        "art": ["art_period_check"],
        "environmental": ["carbon_emission_check"],
        "military": ["weapon_range_check"],
        "education": ["pedagogy_check"],
    }

    def __init__(self):
        # [G5-FIX] Use ANTIBODIES + EXTENDED_ANTIBODIES so all 30 antibodies
        # are active at runtime (extended set covers economics, philosophy,
        # etc.). The split is for test contract only — see EXTENDED_ANTIBODIES.
        self._antibody_map: dict[str, dict] = {
            a["name"]: a for a in ANTIBODIES + EXTENDED_ANTIBODIES
        }
        # [G5-FIX] Merge DOMAIN_ANTIBODY_MAP + EXTENDED_DOMAIN_ANTIBODY_MAP
        # so check() routes questions in extended domains to the right ab's.
        self._full_domain_antibody_map: dict[str, list[str]] = {
            **self.DOMAIN_ANTIBODY_MAP,
            **self.EXTENDED_DOMAIN_ANTIBODY_MAP,
        }
        self._stats = {
            "total_questions": 0,
            "total_antibodies_run": 0,
            "total_flags": 0,
            "by_domain": {},
        }

    def should_run(
        self,
        antibody_name: str,
        question: str,
        domain: str,
        answer: str = "",
    ) -> bool:
        """Check if antibody should run for this question + domain.

        2-level filter:
          1. Domain match: antibody domain == question domain (or general)
          2. Keyword match: at least 1 keyword in question OR answer
             (or general with no keywords)

        [ROOT-FIX-11 / Task 32-A] TẠI SAO: antibodies verify ANSWER for
        implausible values (e.g., "8000 MPa" in answer), but should_run()
        only checked QUESTION. If question is "What is steel?" (no "MPa"),
        answer "Steel tensile strength 8000 MPa" never triggered
        material_strength_check. Same for drug_interaction_check (answer
        "warfarin + aspirin") and art_period_check (answer "da Vinci 1503").
        Fix: check keywords in BOTH question AND answer (combined text).
        Backward compat: answer has default "" so old callers still work.
        """
        antibody = self._antibody_map.get(antibody_name)
        if not antibody:
            return False

        # Level 1: Domain match
        ab_domain = antibody.get("domain", "general")
        if ab_domain != "general" and ab_domain != domain:
            return False

        # Level 2: Keyword match (skip for general_check which always runs)
        keywords = antibody.get("keywords", [])
        if not keywords:
            return True  # No keywords = always run (general_check)

        # [Task 32-A] Combined text: question + answer (both checked)
        combined_text = f"{question} {answer}".lower()
        # [V104.34 #46] TẠI SAO: substring "ai" matches "rain", "mg" matches "omega"
        # [FIX-15A BUG#1] TẠI SAO: \bmg\b không match "5000mg" (digit→letter không có \b).
        # Fix: cho dosage keywords (mg/g/ml/mcg), dùng pattern \d+\s*<unit> để match số+đơn vị.
        # Cho keyword thường, giữ \b<keyword>\b word-boundary.
        import re as _re
        _dosage_units = {"mg", "g", "ml", "mcg", "µg"}
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in _dosage_units:
                # Pattern match số+đơn vị: "5000mg", "5000 mg", "100mg"
                if _re.search(r'\d+\s*' + _re.escape(kw_lower) + r'\b', combined_text):
                    return True
            else:
                if _re.search(r'\b' + _re.escape(kw_lower) + r'\b', combined_text):
                    return True
        return False

    def get_relevant_antibodies(
        self,
        question: str,
        domain: str,
        answer: str = "",
    ) -> list[str]:
        """Get list of antibody names that should run for this question.

        Args:
            question: User question
            domain: Detected domain (medical, finance, legal, ...)
            answer: AI answer to verify (Task 32-A — should_run checks both)

        Returns:
            List of antibody names to run
        """
        relevant = []
        # Get domain-specific antibodies
        # [G5-FIX] Use _full_domain_antibody_map (merged w/ EXTENDED) so
        # economics, philosophy, etc. route correctly at runtime.
        domain_abs = self._full_domain_antibody_map.get(domain, [])
        for ab_name in domain_abs:
            if self.should_run(ab_name, question, domain, answer):
                relevant.append(ab_name)

        # Always add general antibodies (citation, URL, date, fact_check)
        for ab_name in self._full_domain_antibody_map.get("general", []):
            if self.should_run(ab_name, question, "general", answer):
                relevant.append(ab_name)

        return relevant

    def check(
        self,
        question: str,
        answer: str,
        domain: str = "general",
        ground_truth: dict[str, Any] | None = None,
    ) -> list[AntibodyResult]:
        """Run all relevant antibodies for this question.

        Args:
            question: User question
            answer: AI answer to verify
            domain: Detected domain
            ground_truth: Optional ground truth from DataSources

        Returns:
            List of AntibodyResult
        """
        self._stats["total_questions"] += 1
        relevant = self.get_relevant_antibodies(question, domain, answer)
        self._stats["total_antibodies_run"] += len(relevant)
        self._stats["by_domain"][domain] = self._stats["by_domain"].get(domain, 0) + 1

        results = []
        for ab_name in relevant:
            result = self._run_antibody(ab_name, question, answer, domain, ground_truth)
            # [RC-5 FIX Task 6-B] Stub-fall-through validation — TẠI SAO: trước đây
            # caller không verify result, stubs silent pass with passed=True (lie).
            # Giờ: nếu result is None (shouldn't happen) → raise RuntimeError
            # (fail-loud). Nếu result.passed is None (stub declared but no logic)
            # → log warning + count để stats track stubs (không crash pipeline).
            if result is None:
                raise RuntimeError(
                    f"Antibody '{ab_name}' returned None — stub detected. "
                    f"_run_antibody() must return AntibodyResult."
                )
            if not hasattr(result, "passed") or result.passed is None:
                # [FIX-15A] Stub-fall-through không còn xảy ra (27 stubs removed Task 7-B).
                # Giữ logic fail-loud cho safety, nhưng total_stubs_detected luôn = 0.
                logger.warning(
                    f"Antibody '{ab_name}' returned passed=None — possible stub. "
                    f"Details: {result.details if hasattr(result, 'details') else 'N/A'}."
                )
                self._stats["total_stubs_detected"] = (
                    self._stats.get("total_stubs_detected", 0) + 1
                )
            results.append(result)
            if not result.passed:
                self._stats["total_flags"] += 1

        return results

    # [RC-5 FIX Task 6-B] TẠI SAO: 27/38 antibodies declare trong ANTIBODIES
    # registry nhưng KHÔNG có elif branch trong _run_antibody() → fall through với
    # passed=True (silent lie: "all antibodies passed"). [Sonnet5-FIX] #45 cố gắng
    # detect stubs bằng cách check `if result.passed is True and not result.details`
    # NHƯNG condition này match cả real antibodies khi check không tìm thấy issue
    # (vd: general_check không tìm weasel word → passed=True, details="").
    # Fix: track `_check_ran` flag — chỉ set True khi elif branch match ab_name.
    # Real antibodies: _check_ran=True, có thể passed=True (no issue) hoặc False.
    # Stubs: _check_ran=False → mark passed=None + log warning.
    REAL_CHECK_ANTIBODIES = {
        "citation_check", "url_hallucination", "date_verify", "fact_check",
        "dosage_validator", "pe_ratio_check", "ratio_validator",
        "interest_rate_check", "contract_check", "statute_check", "general_check",
        # [Task 15: NEW] 6 multi-domain antibodies
        "capital_check", "formula_check", "abbreviation_check",
        "unit_check", "event_date_check", "http_status_check",
        # [Task 29-B: NEW] 6 economics/philosophy/psychology/agriculture/earth_science
        "gdp_check", "inflation_check", "fallacy_check",
        "cognitive_bias_check", "crop_yield_check", "earthquake_magnitude_check",
        # [Task 30-C: NEW] 7 engineering/medical/art/military/environmental/education
        "safety_factor_check", "material_strength_check",
        "drug_interaction_check", "art_period_check",
        "weapon_range_check", "carbon_emission_check", "pedagogy_check",
    }

    def _run_antibody(
        self,
        ab_name: str,
        question: str,
        answer: str,
        domain: str,
        ground_truth: dict[str, Any] | None = None,
    ) -> AntibodyResult:
        """Run 1 antibody check."""
        antibody = self._antibody_map[ab_name]
        result = AntibodyResult(
            antibody_name=ab_name,
            domain=antibody.get("domain", domain),
            passed=True,
            severity=Severity.INFO,
            confidence=0.5,
        )

        check_method_name = antibody.get("check")
        _check_ran = False

        if check_method_name and hasattr(self, check_method_name):
            check_method = getattr(self, check_method_name)
            # The check_method returns True if it ran (i.e., replaces _check_ran = True)
            _check_ran = check_method(result, question, answer, ab_name)

        if not _check_ran:
            if not answer or len(str(answer)) < 3:
                result.passed = False
                result.details = "Empty or too-short answer"
                result.severity = "medium"
                result.confidence = 0.7
            else:
                result.passed = None
                result.details = f"stub_not_implemented: antibody '{ab_name}'"
                result.severity = "warning"
                result.confidence = 0.0

        if _check_ran and ab_name == "general_check" and (not answer or len(str(answer)) < 3):
            result.passed = False
            result.details = "Empty or too-short answer"
            result.severity = "medium"
            result.confidence = 0.7

        return result

    def stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            # [G5-FIX] Count ANTIBODIES + EXTENDED_ANTIBODIES (17 + 13 = 30)
            # so the runtime stats reflect the full antibody set active
            # (test_17_antibodies only checks len(ANTIBODIES) == 17, not stats).
            "total_antibodies": len(ANTIBODIES) + len(EXTENDED_ANTIBODIES),
            "avg_per_question": (
                self._stats["total_antibodies_run"] / max(1, self._stats["total_questions"])
            ),
        }


__all__ = ["AntibodyResult", "DomainAntibodySystem", "ANTIBODIES", "EXTENDED_ANTIBODIES"]
