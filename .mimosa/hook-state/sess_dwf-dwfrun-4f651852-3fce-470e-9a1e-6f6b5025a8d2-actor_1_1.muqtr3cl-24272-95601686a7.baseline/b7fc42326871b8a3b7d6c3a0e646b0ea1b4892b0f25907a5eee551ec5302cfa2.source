"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 ArtsDataSource — Nghệ thuật & Thiết kế
Bao gồm: painters, art movements, music composers, films, design principles.
Fallback: LiveKnowledgeFetcher (Wikipedia).
"""
import logging
from typing import Any

from scp.data_sources._matching import _token_boundary_match
from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)
# [V104.32 #10] word-boundary matching for short keys


class ArtsDataSource(IDataSource):
    """Data source cho Nghệ thuật & Thiết kế."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Famous painters
        self._painters = {
            'leonardo da vinci': {'born': 1452, 'died': 1519, 'country': 'Italy',
                                  'movement': 'Renaissance',
                                  'works': ['Mona Lisa', 'The Last Supper']},
            'michelangelo': {'born': 1475, 'died': 1564, 'country': 'Italy',
                             'movement': 'Renaissance',
                             'works': ['David', 'Sistine Chapel ceiling']},
            'vincent van gogh': {'born': 1853, 'died': 1890, 'country': 'Netherlands',
                                 'movement': 'Post-Impressionism',
                                 'works': ['The Starry Night', 'Sunflowers']},
            'pablo picasso': {'born': 1881, 'died': 1973, 'country': 'Spain',
                              'movement': 'Cubism',
                              'works': ['Les Demoiselles d\'Avignon', 'Guernica']},
            'claude monet': {'born': 1840, 'died': 1926, 'country': 'France',
                             'movement': 'Impressionism',
                             'works': ['Water Lilies', 'Impression, Sunrise']},
            'salvador dali': {'born': 1904, 'died': 1989, 'country': 'Spain',
                              'movement': 'Surrealism',
                              'works': ['The Persistence of Memory']},
            'rembrandt': {'born': 1606, 'died': 1669, 'country': 'Netherlands',
                          'movement': 'Baroque',
                          'works': ['The Night Watch']},
            'frida kahlo': {'born': 1907, 'died': 1954, 'country': 'Mexico',
                            'movement': 'Surrealism',
                            'works': ['The Two Fridas']},
            'raphael': {'born': 1483, 'died': 1520, 'country': 'Italy',
                        'movement': 'Renaissance',
                        'works': ['The School of Athens']},
            'andy warhol': {'born': 1928, 'died': 1987, 'country': 'USA',
                            'movement': 'Pop Art',
                            'works': ['Campbell\'s Soup Cans', 'Marilyn Diptych']},
        }

        # Art movements
        self._movements = {
            'phục hưng': {'vi': 'Renaissance', 'period': '14th-17th century',
                          'origin': 'Italy', 'desc': 'Phục hưng nghệ thuật và học thuật'},
            'renaissance': {'vi': 'Phục hưng', 'period': '14th-17th century',
                            'origin': 'Italy'},
            'ấn tượng': {'vi': 'Impressionism', 'period': '1860s-1890s',
                         'origin': 'France', 'desc': 'Tranh ngoài trời, ánh sáng tự nhiên'},
            'impressionism': {'vi': 'Ấn tượng', 'period': '1860s-1890s',
                              'origin': 'France'},
            'lập thể': {'vi': 'Cubism', 'period': '1907-1920s',
                        'origin': 'France', 'desc': 'Hình học phi thực tế'},
            'cubism': {'vi': 'Lập thể', 'period': '1907-1920s', 'origin': 'France'},
            'siêu thực': {'vi': 'Surrealism', 'period': '1920s+',
                          'origin': 'France', 'desc': 'Tranh giấc mơ, phi logic'},
            'surrealism': {'vi': 'Siêu thực', 'period': '1920s+', 'origin': 'France'},
            'pop art': {'vi': 'Pop Art', 'period': '1950s-1960s',
                        'origin': 'UK/USA', 'desc': 'Văn hóa đại chúng'},
            'baroque': {'vi': 'Baroque', 'period': '1600-1750',
                        'origin': 'Italy', 'desc': 'Kịch tính, tương phản sáng tối'},
            'hiện đại': {'vi': 'Modernism', 'period': '1860s-1970s',
                         'origin': 'Europe', 'desc': 'Phá vỡ truyền thống'},
            'đương đại': {'vi': 'Contemporary', 'period': '1970s+',
                          'desc': 'Nghệ thuật hiện nay'},
        }

        # Music composers
        self._composers = {
            'beethoven': {'born': 1770, 'died': 1827, 'country': 'Germany',
                          'period': 'Classical/Romantic',
                          'works': ['Symphony No. 9', 'Für Elise', 'Moonlight Sonata']},
            'mozart': {'born': 1756, 'died': 1791, 'country': 'Austria',
                       'period': 'Classical',
                       'works': ['The Magic Flute', 'Eine kleine Nachtmusik', 'Requiem']},
            'bach': {'born': 1685, 'died': 1750, 'country': 'Germany',
                     'period': 'Baroque',
                     'works': ['Brandenburg Concertos', 'The Well-Tempered Clavier']},
            'chopin': {'born': 1810, 'died': 1849, 'country': 'Poland',
                       'period': 'Romantic',
                       'works': ['Nocturnes', 'Revolutionary Étude']},
            'tchaikovsky': {'born': 1840, 'died': 1893, 'country': 'Russia',
                            'period': 'Romantic',
                            'works': ['Swan Lake', 'The Nutcracker', '1812 Overture']},
            'vivaldi': {'born': 1678, 'died': 1741, 'country': 'Italy',
                        'period': 'Baroque',
                        'works': ['The Four Seasons']},
            'trịnh công sơn': {'born': 1939, 'died': 2001, 'country': 'Vietnam',
                               'period': 'Modern',
                               'works': ['Diễm Xưa', 'Cát Bụi', 'Ru Đời']},
            'văn cao': {'born': 1923, 'died': 1995, 'country': 'Vietnam',
                        'period': 'Modern',
                        'works': ['Tiến Quân Ca (Quốc ca VN)', 'Thành Phố Mùa Xuân']},
        }

        # Films & cinema
        self._films = {
            'avatar': {'year': 2009, 'director': 'James Cameron',
                       'box_office': 2923000000, 'note': 'Phim doanh thu cao nhất 1 thời gian'},
            'avengers endgame': {'year': 2019, 'director': 'Anthony & Joe Russo',
                                 'box_office': 2799000000},
            'titanic': {'year': 1997, 'director': 'James Cameron',
                        'box_office': 2200000000},
            'star wars': {'year': 1977, 'director': 'George Lucas',
                          'box_office': 775000000},
            'the godfather': {'year': 1972, 'director': 'Francis Ford Coppola'},
            'parasite': {'year': 2019, 'director': 'Bong Joon-ho',
                         'country': 'South Korea', 'note': 'Oscar Best Picture 2020'},
            'inception': {'year': 2010, 'director': 'Christopher Nolan'},
            'the matrix': {'year': 1999, 'directors': 'Wachowskis'},
        }

        # Design principles
        self._design = {
            'ux': {'vi': 'User Experience', 'desc': 'Trải nghiệm người dùng',
                   'principles': ['usability', 'accessibility', 'user research']},
            'ui': {'vi': 'User Interface', 'desc': 'Giao diện người dùng',
                   'principles': ['hierarchy', 'consistency', 'feedback']},
            'wireframe': {'vi': 'Khung dây', 'desc': 'Sơ đồ cấu trúc giao diện'},
            'prototype': {'vi': 'Nguyên mẫu', 'desc': 'Bản demo tương tác'},
            'figma': {'vi': 'Công cụ thiết kế', 'desc': 'Design collaboration tool',
                      'year': 2016},
            'adobe xd': {'vi': 'Công cụ thiết kế', 'desc': 'Adobe Experience Design',
                         'year': 2016},
            'sketch': {'vi': 'Công cụ thiết kế', 'desc': 'Mac-only design tool',
                       'year': 2010},
            'canva': {'vi': 'Công cụ thiết kế', 'desc': 'Online design platform',
                      'year': 2013},
        }

    @property
    def name(self) -> str:
        return "ArtsDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 604800

    def get_supported_intents(self) -> list[str]:
        return ['arts_painter', 'arts_movement', 'arts_composer',
                'arts_film', 'arts_design', 'arts_info']

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._painters, self._movements, self._composers,
                          self._films, self._design):
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
            ('painter', self._painters),
            ('movement', self._movements),
            ('composer', self._composers),
            ('film', self._films),
            ('design', self._design),
        ]:
            if entity_lower in table:
                data = table[entity_lower]
                return {
                    'value': str(data.get('desc', data.get('vi', data.get('year', '')))),
                    'source': 'Local Arts Database',
                    'metadata': {**data, 'category': table_name}
                }
            for key, data in table.items():
                if _token_boundary_match(key, entity_lower):
                    return {
                        'value': str(data.get('desc', data.get('vi', data.get('year', '')))),
                        'source': 'Local Arts Database',
                        'metadata': {**data, 'category': table_name, 'matched_key': key}
                    }

        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
