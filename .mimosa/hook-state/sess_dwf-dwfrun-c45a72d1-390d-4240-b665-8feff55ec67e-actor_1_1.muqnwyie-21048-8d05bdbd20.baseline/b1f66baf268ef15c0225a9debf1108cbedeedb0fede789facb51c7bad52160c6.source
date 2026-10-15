"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
DataSourceRegistry - Quản lý đăng ký và routing data sources
"""
import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    """
    Registry để quản lý và routing đến các data sources.
    Hỗ trợ đăng ký động và fallback logic.
    """

    def __init__(self):
        self._sources: dict[str, IDataSource] = {}
        self._intent_map: dict[str, list[str]] = {}  # intent -> [source_names]
        self._cache: dict[str, dict[str, Any]] = {}  # cache key -> {value, time, ttl}

    def register(self, source: IDataSource) -> None:
        """
        Đăng ký một data source mới.

        Args:
            source: Instance implement IDataSource
        """
        source_name = source.name

        if source_name in self._sources:
            logger.warning(f"[REGISTRY] Source '{source_name}' already registered, skipping")
            return

        self._sources[source_name] = source

        # Update intent map
        for intent in source.get_supported_intents():
            if intent not in self._intent_map:
                self._intent_map[intent] = []

            # Sort by priority and add
            self._intent_map[intent].append(source_name)
            self._intent_map[intent].sort(
                key=lambda s: self._sources[s].priority
            )

        logger.info(f"[REGISTRY] Registered: {source_name} (intents: {len(source.get_supported_intents())})")

    def get_sources_for_intent(self, intent: str) -> list[IDataSource]:
        """
        Lấy danh sách sources có thể xử lý intent (theo priority).

        Args:
            intent: Intent cần xử lý

        Returns:
            Danh sách sources (rỗng nếu không có)
        """
        if intent not in self._intent_map:
            return []

        return [
            self._sources[name]
            for name in self._intent_map[intent]
            if name in self._sources
        ]

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """
        Lấy dữ liệu cho intent/entity với fallback logic.

        Args:
            intent: Loại câu hỏi
            entity: Thực thể cần tra cứu
            **kwargs: Tham số bổ sung

        Returns:
            Dict với 'value', 'source' hoặc None
        """
        # Check cache first
        cache_key = f"{intent}:{entity}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            import time
            if time.time() - cached['time'] < cached['ttl']:
                logger.debug(f"[REGISTRY] Cache HIT: {cache_key}")
                return cached['data']

        # Get sources for this intent
        sources = self.get_sources_for_intent(intent)

        if not sources:
            logger.debug(f"[REGISTRY] No source for intent: {intent}")
            return None

        # Try each source in priority order
        for source in sources:
            try:
                if source.can_handle(intent, entity):
                    result = source.fetch(intent, entity, **kwargs)
                    if result is not None:
                        # Cache the result
                        import time
                        self._cache[cache_key] = {
                            'data': result,
                            'time': time.time(),
                            'ttl': source.ttl
                        }
                        return result
            except Exception as e:
                logger.warning(f"[REGISTRY] Source {source.name} failed: {e}", exc_info=True)
                continue

        return None

    def get_stats(self) -> dict[str, Any]:
        """Lấy thống kê registry."""
        return {
            'total_sources': len(self._sources),
            'total_intents': len(self._intent_map),
            'sources': list(self._sources.keys()),
            'intents': list(self._intent_map.keys()),
            'cache_size': len(self._cache)
        }

    def list_sources(self) -> list[str]:
        """Return list of registered source names.

        [Task 32-A] Added for diagnostic + SmartClassifier routing verification.
        Returns names (not instances) so callers can check membership without
        pulling in heavy DataSource objects.
        """
        return list(self._sources.keys())

    def health_check_all(self) -> dict[str, bool]:
        """Kiểm tra health của tất cả sources."""
        results = {}
        for name, source in self._sources.items():
            try:
                results[name] = source.health_check()
            except Exception:
                logger.warning('DataSourceRegistry.health_check_all: Exception not handled', exc_info=True)
                results[name] = False
        return results


# Singleton instance
_registry = None

def get_registry() -> DataSourceRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = DataSourceRegistry()
    return _registry
