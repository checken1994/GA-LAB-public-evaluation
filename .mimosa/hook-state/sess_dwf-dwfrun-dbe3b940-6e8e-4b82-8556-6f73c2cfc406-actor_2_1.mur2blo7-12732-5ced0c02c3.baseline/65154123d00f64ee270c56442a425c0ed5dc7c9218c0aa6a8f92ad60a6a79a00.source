"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 SportsDataSource — Thể thao & Giải trí
Bao gồm: Olympic, FIFA World Cup, athletes, sports rules.
Fallback: LiveKnowledgeFetcher (Wikipedia).
"""
import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class SportsDataSource(IDataSource):
    """Data source cho Thể thao & Giải trí."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Olympic Games
        self._olympics = {
            'tokyo 2020': {'year': 2021, 'city': 'Tokyo', 'country': 'Japan',
                           'note': 'Hoãn 1 năm do COVID-19', 'top_country': 'USA'},
            'paris 2024': {'year': 2024, 'city': 'Paris', 'country': 'France',
                           'top_country': 'USA'},
            'rio 2016': {'year': 2016, 'city': 'Rio de Janeiro', 'country': 'Brazil',
                         'top_country': 'USA'},
            'london 2012': {'year': 2012, 'city': 'London', 'country': 'UK',
                            'top_country': 'USA'},
            'beijing 2008': {'year': 2008, 'city': 'Beijing', 'country': 'China',
                             'top_country': 'China'},
            'athens 2004': {'year': 2004, 'city': 'Athens', 'country': 'Greece',
                            'top_country': 'USA'},
            'sydney 2000': {'year': 2000, 'city': 'Sydney', 'country': 'Australia',
                            'top_country': 'USA'},
            'atlanta 1996': {'year': 1996, 'city': 'Atlanta', 'country': 'USA',
                             'top_country': 'USA'},
            'barcelona 1992': {'year': 1992, 'city': 'Barcelona', 'country': 'Spain',
                               'top_country': 'Unified Team'},
            'seoul 1988': {'year': 1988, 'city': 'Seoul', 'country': 'South Korea',
                           'top_country': 'USSR'},
            'los angeles 1984': {'year': 1984, 'city': 'Los Angeles', 'country': 'USA',
                                 'top_country': 'USA'},
            'moscow 1980': {'year': 1980, 'city': 'Moscow', 'country': 'USSR',
                            'top_country': 'USSR', 'note': 'Boycott by USA'},
            #  Add "olympic YYYY" aliases
            'olympic 2024': {'year': 2024, 'city': 'Paris', 'country': 'France', 'top_country': 'USA'},
            'olympic 2020': {'year': 2021, 'city': 'Tokyo', 'country': 'Japan', 'top_country': 'USA'},
            'olympic 2016': {'year': 2016, 'city': 'Rio de Janeiro', 'country': 'Brazil', 'top_country': 'USA'},
            'olympic 2012': {'year': 2012, 'city': 'London', 'country': 'UK', 'top_country': 'USA'},
            'olympic 2008': {'year': 2008, 'city': 'Beijing', 'country': 'China', 'top_country': 'China'},
            'olympic 2004': {'year': 2004, 'city': 'Athens', 'country': 'Greece', 'top_country': 'USA'},
            'olympic 2000': {'year': 2000, 'city': 'Sydney', 'country': 'Australia', 'top_country': 'USA'},
            'olympic 1996': {'year': 1996, 'city': 'Atlanta', 'country': 'USA', 'top_country': 'USA'},
            'olympic 1992': {'year': 1992, 'city': 'Barcelona', 'country': 'Spain', 'top_country': 'Unified Team'},
            'olympic 1988': {'year': 1988, 'city': 'Seoul', 'country': 'South Korea', 'top_country': 'USSR'},
            'olympic 1984': {'year': 1984, 'city': 'Los Angeles', 'country': 'USA', 'top_country': 'USA'},
            'olympic 1980': {'year': 1980, 'city': 'Moscow', 'country': 'USSR', 'top_country': 'USSR'},
        }

        # FIFA World Cup
        self._world_cup = {
            '2022': {'host': 'Qatar', 'winner': 'Argentina', 'runner_up': 'France'},
            '2018': {'host': 'Russia', 'winner': 'France', 'runner_up': 'Croatia'},
            '2014': {'host': 'Brazil', 'winner': 'Germany', 'runner_up': 'Argentina'},
            '2010': {'host': 'South Africa', 'winner': 'Spain', 'runner_up': 'Netherlands'},
            '2006': {'host': 'Germany', 'winner': 'Italy', 'runner_up': 'France'},
            '2002': {'host': 'South Korea/Japan', 'winner': 'Brazil', 'runner_up': 'Germany'},
            '1998': {'host': 'France', 'winner': 'France', 'runner_up': 'Brazil'},
            '1994': {'host': 'USA', 'winner': 'Brazil', 'runner_up': 'Italy'},
            '1990': {'host': 'Italy', 'winner': 'West Germany', 'runner_up': 'Argentina'},
            '1986': {'host': 'Mexico', 'winner': 'Argentina', 'runner_up': 'West Germany'},
        }

        # Famous athletes
        self._athletes = {
            'lionel messi': {'sport': 'Football', 'born': 1987, 'country': 'Argentina',
                             'position': 'Forward', 'ballon_dor': 8},
            'cristiano ronaldo': {'sport': 'Football', 'born': 1985, 'country': 'Portugal',
                                  'position': 'Forward', 'ballon_dor': 5},
            'pelé': {'sport': 'Football', 'born': 1940, 'died': 2022, 'country': 'Brazil',
                     'position': 'Forward', 'world_cups': 3},
            'diego maradona': {'sport': 'Football', 'born': 1960, 'died': 2020,
                               'country': 'Argentina', 'position': 'Forward'},
            'michael jordan': {'sport': 'Basketball', 'born': 1963, 'country': 'USA',
                               'position': 'Shooting Guard', 'nba_titles': 6},
            'lebron james': {'sport': 'Basketball', 'born': 1984, 'country': 'USA',
                             'position': 'Forward', 'nba_titles': 4},
            'kobe bryant': {'sport': 'Basketball', 'born': 1978, 'died': 2020, 'country': 'USA',
                            'position': 'Shooting Guard', 'nba_titles': 5},
            'usain bolt': {'sport': 'Athletics', 'born': 1986, 'country': 'Jamaica',
                           'specialty': 'Sprint', 'world_records': '100m (9.58s), 200m (19.19s)'},
            'michael phelps': {'sport': 'Swimming', 'born': 1985, 'country': 'USA',
                               'olympic_golds': 23},
            'serena williams': {'sport': 'Tennis', 'born': 1981, 'country': 'USA',
                                'grand_slams': 23},
            'roger federer': {'sport': 'Tennis', 'born': 1981, 'country': 'Switzerland',
                              'grand_slams': 20},
            'rafael nadal': {'sport': 'Tennis', 'born': 1986, 'country': 'Spain',
                             'grand_slams': 22},
            'muhammad ali': {'sport': 'Boxing', 'born': 1942, 'died': 2016, 'country': 'USA',
                             'weight': 'Heavyweight'},
            'tiger woods': {'sport': 'Golf', 'born': 1975, 'country': 'USA',
                            'major_titles': 15},
        }

        # Sports rules - basic info
        self._sports_rules = {
            'bóng đá': {'players': 11, 'duration': '90 min (2 halves of 45)',
                        'governing_body': 'FIFA', 'origin': 'England 1863'},
            'football': {'players': 11, 'duration': '90 min',
                         'governing_body': 'FIFA', 'origin': 'England 1863'},
            'soccer': {'players': 11, 'duration': '90 min',
                       'governing_body': 'FIFA', 'origin': 'England 1863'},
            'bóng rổ': {'players': 5, 'duration': '48 min (NBA), 40 min (FIBA)',
                        'governing_body': 'FIBA', 'origin': 'USA 1891'},
            'basketball': {'players': 5, 'duration': '48 min (NBA)',
                           'governing_body': 'FIBA', 'origin': 'USA 1891'},
            'tennis': {'players': '1 or 2 per side', 'sets': 'Best of 3 or 5',
                       'governing_body': 'ITF', 'origin': 'England 19th century'},
            'bóng chuyền': {'players': 6, 'sets': 'Best of 5',
                            'governing_body': 'FIVB', 'origin': 'USA 1895'},
            'volleyball': {'players': 6, 'sets': 'Best of 5',
                           'governing_body': 'FIVB', 'origin': 'USA 1895'},
            'bóng bàn': {'players': '1 or 2 per side', 'sets': 'Best of 5 or 7',
                         'governing_body': 'ITTF', 'origin': 'England late 19th'},
            'cầu lông': {'players': '1 or 2 per side', 'sets': 'Best of 3',
                         'governing_body': 'BWF', 'origin': 'British India'},
            'bơi lội': {'governing_body': 'FINA', 'strokes': ['Freestyle', 'Backstroke',
                                                              'Breaststroke', 'Butterfly']},
        }

    @property
    def name(self) -> str:
        return "SportsDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 604800  # 1 week

    def get_supported_intents(self) -> list[str]:
        return ['sports_olympic', 'sports_world_cup', 'sports_athlete',
                'sports_rules', 'sports_info']

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._olympics, self._world_cup, self._athletes, self._sports_rules):
                if entity_lower in table:
                    return True
                for key in table:
                    if key in entity_lower or entity_lower in key:
                        return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        if not entity:
            return None
        entity_lower = entity.lower().strip()

        # Olympics
        if entity_lower in self._olympics:
            data = self._olympics[entity_lower]
            return {
                'value': str(data.get('year', '')),
                'source': 'Local Sports Database',
                'metadata': data
            }
        for key, data in self._olympics.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': str(data.get('year', '')),
                    'source': 'Local Sports Database',
                    'metadata': data
                }

        # World Cup
        if entity_lower in self._world_cup:
            data = self._world_cup[entity_lower]
            return {
                'value': data.get('winner', ''),
                'source': 'Local Sports Database',
                'metadata': data
            }
        for key, data in self._world_cup.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': data.get('winner', ''),
                    'source': 'Local Sports Database',
                    'metadata': data
                }

        # Athletes
        if entity_lower in self._athletes:
            data = self._athletes[entity_lower]
            return {
                'value': data.get('sport', ''),
                'source': 'Local Sports Database',
                'metadata': data
            }
        for key, data in self._athletes.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': data.get('sport', ''),
                    'source': 'Local Sports Database',
                    'metadata': data
                }

        # Sports rules
        if entity_lower in self._sports_rules:
            data = self._sports_rules[entity_lower]
            return {
                'value': str(data.get('players', '')),
                'source': 'Local Sports Database',
                'metadata': data
            }
        for key, data in self._sports_rules.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': str(data.get('players', '')),
                    'source': 'Local Sports Database',
                    'metadata': data
                }

        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
