"""
V104.4.1 — DataPartitioner (Phân loại theo domain + ngày).

Phân loại data theo domain + ngày để mở file nhanh hơn 10-200x.

Cấu trúc:
  data/
  ├── errors/{YYYY-MM-DD}.jsonl        ← TTL 1 ngày theo ngày
  ├── errors/archive/{date}.jsonl.gz   ← > 7 ngày
  ├── bypasses/{YYYY-MM-DD}.jsonl      ← TTL 7 ngày
  ├── bypasses/archive/{date}.jsonl.gz
  ├── knowledge/{domain}.jsonl         ← theo domain
  └── stats/daily_summary.json

Extracted from `core/data_partitioner.py` in Task 10-B (Modularity Refactor B).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("scp.core.data_partitioner")

# V104.4 constants
DATA_DIR = Path(os.environ.get("SCP_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "v13.db"

# Domain -> table mapping
DOMAIN_TABLES = {
    "geography": "knowledge_geography",
    "math": "knowledge_math",
    "chemistry": "knowledge_chemistry",
    "physics": "knowledge_physics",
    "biology": "knowledge_biology",
    "history": "knowledge_history",
    "general": "knowledge_general",
}

# TTL (seconds) per data type
TTL_QUESTION_LOG = 86400          # 1 day
TTL_VERDICT_CACHE = 3600           # 1 hour (HOT cache)
TTL_VERDICT_CACHE_DB = 86400       # 1 day (WARM cache in SQLite)
TTL_ERROR_STORE_DAILY = 86400      # 1 day
TTL_BYPASS_LOG_DAILY = 604800      # 7 days
TTL_PENDING_RESOLUTIONS = 86400   # 1 day

# Domain keyword detection (compact version)
DOMAIN_KEYWORDS = {
    "math": ["tính", "tổng", "hiệu", "tích", "thương", "phương trình",
             "hằng số", "đạo hàm", "tích phân", "logarit", "lũy thừa",
             "số pi", "căn bậc", "phân số", "phần trăm"],
    "geography": ["thủ đô", "diện tích", "dân số", "sông", "núi", "biển",
                  "đỉnh", "quốc gia", "thành phố", "tỉnh", "miền",
                  "khí hậu", "vĩ độ", "kinh độ"],
    "chemistry": ["công thức", "phân tử", "nguyên tố", "hóa chất",
                  "axit", "bazơ", "muối", "khoáng sản", "nhiên liệu",
                  "phản ứng", "oxi hóa", "khối lượng phân tử", "nhiệt độ sôi"],
    "physics": ["vật lý", "hằng số", "planck", "newton", "tốc độ ánh sáng",
                  "lực", "năng lượng", "động lượng", " entropy",
                  "hạt", "lượng tử", "phát minh vật lý", "trường đại học vật lý"],
    "biology": ["động vật", "thực vật", "nhiễm sắc thể", "adn", "arn",
                "quang hợp", "đặc hữu", "vườn quốc gia", "tế bào",
                "phân loại học", "enzyme", "protein"],
    "history": ["độc lập", "chiến tranh", "sáng lập", "lịch sử",
                "vị vua", "triều đại", "cách mạng", "khởi nghĩa"],
}


# [V5.3-WIRE] bypass_encrypt integration — opt-in via SCP_ENCRYPT_BYPASSES=1 env var.
_BYPASS_ENCRYPTOR_SINGLETON = None
_BYPASS_ENCRYPTOR_LOCK = threading.Lock()


def _get_bypass_encryptor():
    """Lazy singleton for BypassEncryptor. Returns None if env var OFF.

    [A1 fail-closed] Khi SCP_ENCRYPT_BYPASSES=1 mà encryptor không init được
    (vd thiếu package cryptography), exception propagates — KHÔNG còn fallback
    plaintext vì write path đã được yêu cầu encrypt (audit A1).
    """
    global _BYPASS_ENCRYPTOR_SINGLETON
    if os.environ.get("SCP_ENCRYPT_BYPASSES", "0") != "1":
        return None
    if _BYPASS_ENCRYPTOR_SINGLETON is None:
        with _BYPASS_ENCRYPTOR_LOCK:
            if _BYPASS_ENCRYPTOR_SINGLETON is None:
                # Lazy import to avoid import-time hard dependency;
                # [A1] init failure now propagates (fail-closed) instead of
                # silently degrading writes to plaintext.
                from scp.security.bypass_encrypt import BypassEncryptor
                _BYPASS_ENCRYPTOR_SINGLETON = BypassEncryptor(data_dir=str(DATA_DIR))
                logger.info("[V5.3-WIRE] BypassEncryptor initialized — bypasses will be encrypted at-rest")
    return _BYPASS_ENCRYPTOR_SINGLETON


def detect_domain(question: str) -> str:
    """V104.4: Detect domain từ câu hỏi để route vào đúng table/file."""
    q_lower = question.lower()
    scores = {d: 0 for d in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower:
                scores[domain] += 1
    best = max(scores, key=scores.get) if max(scores.values()) > 0 else "general"
    return best


def hash_question(question: str) -> str:
    """SHA-256 của question — để cache lookup nhanh."""
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


class DataPartitioner:
    """Phân loại data theo domain + ngày để mở file nhanh hơn 10-200x."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self._ensure_dirs()
        # [FIX-8] write_bypass can be called from multiple threads (e.g.
        # judge pipeline + AttackCrawler). Concurrent append() on the same
        # daily .jsonl file caused interleaved/corrupted JSON lines.
        # Lock the file-write section to serialize.
        self._write_lock = threading.Lock()

    def _ensure_dirs(self) -> None:
        """Tạo cấu trúc thư mục đầy đủ."""
        for sub in ["errors", "errors/archive",
                    "bypasses", "bypasses/archive",
                    "knowledge", "stats"]:
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)

    # === Knowledge JSONL — theo domain ===

    def knowledge_path(self, domain: str) -> Path:
        """Path cho knowledge file của 1 domain."""
        return self.data_dir / "knowledge" / f"{domain}.jsonl"

    def write_knowledge(self, domain: str, record: dict) -> None:
        """Append 1 record vào knowledge/{domain}.jsonl."""
        path = self.knowledge_path(domain)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_knowledge(self, domain: str, limit: int = 100) -> list[dict]:
        """Read N records gần nhất từ 1 domain."""
        path = self.knowledge_path(domain)
        if not path.exists():
            return []
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()]

    # === Errors JSONL — theo ngày ===

    def errors_path(self, date_str: str) -> Path:
        """Path cho errors file của 1 ngày (YYYY-MM-DD)."""
        return self.data_dir / "errors" / f"{date_str}.jsonl"

    def errors_archive_path(self, date_str: str) -> Path:
        return self.data_dir / "errors" / "archive" / f"{date_str}.jsonl.gz"

    def write_error(self, error_record: dict, when: datetime | None = None) -> None:
        """Append 1 error vào errors/{today}.jsonl."""
        if when is None:
            when = datetime.now()
        date_str = when.strftime("%Y-%m-%d")
        path = self.errors_path(date_str)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_record, ensure_ascii=False) + "\n")

    def read_errors_today(self) -> list[dict]:
        """Read errors của hôm nay."""
        today = datetime.now().strftime("%Y-%m-%d")
        path = self.errors_path(today)
        if not path.exists():
            return []
        with open(path, encoding="utf-8", errors="replace") as f:
            return [json.loads(line) for line in f if line.strip()]

    # === Bypasses JSONL — theo ngày ===

    def bypasses_path(self, date_str: str) -> Path:
        return self.data_dir / "bypasses" / f"{date_str}.jsonl"

    def bypasses_archive_path(self, date_str: str) -> Path:
        return self.data_dir / "bypasses" / "archive" / f"{date_str}.jsonl.gz"

    #  DataQualityScoring layer — cùng cấp WHY (2-layer: action + self-verify).
    def _score_data_quality(self, bypass_record: dict) -> tuple[float, str]:
        """Score data quality of a bypass record (0.0-1.0).

        Args:
            bypass_record: dict with fields like attack_type, question, signatures.

        Returns (score, reason).
        - score < 0.3 → reject (don't store)
        - score >= 0.3 → accept
        - On error → 0.5 (neutral, fail-open)
        """
        try:
            if not isinstance(bypass_record, dict):
                return 0.0, "not a dict"

            _score = 0.0
            _checks_passed = 0
            _checks_total = 0
            _reasons = []

            #  Check 1: attack_type valid (not empty, not None)
            _checks_total += 1
            _attack_type = bypass_record.get("attack_type", "")
            if _attack_type and isinstance(_attack_type, str) and _attack_type.strip():
                # Known attack types get bonus
                _known_types = {"ddos", "apt", "supply_chain", "zeroday",
                                "prompt_injection", "sql_injection", "xss",
                                "csrf", "rce", "lfi", "rfi", "phishing"}
                if _attack_type.strip().lower() in _known_types:
                    _score += 0.35  # known type → strong signal
                else:
                    _score += 0.20  # unknown but non-empty → weak signal
                _checks_passed += 1
            else:
                _reasons.append("empty attack_type")

            #  Check 2: question meaningful (>5 chars, not spam)
            _checks_total += 1
            _question = bypass_record.get("question", "")
            if _question and isinstance(_question, str):
                _q_stripped = _question.strip()
                if len(_q_stripped) > 5:
                    # Spam check: low entropy (repeated chars)
                    if len(set(_q_stripped.lower())) >= 4:
                        _score += 0.30
                        _checks_passed += 1
                    else:
                        _reasons.append("question low entropy (spam)")
                else:
                    _reasons.append(f"question too short ({len(_q_stripped)} chars)")
            else:
                _reasons.append("empty question")

            #  Check 3: signature unique (not duplicate in last 100 records)
            _checks_total += 1
            _signatures = bypass_record.get("signatures", "")
            if _signatures:
                # Convert to string for hashing
                _sig_str = str(_signatures).strip()
                if len(_sig_str) >= 3:
                    # Check uniqueness against recent bypasses
                    _is_duplicate = False
                    try:
                        import hashlib as _hashlib
                        # [Task 7-B] TẠI SAO: SHA-256 thay MD5 (CWE-327, B324)
                        # — signature dedup key, không phá logic so sánh hash.
                        _new_hash = _hashlib.sha256(_sig_str.encode("utf-8")).hexdigest()
                        # [FIX-14] Original code only scanned today's file —
                        # an attacker who replayed yesterday's bypass signature
                        # was never flagged as duplicate (quality stayed 1.0).
                        # Scan the last N days (default 7 = TTL_BYPASS_LOG_DAILY)
                        # across all daily files + archives if present.
                        _dup_window_days = int(os.environ.get("SCP_DUP_CHECK_WINDOW_DAYS", "7"))
                        _lines_seen = 0
                        _max_lines = 100  # cap work — same as original "last 100"
                        for _day_offset in range(_dup_window_days):
                            if _is_duplicate or _lines_seen >= _max_lines:
                                break
                            _day = (datetime.now() - timedelta(days=_day_offset)).strftime("%Y-%m-%d")
                            _path = self.bypasses_path(_day)
                            if not _path.exists():
                                continue
                            try:
                                with open(_path, encoding="utf-8", errors="replace") as f:
                                    _day_lines = f.readlines()
                            except Exception as _dup_err:  # noqa: S112
                                # silent-by-design: unreadable day file only weakens dedup; never blocks the write path.
                                logger.debug("shard: bypass day-file read failed for %s (non-fatal): %s", _path, _dup_err, exc_info=True)
                                continue
                            # Only look at the most recent lines across all files
                            _remaining = _max_lines - _lines_seen
                            _slice = _day_lines[-_remaining:] if _remaining > 0 else []
                            # [SCP-DNA-FIX R5-3] Read-path decryption.
                            # When SCP_ENCRYPT_BYPASSES=1, lines on disk are
                            # Fernet tokens, NOT plaintext JSON. Previously the
                            # read path here did `json.loads(_line)` directly,
                            # which silently failed inside `except Exception:
                            # continue` → signature-dedup was broken (every
                            # encrypted line looked "unique" because it could
                            # never be parsed). Now use the public
                            # BypassEncryptor.decrypt_bypass_if_enabled hook.
                            try:
                                from scp.security.bypass_encrypt import BypassEncryptor
                                _read_encryptor = _get_bypass_encryptor()
                            except Exception as _enc_err:
                                logger.debug(f"_score_data_quality ignored: {_enc_err}", exc_info=True)
                                # [A1] Log instead of silent swallow — dedup
                                # degrades to plaintext parse for legacy lines.
                                logger.warning(
                                    f"[V5.3-WIRE] read-path encryptor unavailable: {_enc_err}"
                                )
                                _read_encryptor = None
                            for _line in _slice:
                                _lines_seen += 1
                                try:
                                    if _read_encryptor is not None:
                                        _existing = BypassEncryptor.decrypt_bypass_if_enabled(
                                            _line, _read_encryptor
                                        )
                                    else:
                                        _existing = json.loads(_line)
                                    if not _existing:
                                        # decrypt_bypass_if_enabled returns {}
                                        # on failure — skip silently (matches
                                        # original `except: continue` behavior).
                                        continue
                                    _existing_sig = str(_existing.get("signatures", "")).strip()
                                    _existing_hash = _hashlib.sha256(_existing_sig.encode("utf-8")).hexdigest()
                                    if _existing_hash == _new_hash:
                                        _is_duplicate = True
                                        break
                                except Exception as _line_err:  # noqa: S112
                                    # silent-by-design: unparseable historical line only weakens dedup; never blocks writes.
                                    logger.debug("shard: bypass line parse failed in dedup scan (non-fatal): %s", _line_err, exc_info=True)
                                    continue
                        if not _is_duplicate:
                            _score += 0.35
                            _checks_passed += 1
                        else:
                            _reasons.append(f"signature duplicate (last {_lines_seen} records across {_dup_window_days}d)")
                    except Exception as _dup_err:
                        logger.debug(f" duplicate check failed (fail-open, award half): {_dup_err}", exc_info=True)
                        _score += 0.175  # half credit (can't verify uniqueness)
                        _checks_passed += 1
                else:
                    _reasons.append("signature too short")
            else:
                _reasons.append("empty signatures")

            # Cap at 1.0
            _score = min(_score, 1.0)
            _reason = (
                f"quality={_score:.2f} ({_checks_passed}/{_checks_total} checks passed)"
                + (f"; issues: {'; '.join(_reasons)}" if _reasons else "")
            )
            return _score, _reason

        except Exception as _score_err:
            logger.debug(f" _score_data_quality error (fail-open, 0.5): {_score_err}", exc_info=True)
            return 0.5, f"scoring error (fail-open): {_score_err}"

    #  Audit log helper for V9.1 self-verify layer.
    def _audit_v91(self, event: str, payload: dict) -> None:
        try:
            _entry = {
                "ts": time.time(),
                "engine": "data_partitioner",
                "event": event,
                "payload": payload,
            }
            _audit_path = self.data_dir / "v91_upgrade_audit.jsonl"
            with open(_audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_entry, ensure_ascii=False) + "\n")
        except Exception as _audit_err:
            logger.debug(f" audit log error (fail-open): {_audit_err}", exc_info=True)

    def write_bypass(self, bypass_record: dict, when: datetime | None = None) -> None:
        """Append 1 bypass vào bypasses/{today}.jsonl.

        [V9.0-WHY-GATE] WHY gates data storage — don't store bypasses WHY rejects.

         DataQualityScoring — score quality before storing.
        Quality < 0.3 → reject (don't store junk).
        """
        # [V9.0-WHY-GATE] WHY gates data storage
        try:
            from scp.meta.why_gate import get_why_gate
            _why = get_why_gate().gate(
                action_type="learning",
                action_desc=f"Write bypass: attack_type={bypass_record.get('attack_type','?')}, question={str(bypass_record.get('question',''))[:50]}",
                context=f"signatures={bypass_record.get('signatures','')[:100]}",
            )
            if not _why.allowed:
                logger.info(f"[V9.0-WHY-GATE] Bypass write blocked by WHY: {bypass_record.get('attack_type','?')}")
                return  # don't store — WHY rejected
        except Exception as _why_err:
            logger.debug(f"[V9.0-WHY-GATE] WHY Gate error (non-blocking): {_why_err}", exc_info=True)

        #  DataQualityScoring — self-verify quality trước khi store.
        try:
            _quality, _q_reason = self._score_data_quality(bypass_record)
            if _quality < 0.3:
                logger.info(
                    f" Bypass rejected by quality score "
                    f"(score={_quality:.2f} < 0.3): {_q_reason}"
                )
                self._audit_v91("data_quality_reject", {
                    "attack_type": bypass_record.get("attack_type", "?"),
                    "quality": _quality, "reason": _q_reason,
                })
                return  # don't store — quality too low
            self._audit_v91("data_quality_ok", {
                "attack_type": bypass_record.get("attack_type", "?"),
                "quality": _quality, "reason": _q_reason,
            })
        except Exception as _quality_call_err:
            logger.debug(f" _score_data_quality call error (fail-open): {_quality_call_err}", exc_info=True)

        if when is None:
            when = datetime.now()
        date_str = when.strftime("%Y-%m-%d")
        path = self.bypasses_path(date_str)

        # [V5.3-WIRE] At-rest encryption — opt-in via SCP_ENCRYPT_BYPASSES=1.
        # [A1 fail-closed] Khi encryption được yêu cầu, lỗi init/encrypt phải
        # propagate — KHÔNG fallback plaintext (plaintext write khi env=1 =
        # leak at-rest, audit A1).
        encryptor = _get_bypass_encryptor()
        # [FIX-8] Serialize the file-write — concurrent append() from judge
        # pipeline + AttackCrawler was producing interleaved JSON lines.
        with self._write_lock:
            if encryptor is not None:
                encrypted_bytes = encryptor.encrypt_bypass(bypass_record)
                # Write as utf-8 string (Fernet token is url-safe base64 text)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(encrypted_bytes.decode("utf-8") + "\n")
                return

            # Default path (env OFF) — plaintext JSON, intentional mode
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(bypass_record, ensure_ascii=False) + "\n")

    # === Archive (gzip nén) ===

    def archive_old_files(self, file_type: str, max_age_days: int = 7) -> dict:
        """Archive files > max_age_days: move → gzip → archive/.

        file_type: "errors" or "bypasses"
        Returns: {archived: [...], sizes_before: N, sizes_after: M}
        """
        import gzip
        import shutil

        result = {"archived": [], "before_bytes": 0, "after_bytes": 0}
        cutoff = datetime.now() - timedelta(days=max_age_days)

        if file_type == "errors":
            base_dir = self.data_dir / "errors"
        elif file_type == "bypasses":
            base_dir = self.data_dir / "bypasses"
        else:
            return result

        for f in base_dir.glob("*.jsonl"):
            # Parse date from filename
            try:
                file_date = datetime.strptime(f.stem, "%Y-%m-%d")
            except ValueError as exc:
                # silent-by-design: non-date files in the archive dir are skipped by design.
                logger.debug("shard: skipped non-date file %s: %s", f, exc, exc_info=True)
                continue

            if file_date >= cutoff:
                continue  # Still fresh

            # Move → gzip → archive
            archive_path = base_dir / "archive" / f"{f.stem}.jsonl.gz"
            archive_path.parent.mkdir(parents=True, exist_ok=True)

            result["before_bytes"] += f.stat().st_size

            # Read + compress
            with open(f, "rb") as src:
                with gzip.open(archive_path, "wb", compresslevel=6) as dst:
                    shutil.copyfileobj(src, dst)

            result["after_bytes"] += archive_path.stat().st_size
            result["archived"].append({
                "date": f.stem,
                "original_size": f.stat().st_size,
                "archived_size": archive_path.stat().st_size,
                "compression_ratio": round(
                    f.stat().st_size / max(archive_path.stat().st_size, 1), 2
                ),
            })

            # Remove original
            f.unlink()

        return result

    def get_structure(self) -> dict:
        """Trả về cấu trúc data directory hiện tại + sizes."""
        structure = {
            "data_dir": str(self.data_dir),
            "total_size_mb": 0,
            "by_directory": {},
            "by_domain_knowledge": {},
            "by_day_errors": {},
            "by_day_bypasses": {},
        }

        # Knowledge per domain
        for domain in DOMAIN_KEYWORDS.keys():
            path = self.knowledge_path(domain)
            if path.exists():
                size = path.stat().st_size
                structure["by_domain_knowledge"][domain] = {
                    "size_bytes": size,
                    "exists": True,
                }
                structure["total_size_mb"] += size

        # Errors per day
        for f in (self.data_dir / "errors").glob("*.jsonl"):
            date_str = f.stem
            structure["by_day_errors"][date_str] = f.stat().st_size
            structure["total_size_mb"] += f.stat().st_size

        # Bypasses per day
        for f in (self.data_dir / "bypasses").glob("*.jsonl"):
            date_str = f.stem
            structure["by_day_bypasses"][date_str] = f.stat().st_size
            structure["total_size_mb"] += f.stat().st_size

        structure["total_size_mb"] = round(
            structure["total_size_mb"] / (1024 * 1024), 3
        )
        return structure
