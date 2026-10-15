"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 LegalDataSource — Luật & Hành chính
Bao gồm: Vietnamese law basics, international law, rights, contracts.
Fallback: LiveKnowledgeFetcher (Wikipedia).
"""
import logging
import os
from typing import Any

from scp.core.api_utils import fetch_with_retry  # [V5.8-API]
from scp.data_sources._matching import _token_boundary_match
from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)
# [V104.32 #12] word-boundary matching for short keys


class LegalDataSource(IDataSource):
    """Data source cho Luật & Hành chính."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        # [V5.8-API] Case.law API key (optional — anonymous access allowed,
        # but rate-limited; registration at https://case.law/api/)
        self._case_law_api_key = os.environ.get("CASE_LAW_API_KEY", "").strip()

        # Vietnamese legal documents
        self._vn_laws = {
            'hiến pháp 2013': {'year': 2013, 'articles': 120,
                               'desc': 'Hiến pháp nước CHXHCN Việt Nam 2013'},
            'hiến pháp 1946': {'year': 1946, 'articles': 70,
                               'desc': 'Hiến pháp đầu tiên nước Việt Nam Dân chủ Cộng hòa'},
            'hiến pháp 1959': {'year': 1959, 'articles': 112,
                               'desc': 'Hiến pháp Việt Nam Dân chủ Cộng hòa 1959'},
            'hiến pháp 1980': {'year': 1980, 'articles': 147,
                               'desc': 'Hiến pháp CHXHCN Việt Nam 1980'},
            'bộ luật dân sự 2015': {'year': 2015, 'articles': 689,
                                    'desc': 'Bộ luật Dân sự số 91/2015/QH13'},
            'bộ luật hình sự 2015': {'year': 2015, 'articles': 426,
                                     'desc': 'Bộ luật Hình sự số 100/2015/QH13 (sửa đổi 2017)'},
            'bộ luật lao động 2019': {'year': 2019, 'articles': 220,
                                      'desc': 'Bộ luật Lao động số 45/2019/QH14'},
            'luật đất đai 2024': {'year': 2024, 'articles': 260,
                                  'desc': 'Luật Đất đai số 31/2024/QH15'},
            'luật doanh nghiệp 2020': {'year': 2020, 'articles': 218,
                                       'desc': 'Luật Doanh nghiệp số 59/2020/QH14'},
            'luật thuế thu nhập doanh nghiệp': {'year': 2013,
                                                'desc': 'Thuế suất 20% (mặc định)'},
            'luật thuế giá trị gia tăng': {'year': 2008,
                                           'desc': 'VAT 10% (mặc định), 0% hoặc 5% cho một số hàng hóa'},
            'luật bảo vệ môi trường 2020': {'year': 2020,
                                            'desc': 'Luật số 72/2020/QH14'},
        }

        # International law concepts
        self._intl_law = {
            'nhân quyền': {'vi': 'Human Rights',
                           'docs': ['UDHR 1948', 'ICCPR 1966', 'ICESCR 1966'],
                           'desc': 'Quyền cơ bản của con người'},
            'tuyên ngôn quốc tế nhân quyền': {'year': 1948,
                                              'org': 'UN', 'articles': 30},
            'công ước vienna về hợp đồng': {'year': 1969,
                                            'desc': 'Vienna Convention on Law of Treaties'},
            'công ước quốc tế về quyền trẻ em': {'year': 1989,
                                                'org': 'UN', 'articles': 54},
            'quyền sở hữu trí tuệ': {'docs': ['WIPO', 'TRIPS', 'Berne Convention'],
                                     'desc': 'Bảo vệ sáng tạo trí tuệ'},
            'wto': {'vi': 'Tổ chức Thương mại Thế giới',
                    'year': 1995, 'members': 164,
                    'desc': 'World Trade Organization'},
            'who': {'vi': 'Tổ chức Y tế Thế giới',
                    'year': 1948, 'members': 194,
                    'desc': 'World Health Organization'},
            'ili': {'vi': 'Luật quốc tế',
                    'desc': 'International Law - quan hệ giữa quốc gia'},
        }

        # Rights & freedoms
        self._rights = {
            'quyền sống': {'vi': 'Right to life', 'source': 'UDHR Art 3'},
            'quyền tự do': {'vi': 'Right to liberty', 'source': 'UDHR Art 3'},
            'quyền bình đẳng': {'vi': 'Equality before law', 'source': 'UDHR Art 7'},
            'quyền tự do ngôn luận': {'vi': 'Freedom of speech', 'source': 'UDHR Art 19'},
            'quyền tự do tôn giáo': {'vi': 'Freedom of religion', 'source': 'UDHR Art 18'},
            'quyền tự do hội họp': {'vi': 'Freedom of assembly', 'source': 'UDHR Art 20'},
            'quyền bầu cử': {'vi': 'Right to vote', 'source': 'UDHR Art 21'},
            'quyền lao động': {'vi': 'Right to work', 'source': 'UDHR Art 23'},
            'quyền giáo dục': {'vi': 'Right to education', 'source': 'UDHR Art 26'},
            'quyền sở hữu': {'vi': 'Right to property', 'source': 'UDHR Art 17'},
        }

        # Contract law basics
        self._contract = {
            'hợp đồng dân sự': {'desc': 'Thỏa thuận giữa các bên về xác định, thay đổi, chấm dứt quyền/nghĩa vụ dân sự',
                                'source': 'BLDS 2015'},
            'hợp đồng kinh tế': {'desc': 'Hợp đồng giữa doanh nghiệp với doanh nghiệp',
                                 'source': 'BLDS 2015'},
            'hợp đồng lao động': {'desc': 'Thỏa thuận giữa người lao động và người sử dụng lao động',
                                  'source': 'BLLĐ 2019'},
            'hợp đồng mua bán': {'desc': 'Chuyển quyền sở hữu tài sản',
                                 'source': 'BLDS 2015'},
            'hợp đồng vay': {'desc': 'Một bên giao tài sản, bên kia phải trả lại',
                             'source': 'BLDS 2015'},
            'hợp đồng thuê': {'desc': 'Một bên cho thuê tài sản, bên kia trả tiền thuê',
                              'source': 'BLDS 2015'},
        }

        # Government structure VN
        self._vn_govt = {
            'quốc hội': {'vi': 'National Assembly',
                         'desc': 'Cơ quan quyền lực nhà nước cao nhất VN',
                         'members': 500, 'term': 5},
            'chủ tịch nước': {'vi': 'President',
                              'desc': 'Người đứng đầu nhà nước',
                              'elected_by': 'Quốc hội', 'term': 5},
            'chính phủ': {'vi': 'Government',
                          'desc': 'Cơ quan hành chính nhà nước cao nhất',
                          'head': 'Thủ tướng'},
            'thủ tướng': {'vi': 'Prime Minister',
                          'desc': 'Người đứng đầu Chính phủ',
                          'elected_by': 'Quốc hội', 'term': 5},
            'tòa án nhân dân tối cao': {'vi': 'Supreme People\'s Court',
                                        'desc': 'Cơ quan xét xử cao nhất VN'},
            'viện kiểm sát nhân dân tối cao': {'vi': 'Supreme People\'s Procuracy',
                                               'desc': 'Cơ quan công tố cao nhất VN'},
        }

    @property
    def name(self) -> str:
        return "LegalDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 604800

    def get_supported_intents(self) -> list[str]:
        return ['legal_vn_law', 'legal_intl', 'legal_rights',
                'legal_contract', 'legal_govt', 'legal_info']

    # [V89 FIX] English→Vietnamese alias map for cross-language matching
    _EN_ALIASES = {
        'constitution': 'hiến pháp',
        'civil code': 'bộ luật dân sự',
        'criminal code': 'bộ luật hình sự',
        'labor law': 'bộ luật lao động',
        'land law': 'luật đất đai',
        'enterprise law': 'luật doanh nghiệp',
    }

    def _resolve_alias(self, entity: str) -> str:
        """Convert English legal terms to Vietnamese DB keys."""
        # [FIX #5] TẠI SAO: was `import re as _re` (creating name `_re`) but next
        # line called `re.search(...)` -> NameError on every legal question with a
        # year (e.g. "civil code 2020"). Swallowed by outer except -> silent fail.
        # Reality > Model: verified `import re` at top of file (line 14) works.
        import re
        e = entity.lower().strip()
        for en, vi in self._EN_ALIASES.items():
            if en in e:
                # Try with year if present
                year_m = re.search(r'(20\d{2}|19\d{2})', e)
                if year_m:
                    key = f"{vi} {year_m.group(1)}"
                    if key in self._vn_laws:
                        return key
                # Try without year
                for k in self._vn_laws:
                    if vi in k:
                        return k
        return entity

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._vn_laws, self._intl_law, self._rights,
                          self._contract, self._vn_govt):
                if entity_lower in table:
                    return True
                for key in table:
                    if _token_boundary_match(key, entity_lower):
                        return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        if not entity:
            return None
        entity_lower = entity.lower().strip()

        for table_name, table in [
            ('vn_law', self._vn_laws),
            ('intl_law', self._intl_law),
            ('rights', self._rights),
            ('contract', self._contract),
            ('govt', self._vn_govt),
        ]:
            if entity_lower in table:
                data = table[entity_lower]
                return {
                    'value': str(data.get('desc', data.get('vi', data.get('year', '')))),
                    'source': 'Local Legal Database',
                    'metadata': {**data, 'category': table_name}
                }
            for key, data in table.items():
                if _token_boundary_match(key, entity_lower):
                    return {
                        'value': str(data.get('desc', data.get('vi', data.get('year', '')))),
                        'source': 'Local Legal Database',
                        'metadata': {**data, 'category': table_name, 'matched_key': key}
                    }

        # [V5.8-API] Local DB miss → try Case.law API for US case law.
        # (Vietnamese law API is not publicly available for free; the local
        #  DB remains the canonical source for VN law. Case.law covers
        #  international/US case-law lookups.)
        case_law_result = self._fetch_from_case_law(entity)
        if case_law_result:
            return case_law_result

        return None

    # [V5.8-API] Case.law (Caselaw Access Project) integration
    def _fetch_from_case_law(self, entity: str) -> dict[str, Any] | None:
        """
        [V5.8-API] Query the Caselaw Access Project API for case-law matches.
        Endpoint: https://api.case.law/v1/cases/?search={query}
        Returns dict or None.
        """
        if not entity or not entity.strip():
            return None
        from urllib.parse import quote
        term = entity.strip()
        # Skip very short queries / pure Vietnamese year-only queries
        if len(term) < 4:
            return None
        url = (
            f"https://api.case.law/v1/cases/?search={quote(term)}"
            f"&page_size=3"
        )
        headers = {"User-Agent": "SCP/1.0"}
        if self._case_law_api_key:
            headers["Authorization"] = f"Token {self._case_law_api_key}"
        try:
            data = fetch_with_retry(url, headers=headers, timeout=8)
            if not data:
                return None
            results = data.get('results', [])
            if not results:
                return None
            case_entries = []
            for c in results[:3]:
                name = c.get('name_abbreviation') or c.get('name') or ''
                citation = (c.get('citations') or [{}])[0].get('cite', '') if c.get('citations') else ''
                jurisdiction = (c.get('jurisdiction') or {}).get('name', '')
                decision_date = c.get('decision_date', '')
                parts = [name]
                if citation:
                    parts.append(citation)
                if jurisdiction:
                    parts.append(f"[{jurisdiction}]")
                if decision_date:
                    parts.append(f"({decision_date})")
                if name:
                    case_entries.append(" ".join(parts))
            if not case_entries:
                return None
            return {
                'value': "; ".join(case_entries),
                'source': 'Caselaw Access Project API',
                'metadata': {
                    'query_term': term,
                    'count': data.get('count', 0),
                    'api': 'case_law_v1',
                    'disclaimer': (
                        'US case-law results. For Vietnamese law, see local DB. '
                        'Always verify with primary legal sources.'
                    ),
                },
                'confidence': 0.7,
            }
        except Exception as e:
            logger.warning(f"[V5.8-API] Case.law API failed for '{term}': {e}", exc_info=True)
            return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
