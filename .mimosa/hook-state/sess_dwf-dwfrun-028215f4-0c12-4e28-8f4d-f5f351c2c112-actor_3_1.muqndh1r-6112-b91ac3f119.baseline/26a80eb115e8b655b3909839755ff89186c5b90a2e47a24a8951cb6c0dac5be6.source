"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
SCP V39.1 — Kham Pha Logger.

Khôi phục tính năng ghi log nén GZIP theo lĩnh vực + sub-domain + tháng.
Bị mất khi tách module V27.

Output: data/kham_pha/{frame}/{sub}_{year_month}.jsonl.gz

Ví dụ:
  data/kham_pha/math/arithmetic_addition_2026-07.jsonl.gz
  data/kham_pha/chemistry/molecular_weight_2026-07.jsonl.gz
  data/kham_pha/weather/temperature_2026-07.jsonl.gz
"""

import gzip
import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger("scp.kham_pha_logger")

# Import DATA_DIR
try:
    from scp.core.db_manager import DATA_DIR
except ImportError as exc:
    # silent-by-design: db_manager import is optional; the documented repo-relative data dir is used.
    logger.debug("kham_pha_logger: DATA_DIR import failed, using repo-relative default: %s", exc, exc_info=True)
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class KhamPhaLogger:
    """
    Ghi log khám phá theo lĩnh vực + sub-domain + tháng (gzip compressed).
    """

    def __init__(self):
        self._log_counter = 0

    def log(self, entry: dict) -> None:
        """
        Ghi 1 entry vào kham_pha/{frame}/{sub}_{month}.jsonl.gz

        Args:
            entry: {question, ai_answer, frame, final_verdict, real_value, source, timestamp, ...}
        """
        self._log_counter += 1
        # Log every 5th entry (not every 10 like V14 — we want more data)
        if self._log_counter % 5 != 0:
            return

        try:
            frame = entry.get("frame", "unknown") or "unknown"
            question = entry.get("question", "")
            ai_answer = entry.get("ai_answer", "")

            sub = self._detect_subdomain(frame, question, ai_answer)
            month = datetime.now().strftime("%Y-%m")

            # data/kham_pha/{frame}/{sub}_{month}.jsonl.gz
            log_dir = os.path.join(DATA_DIR, "kham_pha", frame)
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"{sub}_{month}.jsonl.gz")

            with gzip.open(log_path, "at", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.debug(f"KhamPha log error: {e}", exc_info=True)

    def _detect_subdomain(self, frame: str, question: str, ai_answer: str = "") -> str:
        """Phát hiện sub-domain từ question."""
        q = (question or "").lower()

        if frame == "math":
            if "collatz" in q:
                return "collatz"
            if "giai thừa" in q or re.search(r"\d+\s*!", q):
                return "factorial"
            if "fibonac" in q or "số nguyên tố" in q or "prime" in q:
                return "sequences"
            if re.search(r"[+\-*/]", q) or "tính" in q or "calculate" in q:
                if "+" in q: return "arithmetic_addition"
                elif "-" in q: return "arithmetic_subtraction"
                elif "*" in q: return "arithmetic_multiplication"
                elif "/" in q: return "arithmetic_division"
                return "arithmetic_general"
            return "general"

        if frame == "chemistry":
            if "khối lượng phân tử" in q or "molecular weight" in q:
                return "molecular_weight"
            return "general"

        if frame in ("conversion", "finance"):
            if "chuyển đổi" in q or "sang" in q or "exchange" in q:
                return "currency_exchange"
            if "giá" in q or "price" in q or "bitcoin" in q or "crypto" in q:
                return "crypto_price"
            return "general"

        if frame == "weather":
            if "nhiệt độ" in q or "temperature" in q:
                return "temperature"
            if "độ ẩm" in q or "humidity" in q:
                return "humidity"
            return "general"

        if frame == "biology":
            if "nhiễm sắc thể" in q or "chromosome" in q:
                return "chromosomes"
            if "dna" in q or "rna" in q:
                return "genetics"
            if "nhịp tim" in q or "heart rate" in q:
                return "physiology"
            return "general"

        if frame == "geography":
            if "thủ đô" in q or "capital" in q:
                return "capitals"
            if "dân số" in q or "population" in q:
                return "population"
            if "diện tích" in q or "area" in q:
                return "area"
            return "general"

        if frame == "reality":
            if "tốc độ ánh sáng" in q or "speed of light" in q:
                return "speed_of_light"
            if "planck" in q:
                return "planck_constant"
            if "avogadro" in q:
                return "avogadro"
            if "gia tốc" in q or "gravity" in q:
                return "gravity"
            return "physical_constants"

        if frame == "history":
            if re.search(r"\b\d{3,4}\b", q):
                return "events_by_year"
            if "ai là" in q or "who is" in q or "who was" in q:
                return "biographical"
            return "general"

        if frame == "logic":
            return "comparison"

        if frame == "statistics":
            if "trung bình" in q or "mean" in q or "average" in q:
                return "mean"
            if "median" in q or "trung vị" in q:
                return "median"
            return "general"

        return "general"


# Singleton
_kham_pha_logger: KhamPhaLogger | None = None

def get_kham_pha_logger() -> KhamPhaLogger:
    global _kham_pha_logger
    if _kham_pha_logger is None:
        _kham_pha_logger = KhamPhaLogger()
    return _kham_pha_logger
