# SCP CIRCUIT: M13 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M13-closure.json)
"""
TOP-1% Systems Learning Loop — SCP học từ kho tri thức free của thế giới.

TẠI SAO module này tồn tại:
  Người vận hành SCP không có ngân sách để chạy so sánh trực tiếp với các hệ
  thống TOP 1%. Thay thế trung thực nhất: dùng các nguồn tri thức free (GitHub
  search API, Wikipedia API) để thu thập liên tục các hệ thống/thực hành tốt
  nhất theo chủ đề (agent kernel, evaluation harness, sandboxing, red-teaming,
  evidence journal...), lưu vào ledger durable có provenance, để các tầng
  WHY/autofix/learning của SCP tra cứu (`advise`) khi cần cải tiến code và logic.

Fail-closed:
  - Chỉ fetch 2 host cố định trong ALLOWED_HOSTS (SSRF-safe by construction).
  - Lỗi mạng của MỘT chủ đề không làm chết vòng học (per-topic isolation).
  - Mất mạng → trả {"ok": False} và phục vụ từ ledger cũ; không bịa records.
  - Egress opt-out: SCP_TOP_SYSTEMS_EGRESS=0 → chỉ đọc ledger.

Rate-limit trung thực: GitHub unauthenticated = 60 req/hour. Mỗi topic tốn
2 request (GitHub + Wikipedia) → learn_all() mặc định 8 topic = 16 request.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger("scp.core.top_systems_learning")

ALLOWED_HOSTS = frozenset({"api.github.com", "en.wikipedia.org"})
_USER_AGENT = "SCP-TopSystemsLearner/1.0 (+https://github.com/checken1994/GA-LAB)"

# The TOP-1% practice areas SCP is built around. Each entry maps to one GitHub
# search query + one Wikipedia query. Kept explicit and reviewable on purpose.
TOPIC_LIBRARY: dict[str, dict[str, str]] = {
    "agent_runtime": {"github_query": "AI agent runtime framework", "wiki_query": "Intelligent agent"},
    "agent_kernel": {"github_query": "agent orchestration state machine", "wiki_query": "Finite-state machine"},
    "llm_evaluation": {"github_query": "LLM evaluation benchmark harness", "wiki_query": "Automatic evaluation of language models"},
    "llm_redteam": {"github_query": "LLM red teaming prompt injection", "wiki_query": "Adversarial machine learning"},
    "sandboxing": {"github_query": "code execution sandbox isolation", "wiki_query": "Sandbox (computer security)"},
    "evidence_audit": {"github_query": "audit log hash chain tamper evidence", "wiki_query": "Hash chain"},
    "rag_verification": {"github_query": "retrieval augmented generation verification", "wiki_query": "Retrieval-augmented generation"},
    "observability": {"github_query": "LLM observability tracing", "wiki_query": "Observability"},
}

_TAG_RE = re.compile(r"<[^>]+>")

# [C1 QUARANTINE — Gemini indictment: data poisoning qua README buff-stars]
# Nội dung bên ngoài là DỮ LIỆU KHÔNG TIN CẬY. Mọi README trỏ vào chính SCP
# (bảo nó tắt sandbox, chạy root, lộ secret...) bị CÁCH LY deterministic và
# KHÔNG BAO GIỜ được serve vào prompt của WHY/fix/Reflect.
_QUARANTINE_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+rules",
    r"disable[^\n]{0,40}(sandbox|isolation|guard|filter)",
    r"os_sandbox|tier1_guard|task_kernel\.py",
    r"run\s+(as|with)\s+root|sudo\s+",
    r"\brm\s+-rf\b|format\s+c:",
    r"backdoor|reverse[_ ]shell|exfiltrat",
    r"(scp_admin_key|jwt_secret|api[_ ]?key|\.env|credentials)\s*[:=]",
    r"bypass\s+(security|auth|policy|verif)",
    r"prompt\s+injection|jailbreak",
    # [S04-FIREWALL-FIX 2026-09-03] Families that escaped the v1 wall
    # (found by test_internet_safety_firewall.py): standalone .env mentions,
    # role-hijack ("You are SCP now"), literal credential formats and
    # password assignments. Zero-trust: external content mentioning these is
    # QUARANTINED as a whole record, never served into prompts.
    r"\.env\b",
    r"you\s+are\s+(now\s+)?scp\b",
    r"sk-(live|test|proj)-[A-Za-z0-9\-_]{16,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"AKIA[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"AIza[0-9A-Za-z_\-]{30,}",
    r"\b(password|passwd|secret)\s*[:=]\s*\S+",
    r"/dev/(tcp|udp)/",
    r"(\bunion\s+select\b|\bselect\s+\*\s+from\b|\bdrop\s+table\b)",
    r"(<script\b|javascript:)",
))


_INVISIBLE_RE = re.compile(
    r"[\u200B-\u200F\u202A-\u202E\u2060-\u2069\uFEFF\u00AD\uFE00-\uFE0F]"
)

# Comprehensive Unicode confusable homoglyph translation table (Cyrillic + Greek to Latin)
_HOMOGLYPH_MAP = {
    # Cyrillic lowercase
    '\u0430': 'a', '\u0431': 'b', '\u0432': 'v', '\u0433': 'g', '\u0434': 'd',
    '\u0435': 'e', '\u0451': 'e', '\u0436': 'zh', '\u0437': 'z', '\u0438': 'i',
    '\u0439': 'i', '\u043a': 'k', '\u043b': 'l', '\u043c': 'm', '\u043d': 'n',
    '\u043e': 'o', '\u043f': 'p', '\u0440': 'r', '\u0441': 'c', '\u0442': 't',
    '\u0443': 'u', '\u0444': 'f', '\u0445': 'x', '\u0446': 'ts', '\u0447': 'ch',
    '\u0448': 'sh', '\u0449': 'shch', '\u044a': '', '\u044b': 'y', '\u044c': '',
    '\u044d': 'e', '\u044e': 'yu', '\u044f': 'ya', '\u0455': 's', '\u0456': 'i',
    '\u0458': 'j',
    # Cyrillic uppercase
    '\u0410': 'A', '\u0412': 'B', '\u0415': 'E', '\u041a': 'K', '\u041c': 'M',
    '\u041d': 'H', '\u041e': 'O', '\u0420': 'P', '\u0421': 'C', '\u0422': 'T',
    '\u0423': 'Y', '\u0425': 'X',
    # Greek lowercase
    '\u03b1': 'a', '\u03b2': 'b', '\u03b3': 'g', '\u03b4': 'd', '\u03b5': 'e',
    '\u03b6': 'z', '\u03b7': 'h', '\u03b8': 'th', '\u03b9': 'i', '\u03ba': 'k',
    '\u03bb': 'l', '\u03bc': 'm', '\u03bd': 'n', '\u03be': 'x', '\u03bf': 'o',
    '\u03c0': 'p', '\u03c1': 'r', '\u03c2': 's', '\u03c3': 's', '\u03c4': 't',
    '\u03c5': 'u', '\u03c6': 'f', '\u03c7': 'x', '\u03c8': 'ps', '\u03c9': 'w',
    # Greek uppercase
    '\u0391': 'A', '\u0392': 'B', '\u0395': 'E', '\u0396': 'Z', '\u0397': 'H',
    '\u0399': 'I', '\u039a': 'K', '\u039c': 'M', '\u039d': 'N', '\u039f': 'O',
    '\u03a1': 'P', '\u03a4': 'T', '\u03a5': 'Y', '\u03a7': 'X',
}
_HOMOGLYPH_TABLE = str.maketrans(_HOMOGLYPH_MAP)


def inspect_untrusted(content: str) -> tuple[bool, str]:
    """Deterministic quarantine check with NFKC, homoglyph mapping, and zero-width normalization. Returns (quarantined, reason)."""
    raw = content or ""
    # 1. Strip zero-width and invisible characters
    cleaned = _INVISIBLE_RE.sub("", raw)
    # 2. Apply NFKC Unicode normalization
    nfkc = unicodedata.normalize("NFKC", cleaned)
    # 3. Transliterate Cyrillic/Greek homoglyphs to ASCII
    homoglyph_norm = nfkc.translate(_HOMOGLYPH_TABLE)

    # 4. Optional unidecode enhancement if installed
    unidecode_norm = ""
    try:
        import unidecode
        unidecode_norm = unidecode.unidecode(nfkc)
    except Exception as exc:
        # [B110] unidecode is an optional enhancement; absence/failure keeps
        # unidecode_norm="" and the other candidates still apply. Log, don't pass.
        logger.debug(f"inspect_untrusted unidecode enhancement ignored: {exc}", exc_info=True)

    candidates = [homoglyph_norm, nfkc, raw]
    if unidecode_norm:
        candidates.append(unidecode_norm)

    for pattern in _QUARANTINE_PATTERNS:
        for text_cand in candidates:
            match = pattern.search(text_cand)
            if match:
                return True, f"pattern:{pattern.pattern[:40]}"
    return False, ""



def _extract_concepts(text: str, max_concepts: int = 8) -> list[str]:
    """[CURATION STAGE 3] Trích xuất tri thức cốt lõi (deterministic):
    tiêu đề section của tài liệu = bản đồ khái niệm của kiến trúc."""
    concepts: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if 3 <= len(title) <= 120 and title.lower() not in {c.lower() for c in concepts}:
                concepts.append(title)
        if len(concepts) >= max_concepts:
            break
    return concepts


def reputation_from_stars(stars: int | None) -> str:
    """[Data Quality Gate v2] Uy tín NGUỒN dựa trên metadata — KHÔNG phải
    xác minh nội dung (README 50k stars vẫn có thể độc → vẫn qua quarantine)."""
    if stars is None:
        return "medium"
    if stars >= 10_000:
        return "high"
    if stars >= 1_000:
        return "medium"
    return "low"


def egress_disabled() -> bool:
    return os.environ.get("SCP_TOP_SYSTEMS_EGRESS", "1").strip().lower() in {"0", "false", "off"}


class TokenBucket:
    """Mechanical client-side rate limiter (Cổng "gentleman's agreement" fix).

    Reality Check v2 chỉ ra: "1 vòng = 16 request < 60/h" là LỜI HỨA SUÔNG —
    admin bấm đúp hoặc scheduler lỗi là dính 403 từ GitHub. Bucket này là
    CHỐT CHẶN CỨNG phía client: hết token → chờ (bounded) hoặc raise
    RuntimeError("local_rate_limit_timeout") — không bao giờ gửi request thứ
    N+1 khi quota cơ học không cho phép.
    """

    def __init__(self, capacity: int, refill_seconds: float):
        if capacity <= 0 or refill_seconds <= 0:
            raise ValueError("capacity and refill_seconds must be positive")
        self.capacity = float(capacity)
        self.refill_seconds = float(refill_seconds)
        self._tokens = float(capacity)
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        now = time.monotonic()
        self._tokens = min(self.capacity, self._tokens + (now - self._updated) / self.refill_seconds)
        self._updated = now

    def acquire(self, max_wait: float = 70.0) -> float:
        """Block until 1 token is available. Returns waited seconds.

        Raises RuntimeError if the required wait exceeds max_wait — callers
        treat that as a fail-closed per-source error, never as a network 403.
        """
        deadline = time.monotonic() + max_wait
        waited = 0.0
        while True:
            with self._lock:
                self._refill_locked()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return waited
                need = (1.0 - self._tokens) * self.refill_seconds
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("local_rate_limit_timeout")
            nap = min(need, remaining, 5.0)
            time.sleep(nap)
            waited += nap


# GitHub unauthenticated = 60 req/h. Cap cứng client: 30 burst, refill 1
# token / 75s → bão hòa ~48 req/h < 60. Wikipedia: hào phóng hơn (1 req/s).
_GITHUB_BUCKET = TokenBucket(capacity=30, refill_seconds=75.0)
_WIKI_BUCKET = TokenBucket(capacity=30, refill_seconds=1.2)


class TopSystemsLearner:
    """Collects knowledge about top-tier systems from free internet sources."""

    def __init__(
        self,
        data_dir: str = "data",
        fetcher: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
        raw_fetcher: Callable[[str, dict[str, str]], str] | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.data_dir / "top_systems_knowledge.jsonl"
        # Injectable fetchers for hermetic tests; production uses urllib.
        # fetcher -> JSON APIs; raw_fetcher -> raw text (README deep scraper).
        self._fetcher = fetcher
        self._raw_fetcher = raw_fetcher

    # ------------------------------------------------------------------
    # Network (fixed allowlisted hosts only)
    # ------------------------------------------------------------------
    @staticmethod
    def _http_get_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"host not in learning allowlist: {parsed.hostname!r}")
        if egress_disabled():
            raise RuntimeError("egress disabled by SCP_TOP_SYSTEMS_EGRESS=0")
        merged = {"User-Agent": _USER_AGENT, **(headers or {})}
        req = urllib.request.Request(url, headers=merged)  # noqa: S310 — scheme+host allowlisted above
        # [AUDIT-20260909 SSRF-S1] safe_urlopen thay raw urlopen — thêm lớp
        # validate scheme + chặn private/loopback IP sau allowlist host.
        with safe_urlopen(req, timeout=20) as resp:  # noqa: S310 — validated by safe_urlopen
            return json.loads(resp.read(2_000_000).decode("utf-8", errors="replace"))

    def _get_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if self._fetcher is not None:
            return self._fetcher(url, headers or {})
        return self._http_get_json(url, headers)

    @staticmethod
    def _http_get_raw(url: str, headers: dict[str, str] | None = None, max_bytes: int = 500_000) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"host not in learning allowlist: {parsed.hostname!r}")
        if egress_disabled():
            raise RuntimeError("egress disabled by SCP_TOP_SYSTEMS_EGRESS=0")
        merged = {"User-Agent": _USER_AGENT, **(headers or {})}
        req = urllib.request.Request(url, headers=merged)  # noqa: S310 — scheme+host allowlisted above
        # [AUDIT-20260909 SSRF-S1] safe_urlopen thay raw urlopen — thêm lớp
        # validate scheme + chặn private/loopback IP sau allowlist host.
        with safe_urlopen(req, timeout=20) as resp:  # noqa: S310 — validated by safe_urlopen
            return resp.read(max_bytes).decode("utf-8", errors="replace")

    def _get_raw(self, url: str, headers: dict[str, str] | None = None) -> str:
        if self._raw_fetcher is not None:
            return self._raw_fetcher(url, headers or {})
        return self._http_get_raw(url, headers)

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------
    def _fetch_github(self, query: str, per_source: int) -> list[dict[str, Any]]:
        _GITHUB_BUCKET.acquire()  # mechanical cap — see TokenBucket docstring
        url = (
            "https://api.github.com/search/repositories?q="
            + urllib.parse.quote(query)
            + f"&sort=stars&order=desc&per_page={int(per_source)}"
        )
        data = self._get_json(url, headers={"Accept": "application/vnd.github+json"})
        out: list[dict[str, Any]] = []
        for item in data.get("items", [])[: per_source]:
            description = str(item.get("description") or "")[:400]
            quarantined, reason = inspect_untrusted(description)
            out.append(
                {
                    "source": "github",
                    "kind": "repository",
                    "name": str(item.get("full_name", ""))[:200],
                    "url": str(item.get("html_url", ""))[:300],
                    "stars": int(item.get("stargazers_count", 0)),
                    "forks": int(item.get("forks_count", 0)),
                    "trust": "QUARANTINED" if quarantined else "untrusted",
                    "quarantine_reason": reason,
                    "description": description,
                    "reputation": reputation_from_stars(int(item.get("stargazers_count", 0))),
                }
            )
        return out

    def _fetch_github_readme(self, full_name: str, stars: int | None = None) -> dict[str, Any] | None:
        """[DEEP SCRAPER — Reality Check v3: "300 chữ quảng cáo là không học
        được kiến trúc"]. Lấy NỘI DUNG README THẬT của repo (language-agnostic
        — kiến trúc nằm ở tài liệu, không phải syntax Rust/Python) qua
        api.github.com/{repo}/readme (Accept: raw). Fail per-repo: 1 README
        lỗi không làm chết vòng học.

        [C1 QUARANTINE] Nội dung là DỮ LIỆU KHÔNG TIN CẬY: quét pattern
        injection nhắm vào SCP, dán trust + content_sha256 (provenance mật
        mã). Record QUARANTINED được lưu làm bằng chứng nhưng advise() không
        bao giờ serve vào prompt."""
        _GITHUB_BUCKET.acquire()
        url = f"https://api.github.com/repos/{full_name}/readme"
        content = self._get_raw(url, headers={"Accept": "application/vnd.github.raw"})
        if not content.strip():
            return None
        quarantined, reason = inspect_untrusted(content)
        return {
            "source": "github_readme",
            "kind": "deep_document",
            "name": f"{full_name}/README",
            "url": f"https://github.com/{full_name}",
            "stars": None,
            "trust": "QUARANTINED" if quarantined else "untrusted",
            "reputation": reputation_from_stars(stars),
            "quarantine_reason": reason,
            "content_sha256": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:32],
            # 4000 ký tự đầu đủ chứa section kiến trúc/quick-start của phần
            # lớn README; giới hạn để ledger không phình vô hạn.
            "description": content[:4000],
            "concepts": _extract_concepts(content),
        }

    def _fetch_wikipedia(self, query: str, per_source: int) -> list[dict[str, Any]]:
        _WIKI_BUCKET.acquire()
        url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit="
            + str(int(per_source))
            + "&srsearch="
            + urllib.parse.quote(query)
        )
        data = self._get_json(url)
        out: list[dict[str, Any]] = []
        for item in data.get("query", {}).get("search", [])[:per_source]:
            title = str(item.get("title", ""))
            snippet = _TAG_RE.sub("", str(item.get("snippet", "")))[:400]
            quarantined, reason = inspect_untrusted(snippet)
            out.append(
                {
                    "source": "wikipedia",
                    "kind": "article",
                    "name": title[:200],
                    "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                    "trust": "QUARANTINED" if quarantined else "untrusted",
                    "quarantine_reason": reason,
                    "description": snippet,
                    "reputation": "medium",
                }
            )
        return out

    # ------------------------------------------------------------------
    # Learning cycles
    # ------------------------------------------------------------------
    def _known_content_hashes(self) -> set[str]:
        hashes: set[str] = set()
        if self.ledger_path.exists():
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
                try:
                    digest = json.loads(line).get("content_sha256")
                except (TypeError, ValueError) as exc:
                    # Corrupt ledger line must be visible, not silently dropped.
                    logger.warning("top_systems_learning: corrupt ledger line in %s: %s", self.ledger_path, exc, exc_info=True)
                    continue
                if digest:
                    hashes.add(digest)
        return hashes

    def _append_ledger(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return len(records)

    def learn_topic(self, topic_key: str, per_source: int = 5) -> dict[str, Any]:
        spec = TOPIC_LIBRARY.get(topic_key)
        if not spec:
            return {"ok": False, "topic": topic_key, "reason": "unknown_topic", "known": sorted(TOPIC_LIBRARY)}
        errors: list[str] = []
        records: list[dict[str, Any]] = []
        repos: list[dict[str, Any]] = []
        # NOTE: so sánh bound-method bằng `is` là gotcha Python kinh điển
        # (mỗi lần truy cập self._fetch_github tạo object mới) — phải theo tên.
        for source_name, fetch, query_key in (
            ("github", self._fetch_github, "github_query"),
            ("wikipedia", self._fetch_wikipedia, "wiki_query"),
        ):
            try:
                fetched = fetch(spec[query_key], per_source)
                records.extend(fetched)
                if source_name == "github":
                    repos = fetched
            except Exception as exc:
                logger.debug(f"learn_topic ignored: {exc}", exc_info=True)
                errors.append(f"{fetch.__name__}: {type(exc).__name__}: {str(exc)[:120]}")
        # [DEEP SCRAPER] Không dừng ở 300 chữ description — đọc README thật
        # của từng repo top (fail per-repo, bị TokenBucket chặn nhịp).
        for repo in repos:
            full_name = str(repo.get("name", ""))
            if not full_name:
                continue
            try:
                deep = self._fetch_github_readme(full_name, stars=repo.get("stars"))
                if deep:
                    records.append(deep)
            except Exception as exc:
                logger.debug(f"learn_topic ignored: {exc}", exc_info=True)
                errors.append(f"readme:{full_name}: {type(exc).__name__}: {str(exc)[:120]}")
        # [CURATION STAGE 4] Long-term memory hygiene: nội dung trùng hash
        # (README không đổi) không được ghi lại lần nữa — ledger chỉ chứa tri thức mới.
        seen = self._known_content_hashes()
        unique_records = []
        for record in records:
            record["topic"] = topic_key
            record["collected_at"] = time.time()
            digest = record.get("content_sha256")
            if digest:
                if digest in seen:
                    continue
                seen.add(digest)
            unique_records.append(record)
        records = unique_records
        written = self._append_ledger(records)
        return {
            "ok": len(errors) == 0,
            "topic": topic_key,
            "records": written,
            "deep_readmes": sum(1 for r in records if r.get("source") == "github_readme"),
            "errors": errors,
        }

    def learn_all(self, topics: list[str] | None = None, per_source: int = 5) -> dict[str, Any]:
        keys = [k for k in (topics or TOPIC_LIBRARY.keys()) if k in TOPIC_LIBRARY]
        unknown = [k for k in (topics or []) if k not in TOPIC_LIBRARY]
        results = [self.learn_topic(k, per_source=per_source) for k in keys]
        return {
            "ok": all(r.get("ok") for r in results) if results else False,
            "topics_run": keys,
            "unknown_topics": unknown,
            "records": sum(r.get("records", 0) for r in results),
            "results": results,
            "ledger": str(self.ledger_path),
        }

    # ------------------------------------------------------------------
    # Consumption — what WHY/autofix/learning will consult
    # ------------------------------------------------------------------
    def advise(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        tokens = [t for t in query.lower().split() if t]
        scored: list[tuple[int, dict[str, Any]]] = []
        if self.ledger_path.exists():
            lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines[-2000:]):
                try:
                    record = json.loads(line)
                except (TypeError, ValueError) as exc:
                    # Corrupt ledger line must be visible, not silently dropped.
                    logger.warning("top_systems_learning: corrupt ledger line in %s: %s", self.ledger_path, exc, exc_info=True)
                    continue
                # [C1] Record bị cách ly KHÔNG BAO GIỜ được serve vào prompt.
                if record.get("trust") == "QUARANTINED":
                    continue
                haystack = " ".join(
                    [record.get("topic", ""), record.get("name", ""), record.get("description", "")]
                    + [str(c) for c in (record.get("concepts") or [])]
                ).lower()
                score = sum(1 for t in tokens if t in haystack)
                if score:
                    scored.append((score, record))
        _REP_WEIGHT = {"high": 2.0, "medium": 1.0, "low": 0.25}
        scored.sort(
            key=lambda pair: -(pair[0] + _REP_WEIGHT.get(pair[1].get("reputation", "low"), 0.25))
        )
        return [record for _, record in scored[: max(1, int(limit))]]

    def prune_knowledge(self, keep_days: int = 90, keep_min_reputation: str = "high") -> dict[str, Any]:
        """[MẢNH #23 — Oblivion Engine v1] Trí nhớ vô hạn là căn bệnh: ledger
        không biết quên sẽ bị nghiền nát bởi giáo điều quá khứ. Prune có chọn
        lọc: record quá keep_days ngày bị xóa TRỪ khi reputation cao.
        QUARANTINED record cũ cũng xóa (bằng chứng hết giá trị theo thời gian).
        Toàn bộ nội dung ghi vào .backup trước khi xóa — rollback path luôn mở."""
        if not self.ledger_path.exists():
            return {"pruned": 0, "kept": 0}
        cutoff = time.time() - keep_days * 86400
        rank = {"high": 2, "medium": 1, "low": 0}
        backup = self.ledger_path.with_suffix(".jsonl.backup")
        backup.write_text(self.ledger_path.read_text(encoding="utf-8"), encoding="utf-8")
        kept_lines, pruned = [], 0
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except (TypeError, ValueError) as exc:
                # Corrupt line is kept verbatim (no data loss) but must be visible.
                logger.warning("top_systems_learning: corrupt ledger line kept in %s: %s", self.ledger_path, exc, exc_info=True)
                kept_lines.append(line)
                continue
            collected = float(record.get("collected_at", 0))
            is_old = collected < cutoff
            rep = str(record.get("reputation", "medium"))
            if is_old and rank.get(rep, 1) < rank.get(keep_min_reputation, 2):
                pruned += 1
                continue
            kept_lines.append(line)
        self.ledger_path.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""), encoding="utf-8")
        return {"pruned": pruned, "kept": len(kept_lines), "backup": str(backup)}

    def stats(self) -> dict[str, Any]:
        count = 0
        topics: set[str] = set()
        if self.ledger_path.exists():
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
                try:
                    record = json.loads(line)
                except (TypeError, ValueError) as exc:
                    # Corrupt ledger line must be visible, not silently dropped.
                    logger.warning("top_systems_learning: corrupt ledger line in %s: %s", self.ledger_path, exc, exc_info=True)
                    continue
                count += 1
                if record.get("topic"):
                    topics.add(str(record["topic"]))
        return {
            "records": count,
            "topics_covered": sorted(topics),
            "topic_library": sorted(TOPIC_LIBRARY),
            "ledger": str(self.ledger_path),
            "egress": "disabled" if egress_disabled() else "enabled",
        }


_LEARNER: TopSystemsLearner | None = None
_LEARNER_LOCK = threading.Lock()


def get_learner(data_dir: str = "data") -> TopSystemsLearner:
    global _LEARNER
    if _LEARNER is None:
        with _LEARNER_LOCK:
            if _LEARNER is None:
                _LEARNER = TopSystemsLearner(data_dir=data_dir)
    return _LEARNER
