"""Canonical fast learning configuration and compatibility wrapper."""
from __future__ import annotations

import asyncio  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import json  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import logging
import os
import random  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import re  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import sqlite3  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import threading
import time  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
import types
import urllib.parse
import urllib.request  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from datetime import datetime  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from pathlib import Path  # noqa: F401  # [hygiene-keep] wire-parent namespace injection

from scp.core.db_manager import _KNOWLEDGE_CANONICAL_DDL  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from scp.core.learning_run_ledger import ledger_run  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
from scp.core.subsystem_telemetry import (  # noqa: F401  # [hygiene-keep] wire-parent namespace injection
    SubsystemTelemetry,
    heartbeat_sleep,
    telemetry_async_cycle,
)

logger = logging.getLogger("scp.core.fast_learning_engine")

SEED_QUESTIONS = {
    "geography": ["Thủ đô của {country} là gì?", "Diện tích của {country} bao nhiêu km vuông?", "Dân số của {country} là bao nhiêu?", "Sông dài nhất ở {country} tên gì?", "Đỉnh núi cao nhất ở {country} tên gì?"],
    "history": ["{country} độc lập vào năm nào?", "Ai là người sáng lập {country}?", "Chiến tranh lớn nhất ở {country} diễn ra khi nào?"],
    "chemistry": ["Khoáng sản quan trọng nhất của {country} là gì?", "Ngành hóa chất lớn nhất ở {country} sản xuất cái gì?", "Nhiên liệu chính được dùng để phát điện ở {country} là gì?", "Công thức phân tử của {compound} là gì?", "Khối lượng phân tử của {compound} là bao nhiêu?", "Nhiệt độ sôi của {compound} là bao nhiêu độ C?"],
    "physics": ["Nhà vật lý học nổi tiếng nhất của {country} là ai?", "Phát minh vật lý quan trọng nhất của {country} là gì?", "Trường đại học nghiên cứu vật lý hàng đầu ở {country} tên gì?", "Tốc độ ánh sáng là bao nhiêu km/s?", "Hằng số hấp dẫn G có giá trị bao nhiêu?", "Hằng số Planck có giá trị bao nhiêu?"],
    "biology": ["Động vật đặc trưng (đặc hữu) của {country} là con gì?", "Loài thực vật phổ biến nhất ở {country} là cây gì?", "Vườn quốc gia lớn nhất ở {country} tên gì?", "Số nhiễm sắc thể của con người là bao nhiêu?", "ADN được phát hiện bởi ai?", "Quang hợp tạo ra khí gì?"],
}
COUNTRIES = ["Việt Nam", "Trung Quốc", "Nhật Bản", "Hàn Quốc", "Ấn Độ", "Nga", "Mỹ", "Anh", "Pháp", "Đức", "Brazil", "Úc", "Canada", "Thái Lan"]
DOMAINS = ["geography", "history", "chemistry", "physics", "biology"]
COMPOUNDS = ["nước", "muối ăn", "axit sunfuric", "ethanol", "methane", "ammoniac"]
COUNTRY_DOMAIN_HINTS = {
    "Việt Nam": {"chemistry": "khoáng sản: than đá, apatit, boxit", "physics": "nhà vật lý: Trần Đại Nghĩa", "biology": "đặc hữu: sao la, voọc mũi hếch, rùa Hoàn Kiếm"},
    "Trung Quốc": {"chemistry": "khoáng sản: đất hiếm, than đá lớn nhất thế giới", "physics": "phát minh: la bàn, thuốc súng", "biology": "đặc hữu: gấu trúc, cá heo Dương Tử"},
    "Nhật Bản": {"chemistry": "ngành hóa chất: Sumitomo, Mitsui", "physics": "Nobel vật lý: Yukawa Hideki (1949)", "biology": "đặc hữu: salamander khổng lồ Nhật Bản, hạc đỏ"},
    "Hàn Quốc": {"chemistry": "ngành hóa chất: LG Chem, Samsung SDI", "physics": "Nobel vật lý: chưa có", "biology": "đặc hữu: hổ Siberia (giới hạn), sáo Triều Tiên"},
    "Ấn Độ": {"chemistry": "khoáng sản: quặng sắt, mica", "physics": "Nobel vật lý: C.V. Raman (1930)", "biology": "đặc hữu: hổ Bengal, sư tử châu Á, voi Ấn Độ"},
    "Nga": {"chemistry": "khoáng sản: dầu mỏ, khí tự nhiên, kim cương", "physics": "Nobel vật lý: nhiều (Landau, Kapitsa, Ginzburg)", "biology": "đặc hữu: hổ Amur, báo tuyết, gấu nâu Kamchatka"},
    "Mỹ": {"chemistry": "ngành hóa chất: Dow, DuPont, ExxonMobil", "physics": "Nobel vật lý: Feynman, Einstein, many", "biology": "đặc hữu: đại bàng hói, gấu xám, nai sừng tấm"},
    "Anh": {"chemistry": "ngành hóa chất: ICI (lịch sử), BP, Shell", "physics": "Newton, Faraday, Maxwell, Hawking", "biology": "đặc hữu: chim cuồi, hồ Loch Ness (huyền thoại)"},
    "Pháp": {"chemistry": "khoáng sản: uranium (Artois), muối", "physics": "Nobel vật lý: Becquerel, Curie, de Broglie", "biology": "đặc hữu: giông Pháp, nai Do ec"},
    "Đức": {"chemistry": "BASF, Bayer, Bayerische Motoren Werke", "physics": "Einstein, Planck, Heisenberg, Born", "biology": "đặc hữu: lợn rừng Đức, chim đại bàng vàng"},
    "Brazil": {"chemistry": "khoáng sản: quặng sắt, nhôm, mangan", "physics": "Nobel vật lý: chưa có", "biology": "đặc hữu: Amazon — jaguar, anaconda, chim ruồi"},
    "Úc": {"chemistry": "khoáng sản: quặng sắt, vàng, than đá", "physics": "Nobel vật lý: Bragg (cha+con, 1915)", "biology": "đặc hữu: kangaroo, koala, platypus, echidna"},
    "Canada": {"chemistry": "khoáng sản: uranium, kali, vàng", "physics": "Nobel vật lý: Strangeway, Brockhouse, McDonald", "biology": "đặc hữu: gấu Bắc Cực, nai sừng tấm, beaver"},
    "Thái Lan": {"chemistry": "khoáng sản: thiếc, wolfram, fluorite", "physics": "Nobel vật lý: chưa có", "biology": "đặc hữu: voi Thái, gaur, bò tót"},
}


def get_country_domain_matrix() -> dict:
    matrix = {}
    for country in COUNTRIES:
        matrix[country] = {}
        for domain in DOMAINS:
            matrix[country][domain] = sum(1 for template in SEED_QUESTIONS[domain] if "{country}" in template)
    return matrix


def get_total_combinations() -> int:
    return sum(sum(cells.values()) for cells in get_country_domain_matrix().values())


NEWS_SOURCES = [
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://vnexpress.net/rss/the-gioi.rss",
]
LEARNING_INTERVAL = int(os.environ.get("SCP_LEARNING_INTERVAL", "3600"))
PARALLEL_LLM_CONCURRENCY = int(os.environ.get("SCP_LEARN_CONCURRENCY", "10"))
WIKIPEDIA_CONCURRENCY = int(os.environ.get("SCP_WIKI_CONCURRENCY", "5"))
LEARN_INTERVAL_FAST = int(os.environ.get("SCP_LEARN_INTERVAL_FAST", "300"))
LEARN_INTERVAL_BURST = int(os.environ.get("SCP_LEARN_INTERVAL_BURST", "60"))
LEARN_INTERVAL_IDLE = int(os.environ.get("SCP_LEARN_INTERVAL_IDLE", "1800"))
LEARN_CYCLE_TIMEOUT_SECONDS = int(os.environ.get("SCP_FAST_LEARNING_CYCLE_TIMEOUT_SECONDS", "300"))
SKIP_KNOWN_QUESTIONS = os.environ.get("SCP_SKIP_KNOWN", "1") == "1"
COMPOUNDING_ENABLED = os.environ.get("SCP_COMPOUNDING", "1") == "1"
_FAST_LEARNING_THREAD: threading.Thread | None = None
_FAST_LEARNING_THREAD_LOCK = threading.Lock()

from .fast_learning_engine_parts import fastlearningengine as _p_engine
from .fast_learning_engine_parts import start_fast_learning_thread as _p_thread

_PARTS = (_p_engine, _p_thread)


def _wire_parts() -> None:
    shared = dict(globals())
    for part in _PARTS:
        part.__dict__.update(shared)


def _rebind_part_function(fn):
    """Bind extracted thread orchestration to this module's singleton state."""
    rebound = types.FunctionType(fn.__code__, globals(), fn.__name__, fn.__defaults__, fn.__closure__)
    rebound.__kwdefaults__ = fn.__kwdefaults__
    rebound.__annotations__ = dict(getattr(fn, "__annotations__", {}))
    rebound.__doc__ = fn.__doc__
    rebound.__module__ = __name__
    return rebound


_wire_parts()
FastLearningEngine = _p_engine.FastLearningEngine
start_fast_learning_thread = _rebind_part_function(_p_thread.start_fast_learning_thread)
# Preserve the historical facade identity. Before the split these public
# objects were defined in this module; callers that introspect or pickle them
# must not observe an implementation-only ``*_parts`` module after refactoring.
FastLearningEngine.__module__ = __name__
_wire_parts()


def start_learning_thread(scp_db_path: str = "data/v13.db", data_dir: str = "data") -> threading.Thread:
    logger.info("[G3-MERGE] start_learning_thread() delegates to the idempotent canonical learning thread")
    return start_fast_learning_thread(scp_db_path=scp_db_path, data_dir=data_dir)


_wire_parts()

__all__ = [
    "FastLearningEngine", "start_fast_learning_thread", "start_learning_thread",
    "get_country_domain_matrix", "get_total_combinations", "SEED_QUESTIONS",
    "COUNTRIES", "DOMAINS", "COMPOUNDS", "COUNTRY_DOMAIN_HINTS",
]
