"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
IDataSource Interface - Base interface cho tất cả data sources

[V104.32] Còn cung cấp shared negative-result cache cho health pings:
`shared_health_ping` + `reachability_ping` + `reset_shared_health_cache`.
"""
import logging
import os
import threading
import time
import urllib.error
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# [V104.32] Shared health-ping cache (cross-instance)
# ---------------------------------------------------------------------------
# Root cause fixed here: the honest-ping wave (AUDIT-FIX low-4) made
# health_check() perform REAL network pings, but the 60s result cache lived in
# each instance's `self._cache`. The test suite (and /health consumers) build
# FRESH source instances per call-chain, so the per-instance cache never hit
# and every call re-payed the network timeout (dozens of serial 3-10s
# timeouts). Fix: one process-wide cache keyed per source class.
#
# FAIL-CLOSED CONTRACT (không đổi): health_check() vẫn trả False khi ping thật
# gần nhất thất bại. Cache một kết quả False trong TTL KHÔNG fake health — đó
# chính là quan sát thực tế gần nhất về endpoint ("last observed reality").
# Caching chỉ loại bỏ việc LẶP LẠI cùng một ping trong khoảng TTL ngắn; sau
# TTL, ping thật được chạy lại. Kết quả True (ping thành công) dùng chung cache
# để giữ nhất quán với hành vi per-instance 60s trước đây.
_SHARED_HEALTH_CACHE: dict[str, tuple[bool, float]] = {}
_SHARED_HEALTH_CACHE_LOCK = threading.Lock()
_HEALTH_NEG_TTL_ENV = "SCP_HEALTH_NEG_CACHE_TTL"
_DEFAULT_HEALTH_NEG_TTL = 60.0


def health_neg_cache_ttl() -> float:
    """TTL (giây) của shared health cache, đọc env MỖI LẦN GỌI để tests và
    vận hành có thể override runtime (SCP_HEALTH_NEG_CACHE_TTL, default 60).
    TTL <= 0 tắt cache (ping mỗi lần gọi)."""
    raw = os.environ.get(_HEALTH_NEG_TTL_ENV, "")
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            logger.warning(
                "[health-cache] %s=%r không parse được — dùng default %ss",
                _HEALTH_NEG_TTL_ENV, raw, _DEFAULT_HEALTH_NEG_TTL,
            )
    return _DEFAULT_HEALTH_NEG_TTL


def reset_shared_health_cache() -> None:
    """Xoá toàn bộ shared health cache (test isolation + admin diagnostics)."""
    with _SHARED_HEALTH_CACHE_LOCK:
        _SHARED_HEALTH_CACHE.clear()


def shared_health_ping(source_id: str, ping: Callable[[], bool]) -> bool:
    """Chạy `ping()` tối đa 1 lần mỗi TTL per `source_id`, trả kết quả honest.

    - Trong TTL: trả kết quả đã quan sát (True hoặc False) KHÔNG re-ping.
    - Ngoài TTL / lần đầu / TTL<=0: chạy `ping()` thật và cache kết quả.
    - `ping()` raise (bug, network stack lỗi) → coi là ping thất bại → False
      (fail-closed) và được cache như một quan sát thất bại thật.

    Cache là CROSS-INSTANCE (key theo source, không theo object) — chính là
    điểm khác biệt so với self._cache cũ khiến test suite re-ping hàng chục
    lần mỗi call-chain.
    """
    ttl = health_neg_cache_ttl()
    now = time.time()
    if ttl > 0:
        with _SHARED_HEALTH_CACHE_LOCK:
            entry = _SHARED_HEALTH_CACHE.get(source_id)
            if entry is not None and now - entry[1] < ttl:
                return entry[0]
    try:
        healthy = bool(ping())
    except Exception as exc:
        logger.warning(
            "[health-cache] ping của %s raise %s — fail-closed False: %s",
            source_id, type(exc).__name__, exc, exc_info=True,
        )
        healthy = False
    with _SHARED_HEALTH_CACHE_LOCK:
        _SHARED_HEALTH_CACHE[source_id] = (healthy, time.time())
    return healthy


def reachability_ping(url: str, *, timeout: float = 3.0) -> bool:
    """Ping reachability thuần của một endpoint (URL cố định, không chứa key).

    Bất kỳ HTTP response nào (kể cả 401/403/404 do thiếu key/tham số) chứng
    minh service SỐNG → True. Chỉ exception tầng transport (egress denied, DNS,
    timeout, connection refused) → False. Đây là cùng contract fail-closed với
    pattern health_check của agriculture/finance từ AUDIT-FIX low-4.
    """
    # Import lười: tránh kéo egress policy machinery vào mọi lần import
    # interface (giữ hành vi import nhẹ như trước).
    from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

    try:
        with safe_urlopen(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        # HTTPError = ĐÃ nhận HTTP response từ server → endpoint sống.
        return True
    except Exception as exc:
        logger.warning(
            "[health-cache] reachability ping %s thất bại: %s",
            url, type(exc).__name__,
        )
        return False


class IDataSource(ABC):
    """
    Interface chuẩn cho tất cả data sources.
    Mỗi lĩnh vực mới cần implement interface này.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên của data source."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Độ ưu tiên (1 = cao nhất)."""
        pass

    @property
    @abstractmethod
    def ttl(self) -> int:
        """Cache TTL tính bằng giây."""
        pass

    @abstractmethod
    def get_supported_intents(self) -> list[str]:
        """Trả về danh sách intents mà source này hỗ trợ."""
        pass

    @abstractmethod
    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        """Kiểm tra xem source này có xử lý được intent không."""
        pass

    @abstractmethod
    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """
        Lấy dữ liệu thực để xác minh.

        Args:
            intent: Loại câu hỏi (ví dụ: 'molecular_weight', 'exchange_rate')
            entity: Thực thể cần tra cứu (ví dụ: 'water', 'USD/EUR')
            **kwargs: Các tham số bổ sung

        Returns:
            Dict với keys:
                - value: Giá trị thực
                - source: Tên nguồn dữ liệu
                - metadata: Thông tin bổ sung (optional)
            None nếu không tìm thấy
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Kiểm tra xem data source có hoạt động không."""
        pass
