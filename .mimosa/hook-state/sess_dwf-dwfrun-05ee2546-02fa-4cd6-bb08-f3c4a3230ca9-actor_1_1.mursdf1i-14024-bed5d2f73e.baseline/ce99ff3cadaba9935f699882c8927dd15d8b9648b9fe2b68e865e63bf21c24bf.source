"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
RealityDataSource - Data source cho "Thực tế" kiểm tra
Bao gồm: physical impossibilities, common facts, world records.
"""
import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class RealityDataSource(IDataSource):
    """Data source cho reality checks (kiểm tra tính hợp lý)."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Physical limits (anything beyond this is suspicious)
        self._physical_limits = {
            'tốc độ ánh sáng': 299792458,  # m/s - absolute speed limit
            'speed of light': 299792458,
            'nhiệt độ thấp nhất': -273.15,  # °C - absolute zero
            'absolute zero': -273.15,
            'nhiệt độ cao nhất có thể': 1.416808e32,  # K - Planck temperature
            'planck temperature': 1.416808e32,
            'áp suất khí quyển': 101325,  # Pa - sea level
            'atmospheric pressure': 101325,
            'độ sâu biển sâu nhất': 10994,  # m - Mariana Trench
            'mariana trench depth': 10994,
            'đỉnh núi cao nhất': 8848.86,  # m - Everest
            'mount everest height': 8848.86,
            'tuổi tối đa con người': 122,  # years - Jeanne Calment
            'human max age': 122,
            'số tim đập tối đa': 220,  # bpm - max heart rate
            'max heart rate': 220,
            'khối lượng con người lớn nhất': 635,  # kg - Jon Brower Minnoch
            'heaviest human': 635,
            'chiều cao con người cao nhất': 2.72,  # m - Robert Wadlow
            'tallest human': 2.72,
        }

        # Common world facts
        self._world_facts = {
            'số quốc gia': 195,
            'number of countries': 195,
            'dân số thế giới': 8.1e9,
            'world population': 8.1e9,
            'diện tích trái đất': 510072000,  # km² total surface
            'earth surface area': 510072000,
            'diện tích đất liền': 148940000,  # km²
            'earth land area': 148940000,
            'diện tích đại dương': 361132000,  # km²
            'earth ocean area': 361132000,
            'số châu lục': 7,
            'number of continents': 7,
            'số đại dương': 5,
            'number of oceans': 5,
            'số ngôn ngữ': 7151,  # living languages
            'number of languages': 7151,
            'số múi giờ': 38,
            'number of time zones': 38,
            'số nguyên tố tự nhiên': 118,
            'number of elements': 118,
            'số hành tinh': 8,
            'number of planets': 8,
            'số sao dải ngân hà': 2e11,
            'stars in milky way': 2e11,
            'số thiên hà vũ trụ': 2e12,
            'galaxies in universe': 2e12,
        }

        # Impossible claims (always flagged as false)
        self._impossible_claims = {
            'vượt tốc độ ánh sáng': 'Vật chất không thể vượt qua tốc độ ánh sáng trong chân không',
            'faster than light': 'Matter cannot exceed speed of light in vacuum',
            'nhiệt độ dưới không tuyệt đối': 'Không có nhiệt độ dưới -273.15°C',
            'below absolute zero': 'No temperature below -273.15°C exists',
            'hạt nhân nguyên tử tự phân rã trong 1 giây': 'Phân rã hạt nhân là quá trình ngẫu nhiên, không có thời gian cố định',
            'vĩnh sinh': 'Không có sinh vật vĩnh sinh',
            'immortality': 'No organism is biologically immortal in practice',
            'tạo năng lượng từ hư không': 'Vi phạm định luật bảo toàn năng lượng',
            'energy from nothing': 'Violates conservation of energy',
            'đi ngược thời gian': 'Vi phạm mũi tên thời gian nhiệt động lực học',
            'time travel to past': 'Violates 2nd law of thermodynamics',
        }

        # Common sense checks
        self._common_sense = {
            'nước sôi ở 100c': True,
            'water boils at 100c': True,
            'nước đóng băng ở 0c': True,
            'water freezes at 0c': True,
            'trái đất phẳng': False,
            'earth is flat': False,
            'mặt trời quay quanh trái đất': False,
            'sun revolves around earth': False,
            'con người có 206 xương': True,
            'humans have 206 bones': True,
            'con người có 2 thận': True,
            'humans have 2 kidneys': True,
            'nước là h2o': True,
            'water is h2o': True,
            '1+1=2': True,
            'số pi = 3.14': True,
            'pi equals 3.14': True,
            'phốt pho là kim loại': False,
            'phosphorus is metal': False,
            'đá nổi trên nước': False,  # Most stones sink
            'stones float on water': False,
            'kim loại dẫn điện': True,
            'metals conduct electricity': True,
            'cao su dẫn điện': False,
            'rubber conducts electricity': False,
            'trái đất cách mặt trời 1 ly': False,
            'earth is 1 cm from sun': False,
        }

    @property
    def name(self) -> str:
        return "RealityDataSource"

    @property
    def priority(self) -> int:
        return 1  # High priority for reality checks

    @property
    def ttl(self) -> int:
        return 604800  # 1 week

    def get_supported_intents(self) -> list[str]:
        return [
            'reality_check',
            'physical_limit',
            'world_fact',
            'impossible_claim',
            'common_sense',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._physical_limits, self._world_facts,
                          self._impossible_claims, self._common_sense):
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

        # Physical limits
        if entity_lower in self._physical_limits:
            return {
                'value': self._physical_limits[entity_lower],
                'source': 'Local Reality Database',
                'metadata': {'category': 'physical_limit', 'name': entity_lower}
            }
        for key, val in self._physical_limits.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': val,
                    'source': 'Local Reality Database',
                    'metadata': {'category': 'physical_limit', 'name': key}
                }

        # World facts
        if entity_lower in self._world_facts:
            return {
                'value': self._world_facts[entity_lower],
                'source': 'Local Reality Database',
                'metadata': {'category': 'world_fact', 'name': entity_lower}
            }
        for key, val in self._world_facts.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': val,
                    'source': 'Local Reality Database',
                    'metadata': {'category': 'world_fact', 'name': key}
                }

        # Impossible claims
        if entity_lower in self._impossible_claims:
            return {
                'value': False,
                'source': 'Local Reality Database',
                'metadata': {
                    'category': 'impossible_claim',
                    'name': entity_lower,
                    'reason': self._impossible_claims[entity_lower]
                }
            }
        for key, reason in self._impossible_claims.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': False,
                    'source': 'Local Reality Database',
                    'metadata': {
                        'category': 'impossible_claim',
                        'name': key,
                        'reason': reason
                    }
                }

        # Common sense
        if entity_lower in self._common_sense:
            return {
                'value': self._common_sense[entity_lower],
                'source': 'Local Reality Database',
                'metadata': {'category': 'common_sense', 'name': entity_lower}
            }
        for key, val in self._common_sense.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': val,
                    'source': 'Local Reality Database',
                    'metadata': {'category': 'common_sense', 'name': key}
                }

        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
