"""
Mảnh ghép #40 — Budget Engine: tự quản lý tài chính theo độ khó của task.

TẠI SAO: gọi model đắt cho task check chính tả là tự phá sản; gọi model rẻ
cho bug logic khó là tự ngược đãi chất lượng. Engine này chấm ĐỘ KHÓ của
input bằng đặc trưng deterministic (không LLM, không mạng), rồi quyết định
thứ tự tier:
  - EASY  → free_first: thử FREE model trước (rẻ, nhanh)
  - HARD  → paid_first: giữ PAID model trước (mạnh)
Routing vẫn qua chuỗi failover hiện có — engine chỉ XÁO THỨ TỰ tier,
không thay đổi provider nào cả (không ưu tiên model, chỉ ưu tiên ngân sách).
"""
from __future__ import annotations

import os
import re

_HARD_SIGNALS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"race condition|deadlock|concurr|thread|mutex",
    r"memory leak|stack overflow|segfault|crash",
    r"security|injection|bypass|exploit|privilege",
    r"architecture|refactor|design|protocol|state machine",
    r"async|await|event loop|callback",
    r"algorithm|complexity|optimize",
))
_EASY_SIGNALS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"typo|spelling|syntax|import statement|rename",
    r"\blog(ging)?\b|comment|docstring",
    r"\bprint\b|variable name",
))


def difficulty_score(text: str) -> float:
    """Điểm độ khó >= 0 (deterministic). Càng cao càng cần model mạnh."""
    if not text:
        return 0.0
    score = 0.0
    for pattern in _HARD_SIGNALS:
        if pattern.search(text):
            score += 10.0
    for pattern in _EASY_SIGNALS:
        if pattern.search(text):
            score -= 3.0
    # Input dài = context nặng = chi phí thật
    score += min(len(text) / 2000.0, 5.0)
    return round(max(score, 0.0), 2)


def route_tier(text: str, task: str = "default", hard_threshold: float = 10.0) -> str:
    """'paid_first' hoặc 'free_first' theo ngân sách + độ khó.

    Override tường task: env SCP_BUDGET_TIER_<TASK>=paid_first|free_first.
    task='autofix' luôn paid_first (vá code cần model mạnh nhất — ROOT-FIX 46).
    """
    env_override = os.environ.get(f"SCP_BUDGET_TIER_{task.upper()}", "").strip().lower()
    if env_override in {"paid_first", "free_first"}:
        return env_override
    if task == "autofix":
        return "paid_first"
    return "paid_first" if difficulty_score(text) >= hard_threshold else "free_first"


def order_tiers(text: str, task: str = "default", hard_threshold: float = 10.0) -> list[str]:
    """Trả về thứ tự tier: ['paid', 'free'] hoặc ['free', 'paid']."""
    return ["paid", "free"] if route_tier(text, task, hard_threshold) == "paid_first" else ["free", "paid"]
