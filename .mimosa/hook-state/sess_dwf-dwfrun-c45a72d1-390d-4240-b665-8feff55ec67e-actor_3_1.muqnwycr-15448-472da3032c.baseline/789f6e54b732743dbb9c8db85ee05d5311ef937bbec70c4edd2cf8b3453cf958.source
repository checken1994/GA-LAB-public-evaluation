"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 MedicalDataSource — Y tế & Sức khỏe
Bao gồm: bệnh常见, thuốc, cơ thể người, chỉ số sức khỏe, vaccine.
Fallback: LiveKnowledgeFetcher (Wikipedia + MedlinePlus).
"""
import logging
import os
import re
import urllib.parse
import urllib.request
from typing import Any

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.interfaces.data_source import IDataSource
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)

# [AUDIT-20260909 SSRF-S1] pmid từ response NCBI (external data) PHẢI là
# digits — chặn trước khi ghép vào URL efetch.
_PMID_RE = re.compile(r"^\d{1,10}$")


def build_ncbi_efetch_pubmed_url(pmids: list) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — mỗi pmid PHẢI fullmatch
    ^\\d{1,10}$; input xấu → ValueError TRƯỚC KHI fetch. Host cố định
    eutils.ncbi.nlm.nih.gov."""
    ids = [str(p or "").strip() for p in (pmids or [])]
    if not ids:
        raise ValueError("empty_pmid_list")
    for pid in ids:
        if not _PMID_RE.fullmatch(pid):
            raise ValueError(f"invalid_pmid:{pid[:32]!r}")
    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={','.join(ids)}"
        f"&rettype=abstract&retmode=text"
    )


# [V104.31 #2] Min key length for fuzzy token-boundary matching
_MIN_FUZZY_KEY_LEN = 4


def _token_boundary_match(key: str, entity_lower: str) -> bool:
    """[V104.31 #2] Word-boundary match — was: substring 'in' matched 'insulin'."""
    if not key or not entity_lower:
        return False
    if key == entity_lower:
        return True
    if len(key) < _MIN_FUZZY_KEY_LEN:
        return False
    pattern = r'(?<![\wÀ-ỹ])' + re.escape(key) + r'(?![\wÀ-ỹ])'
    if re.search(pattern, entity_lower):
        return True
    if len(entity_lower) >= _MIN_FUZZY_KEY_LEN:
        pattern_rev = r'(?<![\wÀ-ỹ])' + re.escape(entity_lower) + r'(?![\wÀ-ỹ])'
        if re.search(pattern_rev, key):
            return True
    return False


class MedicalDataSource(IDataSource):
    """Data source cho Y tế & Sức khỏe."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        # [V104.31 #9] Source date + low confidence for static medical data
        self._source_date = "2024-06"
        self._static_confidence = 0.55
        # [V5.8-API] PubMed API key (NCBI E-utilities) — available in .env
        self._pubmed_api_key = os.environ.get("PUBMED_API_KEY", "").strip()
        self._ncbi_api_key = os.environ.get("NCBI_API_KEY", "").strip() or self._pubmed_api_key

        # Bệnh thường gặp
        self._diseases = {
            'cảm lạnh': {'en': 'Common cold', 'cause': 'Virus (rhinovirus)', 'duration': '7-10 days',
                         'symptoms': ['sổ mũi', 'hắt hơi', 'đau họng', 'ho']},
            'cảm cúm': {'en': 'Flu', 'cause': 'Influenza virus', 'duration': '5-7 days',
                        'symptoms': ['sốt cao', 'đau cơ', 'mệt mỏi', 'ho']},
            'viêm phổi': {'en': 'Pneumonia', 'cause': 'Vi khuẩn/virus', 'duration': '2-3 weeks',
                          'symptoms': ['sốt', 'ho có đờm', 'khó thở', 'đau ngực']},
            'tiểu đường': {'en': 'Diabetes', 'cause': 'Insulin deficiency/resistance',
                           'types': ['Type 1', 'Type 2', 'Gestational'],
                           'symptoms': ['khát nước', 'đi tiểu nhiều', 'mệt mỏi', 'giảm cân']},
            'huyết áp cao': {'en': 'Hypertension', 'cause': 'Multiple factors',
                             'threshold': '≥140/90 mmHg',
                             'symptoms': ['đầu đau', 'chóng mặt', 'mệt mỏi']},
            'tim mạch': {'en': 'Cardiovascular disease', 'cause': 'Multiple',
                         'symptoms': ['đau ngực', 'khó thở', 'mệt mỏi']},
            'ung thư': {'en': 'Cancer', 'cause': 'Đột biến gen',
                        'types': ['phổi', 'vú', 'dạ dày', 'gan', 'da']},
            'sốt xuất huyết': {'en': 'Dengue fever', 'cause': 'Dengue virus (muỗi Aedes)',
                               'duration': '7-10 days',
                               'symptoms': ['sốt cao', 'đau đầu', 'đau cơ', 'xuất huyết']},
            'viêm gan': {'en': 'Hepatitis', 'cause': 'Virus (A, B, C)',
                         'types': ['A', 'B', 'C', 'D', 'E'],
                         'symptoms': ['vàng da', 'mệt mỏi', 'đau bụng']},
            'sởi': {'en': 'Measles', 'cause': 'Measles virus',
                    'symptoms': ['sốt', 'phát ban', 'ho', 'viêm mắt']},
            'covid-19': {'en': 'COVID-19', 'cause': 'SARS-CoV-2',
                         'symptoms': ['sốt', 'ho', 'mất vị giác', 'mệt mỏi']},
            'thủy đậu': {'en': 'Chickenpox', 'cause': 'Varicella-zoster virus',
                         'symptoms': ['phát ban ngứa', 'sốt nhẹ']},
            'quai bị': {'en': 'Mumps', 'cause': 'Mumps virus',
                        'symptoms': ['sưng tuyến nước bọt', 'sốt']},
        }

        # Thuốc phổ biến
        self._medicines = {
            'paracetamol': {'use': 'Giảm đau, hạ sốt', 'dose': '500mg người lớn, 4h/lần',
                            'max_daily': '4000mg', 'side_effects': ['nếu quá liều: tổn thương gan']},
            'acetaminophen': {'use': 'Giảm đau, hạ sốt (tên khác của paracetamol)',
                              'dose': '500mg người lớn'},
            'ibuprofen': {'use': 'Giảm đau, kháng viêm', 'dose': '200-400mg, 6h/lần',
                          'side_effects': ['đau dạ dày']},
            'aspirin': {'use': 'Giảm đau, chống viêm, chống huyết khối',
                        'dose': '81mg (heart), 325mg (pain)'},
            'amoxicillin': {'use': 'Kháng sinh (vi khuẩn)', 'dose': '500mg, 8h/lần',
                            'note': 'Cần đơn thuốc'},
            'metformin': {'use': 'Tiểu đường Type 2', 'dose': '500-2000mg/ngày'},
            'omeprazole': {'use': 'Giảm axit dạ dày', 'dose': '20-40mg/ngày'},
            'loratadine': {'use': 'Kháng histamin (dị ứng)', 'dose': '10mg/ngày'},
            'vitamin c': {'use': 'Bổ sung vitamin C', 'dose': '500-1000mg/ngày',
                          'note': 'Tan trong nước'},
            'vitamin d': {'use': 'Bổ sung vitamin D', 'dose': '600-800 IU/ngày',
                          'note': 'Tan trong dầu'},
            'insulin': {'use': 'Tiểu đường Type 1', 'dose': 'Theo đơn'},
            'penicillin': {'use': 'Kháng sinh', 'dose': 'Theo đơn'},
        }

        # Chỉ số sức khỏe
        self._vitals = {
            'nhịp tim lúc nghỉ': {'normal': '60-100 bpm', 'unit': 'bpm'},
            'nhiệt độ cơ thể': {'normal': '36.1-37.2°C', 'unit': '°C'},
            'huyết áp bình thường': {'normal': '<120/80 mmHg', 'unit': 'mmHg'},
            'huyết áp cao': {'threshold': '≥140/90 mmHg', 'unit': 'mmHg'},
            'spo2': {'normal': '95-100%', 'unit': '%'},
            'đường huyết lúc đói': {'normal': '70-99 mg/dL', 'unit': 'mg/dL'},
            'đường huyết sau ăn': {'normal': '<140 mg/dL (2h)', 'unit': 'mg/dL'},
            'cholesterol tổng': {'normal': '<200 mg/dL', 'unit': 'mg/dL'},
            'ldl': {'normal': '<100 mg/dL', 'unit': 'mg/dL'},
            'hdl': {'normal': '>40 mg/dL (nam), >50 (nữ)', 'unit': 'mg/dL'},
            'bmi bình thường': {'range': '18.5-24.9', 'unit': 'kg/m²'},
            'bmi thiếu cân': {'range': '<18.5', 'unit': 'kg/m²'},
            'bmi thừa cân': {'range': '25-29.9', 'unit': 'kg/m²'},
            'bmi béo phì': {'range': '≥30', 'unit': 'kg/m²'},
        }

        # Cơ thể người
        self._body = {
            'số xương': 206,
            'số cơ': 600,
            'số nhiễm sắc thể': 46,
            'số thận': 2,
            'số phổi': 2,
            'số tim': 1,
            'số gan': 1,
            'số dạ dày': 1,
            'số não': 1,
            'số tế bào thần kinh': 86000000000,  # neurons
            'lượng máu': 5000,  # ml
            'nhiệt độ cơ thể bình thường': 37.0,  # °C
            'nhịp tim bình thường': 72,  # bpm
            'huyết áp bình thường': '120/80',
            'tuổi thọ trung bình thế giới': 73,  # years
        }

        # Vaccine
        self._vaccines = {
            'covid-19': {'type': 'mRNA/Virus vector', 'doses': '2 + booster',
                         'effectiveness': '85-95%'},
            'vaccine viêm gan B': {'type': 'Recombinant', 'doses': '3',
                                   'effectiveness': '95%+'},
            'bcg': {'type': 'Live attenuated', 'use': 'Lao',
                    'doses': '1 lúc sinh'},
            'sởi': {'type': 'Live attenuated', 'doses': '2 (MMR)'},
            'bại liệt': {'type': 'IPV/OPV', 'doses': '4'},
            'uốn ván': {'type': 'Toxoid', 'doses': '5 (DPT) + booster'},
        }

    @property
    def name(self) -> str:
        return "MedicalDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        # [FIX-CRIT-46 BUG 6] TẠI SAO: was 604800 (7 days) → stale drug doses
        # served for a full week. Medical knowledge (drug doses, contraindications,
        # vaccine schedules, clinical guidelines) changes on a faster cadence;
        # serving a 7-day-stale paracetamol max_daily dose is medically unsafe.
        # Fix: 86400 (24 hours) — same cadence as MedlinePlus / FDA drug-label
        # updates. Aligns with domain_registry.py medical entry.
        return 86400  # 24 hours

    def get_supported_intents(self) -> list[str]:
        return ['medical_disease', 'medical_medicine', 'medical_vital',
                'medical_body', 'medical_vaccine', 'medical_info',
                # [FIX-CRIT-46 BUG 7] medical_dose_advice — user asking "what
                # dose should I take?" → SCP MUST abstain per Constitution
                # ("abstain rather than fabricate"). Returning a stored dose
                # as evidence would be practicing medicine without a license.
                'medical_dose_advice']

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._diseases, self._medicines, self._vitals,
                          self._body, self._vaccines):
                if entity_lower in table:
                    return True
                for key in table:
                    if _token_boundary_match(key, entity_lower):  # [V104.31 #2]
                        return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        if not entity:
            return None
        entity_lower = entity.lower().strip()

        # [FIX-CRIT-46 BUG 7] TẠI SAO: previously NO abstain path — the fetch()
        # method returned a stored dose (e.g. "paracetamol 500mg người lớn, 4h/lần")
        # as evidence whenever a user asked "what dose should I take?". That is
        # practicing medicine without a license and violates the SCP Constitution
        # ("abstain rather than fabricate"). The static dose in the local DB is
        # a reference value, NOT personalized medical advice — patient weight,
        # age, liver function, comorbidities, concurrent medications all matter.
        # Fix: if the caller classified the question intent as
        # `medical_dose_advice` (user asking "what dose should I take?",
        # "liều dùng bao nhiêu?", "how many mg should I take?"), abstain —
        # return None value with abstain=True and a reason. Downstream
        # (judge.py / engine.py) sees value=None and propagates UNKNOWN/
        # abstain rather than serving the stored dose as an answer.
        if intent == 'medical_dose_advice':
            return {
                'value': None,
                'abstain': True,
                'reason': (
                    "SCP cannot provide medical dosage advice. "
                    "Consult a healthcare professional."
                ),
                'source': 'MedicalDataSource (abstain policy)',
                'metadata': {
                    'intent': 'medical_dose_advice',
                    'abstain': True,
                    'disclaimer': (
                        "Dose depends on patient weight, age, liver/kidney "
                        "function, comorbidities, and concurrent medications. "
                        "SCP's static DB contains reference values, not "
                        "personalized medical advice."
                    ),
                },
                'confidence': 0.0,
            }

        # [V104.31 #9] Common metadata: source_date + disclaimer for static DB
        disclaimer = (
            "Dữ liệu y tế tĩnh — chỉ tham khảo. Không thay thế tư vấn bác sĩ. "
            "Có thể lỗi thời so với hướng dẫn lâm sàng mới nhất."
        )
        common_meta = {
            'source_date': self._source_date,
            'static_confidence': self._static_confidence,
            'disclaimer': disclaimer,
        }

        # Diseases
        if entity_lower in self._diseases:
            data = self._diseases[entity_lower]
            return {
                'value': data.get('en', ''),
                'source': 'Local Medical Database',
                'metadata': {**data, **common_meta},
                'confidence': self._static_confidence,
            }
        for key, data in self._diseases.items():
            if _token_boundary_match(key, entity_lower):  # [V104.31 #2]
                return {
                    'value': data.get('en', ''),
                    'source': 'Local Medical Database',
                    'metadata': {**data, **common_meta},
                    'confidence': self._static_confidence,
                }

        # Medicines
        if entity_lower in self._medicines:
            data = self._medicines[entity_lower]
            return {
                'value': data.get('use', ''),
                'source': 'Local Medical Database',
                'metadata': {**data, **common_meta},
                'confidence': self._static_confidence,
            }
        for key, data in self._medicines.items():
            if _token_boundary_match(key, entity_lower):  # [V104.31 #2]
                return {
                    'value': data.get('use', ''),
                    'source': 'Local Medical Database',
                    'metadata': {**data, **common_meta},
                    'confidence': self._static_confidence,
                }

        # Vitals
        if entity_lower in self._vitals:
            data = self._vitals[entity_lower]
            return {
                'value': data.get('normal', data.get('threshold', data.get('range', ''))),
                'source': 'Local Medical Database',
                'metadata': {**data, **common_meta},
                'confidence': self._static_confidence,
            }
        for key, data in self._vitals.items():
            if _token_boundary_match(key, entity_lower):  # [V104.31 #2]
                return {
                    'value': data.get('normal', data.get('threshold', data.get('range', ''))),
                    'source': 'Local Medical Database',
                    'metadata': {**data, **common_meta},
                    'confidence': self._static_confidence,
                }

        # Body
        if entity_lower in self._body:
            return {
                'value': self._body[entity_lower],
                'source': 'Local Medical Database',
                'metadata': {'fact': entity_lower, 'value': self._body[entity_lower], **common_meta},
                'confidence': self._static_confidence,
            }
        for key, val in self._body.items():
            if _token_boundary_match(key, entity_lower):  # [V104.31 #2]
                return {
                    'value': val,
                    'source': 'Local Medical Database',
                    'metadata': {'fact': key, 'value': val, **common_meta},
                    'confidence': self._static_confidence,
                }

        # Vaccines
        if entity_lower in self._vaccines:
            data = self._vaccines[entity_lower]
            return {
                'value': data.get('type', ''),
                'source': 'Local Medical Database',
                'metadata': {**data, **common_meta},
                'confidence': self._static_confidence,
            }

        # [V5.8-API] Try PubMed (NCBI E-utilities) as fallback for medical info.
        # Local DB is preferred for known Vietnamese terms (keeps existing tests
        # passing + keeps source_date/disclaimer/static_confidence contract).
        # PubMed is tried ONLY when local DB has no match — gives real abstracts
        # for drug/disease queries outside the static DB's coverage.
        pubmed_result = self._fetch_from_pubmed(entity)
        if pubmed_result:
            return pubmed_result

        return None

    # [V5.8-API] PubMed E-utilities integration
    def _fetch_from_pubmed(self, entity: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Fetch medical info from PubMed via NCBI E-utilities.
        Step 1: esearch.fcgi (JSON) → list of PMIDs
        Step 2: efetch.fcgi (text) → abstracts for top PMIDs
        Returns dict with value/source/metadata/confidence, or None on failure.
        """
        if not entity or not entity.strip():
            return None
        term = entity.strip()
        # Build esearch URL (JSON response — handled by fetch_with_retry)
        api_key_param = f"&api_key={self._pubmed_api_key}" if self._pubmed_api_key else ""
        esearch_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={urllib.parse.quote(term, safe='')}"
            f"&retmode=json&retmax=3{api_key_param}"
        )
        try:
            esearch_data = fetch_with_retry(esearch_url, headers={"User-Agent": "SCP/1.0"}, timeout=5)
            if not esearch_data:
                return None
            id_list = esearch_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return None
        except Exception as e:
            logger.warning(f"[V5.8-API] PubMed esearch failed for '{term}': {e}", exc_info=True)
            return None

        # Fetch abstracts via efetch (text/plain response)
        pmids = id_list[:3]
        # [AUDIT-20260909 SSRF-S1] pmids (external data) được validate bằng
        # regex trong builder; input xấu → ValueError TRƯỚC KHI fetch.
        efetch_url = build_ncbi_efetch_pubmed_url(pmids) + api_key_param
        try:
            req = urllib.request.Request(
                efetch_url, headers={"User-Agent": "SCP/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=8) as resp:
                if getattr(resp, "status", 200) != 200:
                    return None
                abstract_text = resp.read().decode("utf-8", errors="replace").strip()
            if not abstract_text:
                return None
            if len(abstract_text) < 20:
                return None
            # Truncate very long abstracts to a sensible size
            if len(abstract_text) > 2000:
                abstract_text = abstract_text[:2000] + "... [truncated]"
            return {
                'value': abstract_text,
                'source': 'PubMed API (NCBI E-utilities)',
                'metadata': {
                    'pmids': pmids,
                    'query_term': term,
                    'api': 'pubmed_esearch+efetch',
                    'disclaimer': (
                        'PubMed abstracts are reference material, not medical advice. '
                        'Consult a healthcare professional for diagnosis/treatment.'
                    ),
                },
                'confidence': 0.85,
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] PubMed efetch failed for PMIDs {pmids}: {e}", exc_info=True)
            return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
