"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
Batch API Processor - Xử lý nhiều API calls trong 1 request
Tối ưu cho: Currency, Crypto, Weather, NASA data
"""
import json
import logging
import re
import time
import urllib.parse
import urllib.request

from scp.security.url_safety import safe_urlopen

logger = logging.getLogger(__name__)

# [AUDIT-20260909 S6a] Bảo vệ outbound fetch: mọi giá trị query chỉ được chứa
# ký tự an toàn (chữ/số/dấu phân cách), hostname phải khớp endpoint dự kiến,
# và request đi qua safe_urlopen (validate scheme + chặn IP nội bộ/loopback).
_QUERY_VALUE_SAFE = re.compile(r"^[A-Za-z0-9._,-]{1,120}$")


def _http_get_json(url: str, expected_host: str, timeout: int) -> dict:
    """Fetch JSON từ upstream: kiểm tra host + giá trị query, rồi fetch an toàn."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise ValueError("Unexpected upstream endpoint")
    for _key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        if not _QUERY_VALUE_SAFE.match(value):
            raise ValueError("Unsafe query parameter")
    req = urllib.request.Request(url, headers={"User-Agent": "SCP-Batch/1.0"})  # noqa: S310 — validated by safe_urlopen
    with safe_urlopen(req, timeout=timeout) as resp:
        if getattr(resp, "status", 200) != 200:
            raise ValueError("Upstream returned non-success status")
        return json.loads(resp.read().decode("utf-8"))


class BatchAPIProcessor:
    """
    Batch processor để gom nhiều API calls thành 1 request.
    Giảm số lượng HTTP requests, tăng tốc độ.
    """

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes

    def batch_fetch_rates(self, pairs: list[tuple[str, str]]) -> dict[tuple[str, str], float | None]:
        """
        Fetch multiple exchange rates in ONE API call.

        Args:
            pairs: List of (from_currency, to_currency)

        Returns:
            Dict[(from, to)] = rate value
        """
        if not pairs:
            return {}

        # Group by base currency
        groups = {}
        for from_curr, to_curr in pairs:
            # Skip if same currency
            if from_curr == to_curr:
                continue
            if from_curr not in groups:
                groups[from_curr] = []
            if to_curr not in groups[from_curr]:
                groups[from_curr].append(to_curr)

        results = {}

        # Fetch each group in ONE request
        for base, targets in groups.items():
            cache_key = (base, tuple(sorted(targets)))

            # Check cache first
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if time.time() - cached['time'] < self._cache_ttl:
                    results.update(cached['rates'])
                    continue

            # One API call for all targets
            targets_str = ','.join(targets)
            url = f"https://api.frankfurter.app/latest?from={base}&to={targets_str}"

            try:
                data = _http_get_json(url, "api.frankfurter.app", self.timeout)
                for target in targets:
                    rate = data.get('rates', {}).get(target)
                    if rate:
                        results[(base, target)] = rate

                # Cache the result
                # [V104.36 #67] TẠI SAO: dict(results) snapshots ALL accumulated
                # rates from earlier groups → cache poisoning. On later cache hit,
                # caller receives rates they never asked for.
                # Fix: snapshot only THIS group's contributions.
                group_rates = {(base, t): data.get('rates', {}).get(t)
                               for t in targets if data.get('rates', {}).get(t)}
                self._cache[cache_key] = {
                    'rates': group_rates,
                    'time': time.time()
                }
            except Exception as e:
                logger.warning(f"Batch fetch failed for {base}: {e}", exc_info=True)
                # Fallback: individual fetches
                for target in targets:
                    rate = self._fetch_single_rate(base, target)
                    if rate:
                        results[(base, target)] = rate

        return results

    def _fetch_single_rate(self, from_curr: str, to_curr: str) -> float | None:
        """Fallback: fetch single rate."""
        try:
            url = f"https://api.frankfurter.app/latest?from={from_curr}&to={to_curr}"
            data = _http_get_json(url, "api.frankfurter.app", self.timeout)
            return data.get('rates', {}).get(to_curr)
        except Exception as e:
            logger.warning(f"Single rate fetch failed for {from_curr}->{to_curr}: {e}", exc_info=True)
        return None

    def batch_fetch_crypto(self, symbols: list[str]) -> dict[str, float | None]:
        """
        Fetch multiple crypto prices in ONE API call.

        Args:
            symbols: List of crypto symbols (BTC, ETH, etc.)

        Returns:
            Dict[symbol] = price
        """
        if not symbols:
            return {}

        results = {}

        # CoinGecko API - fetch multiple coins at once
        try:
            ids = ','.join(symbols).lower()
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
            data = _http_get_json(url, "api.coingecko.com", self.timeout)

            for symbol in symbols:
                symbol_lower = symbol.lower()
                if symbol_lower in data:
                    price = data[symbol_lower].get('usd')
                    if price:
                        results[symbol] = price
        except Exception as e:
            logger.warning(f"Batch crypto fetch failed: {e}", exc_info=True)
            # Fallback to individual fetches
            for symbol in symbols:
                price = self._fetch_single_crypto(symbol)
                if price:
                    results[symbol] = price

        return results

    def _fetch_single_crypto(self, symbol: str) -> float | None:
        """Fallback: fetch single crypto."""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd"
            data = _http_get_json(url, "api.coingecko.com", self.timeout)
            return data.get(symbol.lower(), {}).get('usd')
        except Exception as e:
            logger.warning(f"Single crypto fetch failed for {symbol}: {e}", exc_info=True)
        return None

    def batch_fetch_weather(self, cities: list[str]) -> dict[str, float | None]:
        """
        Fetch multiple weather data in ONE API call.

        Args:
            cities: List of city names

        Returns:
            Dict[city] = temperature
        """
        if not cities:
            return {}

        results = {}

        # Open-Meteo supports multiple cities
        try:
            # Map city names to coordinates (simplified)
            city_coords = {
                'hanoi': (21.0285, 105.8542),
                'tokyo': (35.6762, 139.6503),
                'london': (51.5074, -0.1278),
                'paris': (48.8566, 2.3522),
                'new york': (40.7128, -74.0060),
                'sydney': (-33.8688, 151.2093),
            }

            # [V104.37 #82] TẠI SAO: V104.36 #68 used enumerate(coords) but
            # coords skips missing cities → index misaligned → wrong city mapping.
            # Fix: build (city_name, lat, lon) tuples, loop directly.
            matched_cities = []
            for city in cities:
                city_lower = city.lower()
                if city_lower in city_coords:
                    lat, lon = city_coords[city_lower]
                    matched_cities.append((city, lat, lon))

            for city_name, lat, lon in matched_cities:
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                try:
                    data = _http_get_json(url, "api.open-meteo.com", self.timeout)
                    temp = data.get('current_weather', {}).get('temperature')
                    if temp is not None:
                        results[city_name] = temp
                except Exception as e:
                    logger.debug(f"Weather fetch failed for {city_name}: {e}", exc_info=True)

        except Exception as e:
            logger.warning(f"Batch weather fetch failed: {e}", exc_info=True)

        return results

    def get_cache_stats(self) -> dict:
        """Return cache statistics."""
        total = len(self._cache)
        expired = sum(
            1 for v in self._cache.values()
            if time.time() - v['time'] >= self._cache_ttl
        )
        return {
            'total_entries': total,
            'expired': expired,
            'active': total - expired,
            'ttl_seconds': self._cache_ttl
        }


# Singleton instance
_batch_processor = None

def get_batch_processor() -> BatchAPIProcessor:
    """Get singleton batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchAPIProcessor()
    return _batch_processor
