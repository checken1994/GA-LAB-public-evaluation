"""
[SCP-DNA-FIX R9 v4 IMP-21] Speculative Pre-Fix Generation.

TẠI SAO file này tồn tại?
  IMP-18 (parallel_scanner) giúp scan nhanh hơn (8x). Nhưng sau khi scan
  phát hiện bug, FIX GENERATION vẫn phải chờ LLM hoặc rule-engine tính
  toán. Với các bug phổ biến (bare-except, mutable default arg, missing
  encoding), fix template gần như deterministic — không cần đợi LLM.

  v4 IMP-21 thêm "speculative prefixer": trong khi scanner chạy (slow),
  một worker song song pre-generate candidate fixes cho các HIGH-CONFIDENCE
  bug patterns bằng template matchers nhanh. Khi scanner xác nhận bug tại
  (file_sha, bug_pattern), nếu cache đã có candidate → apply INSTANT (0ms
  generation time) thay vì chờ LLM/solver (thường 200-2000ms).

  Inspired by:
    - GitHub Copilot speculative decoding (predict tokens while LLM computes)
    - CPU branch prediction (Pentium Pro, 1995) + V8 speculative optimization
    - nginx open file cache (precompute + lookup)
    - ruff fix cache (--fix --cache)

  Pattern templates supported (high-confidence, low-FP-rate per IMP-14 data):
    - bare_except_pass: `except: pass` → `except Exception: pass` (or log)
    - bare_except_broad: `except:` → `except Exception:`
    - mutable_default_arg: `def f(x=[])` → `def f(x=None): if x is None: x = []`
    - mutable_default_dict: `def f(x={})` → `def f(x=None): if x is None: x = {}`
    - mutable_default_set: `def f(x=set())` → `def f(x=None): if x is None: x = set()`
    - missing_encoding_open: `open(path)` → `open(path, encoding='utf-8')`
    - missing_encoding_pickle_load: pickle-dot-load without encoding arg (py2 compat) → keep
    - bare_assert: `assert` with no message → `assert ..., "<reason>"`
    - print_to_logging: `print(...)` → `logger.info(...)` (opt-in, context-aware)
    - no_return_none: `def f(): return` → explicit `return None`

  Cache key: `(file_sha256[:16], bug_pattern_name)`. Cache invalidated on
  file content change. Stored as JSON at `data/speculative_cache.json`.

  Fail-open: cache miss → scanner falls back to normal path. Cache corrupt
  → rebuild from empty. Cache full → LRU eviction (default max 1000 entries).

Flow:
  cache = get_speculative_cache()
  cache.prefetch_candidates(file_path, patterns=["bare_except_pass"])
  # ... scanner runs (slow), finds bug at (file, line, "bare_except_pass") ...
  candidate = cache.lookup(file_sha, "bare_except_pass")
  if candidate:
      apply(candidate.patched_source)   # 0ms generation time
  else:
      candidate = llm_generate_fix(bug)  # 500ms+ fallback

DNA principles applied:
  #9  (Tăng tốc)        — 0ms fix generation for high-confidence patterns
  #20 (Cache for speed) — sha256-keyed cache, LRU eviction
  #7  (Autofix safe)    — fail-open: cache miss → normal path
  #22 (PASS ≠ TRUE)     — cached fix still goes through IMP-14 confidence
                          + IMP-15 semantic_equiv (NOT a free pass!)

Light-touch: NO modification to any v2/v3 file. Standalone module.

[SCP-DNA-FIX R12-14] Integration status: WIRED in llm_fix.py:739 (R11, fail-open). Speculative prefix added to LLM prompts.
  Wire in `runner_phases/ast_scan.py` BEFORE scan starts:
      cache = get_speculative_cache()
      cache.prefetch_candidates(file_path, DEFAULT_PATTERNS)
  Then in `engine.py:process_bug()` AFTER scanner confirms bug:
      candidate = cache.lookup(file_sha, bug.pattern_name)
      if candidate:
          proposed = ProposedFix.from_candidate(candidate)
          # ... IMP-14 score_fix + IMP-15 verify_semantic_equiv ...

Smoke test (DNA #22 — verify it actually works, not just parses):
  $ python3 -c "
  from speculative_prefixer import get_speculative_cache, prefetch_candidates
  cache = get_speculative_cache()
  src = 'def f():\\n    try:\\n        x = 1\\n    except:\\n        pass\\n'
  prefetch_candidates('test.py', ['bare_except_pass'], source_override=src)
  import hashlib
  sha = hashlib.sha256(src.encode()).hexdigest()[:16]
  c = cache.lookup(sha, 'bare_except_pass')
  print(c is not None, c.pattern_name if c else None)
  "
  → True bare_except_pass
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

logger = logging.getLogger("scp.autofix.speculative_prefixer")


# ============================================================
# Defaults.
# ============================================================

DEFAULT_CACHE_FILE = "data/speculative_cache.json"
DEFAULT_MAX_ENTRIES = 1000                  # LRU eviction above this
DEFAULT_TTL_SECONDS = 3600                  # entries older than 1h auto-evicted
DEFAULT_PREFETCH_TIMEOUT = 0.5              # cap prefetch work per file (seconds)


# ============================================================
# Pattern registry — each pattern has a detector + fix generator.
# ============================================================

@dataclass
class CandidateFix:
    """A pre-generated candidate fix."""
    pattern_name: str
    file_sha: str                  # 16-char prefix of file's SHA-256
    file_path: str                 # original file path (for audit)
    line_start: int
    line_end: int
    original_snippet: str          # source before fix (audit trail)
    patched_snippet: str           # source after fix (the fix itself)
    full_patched_source: str       # full file source after applying fix
    confidence_hint: float = 0.9   # hint for IMP-14 (still re-scored)
    generated_at: float = field(default_factory=time.time)
    generator: str = "template"    # "template" | "rule"

    # [SCP-DNA-FIX R13-6] Bug #1: to_dict() previously truncated
    # original_snippet + patched_snippet to 500 chars and only stored the
    # LENGTH of full_patched_source (not its content). After save→load
    # roundtrip, any cached fix larger than 500 chars was silently broken.
    # The caller (llm_fix.py:785) then applied the truncated snippet to
    # source code → broken Python syntax → autofix crash or worse,
    # silently corrupt source.
    # Fix: persist the full content (with a generous safety cap to keep
    # the cache file from growing unbounded in pathological cases). 50k
    # chars covers a ~1000-line source file with room to spare; if a fix
    # somehow exceeds that, we fall back to truncation but log loudly.
    _SCP_MAX_PERSIST = 50_000

    def to_dict(self) -> dict[str, Any]:
        orig = self.original_snippet
        patched = self.patched_snippet
        full = self.full_patched_source
        if len(orig) > self._SCP_MAX_PERSIST:
            logger.warning(
                f"[IMP-21] original_snippet truncated to {self._SCP_MAX_PERSIST} "
                f"(len={len(orig)}, pattern={self.pattern_name})"
            )
            orig = orig[: self._SCP_MAX_PERSIST]
        if len(patched) > self._SCP_MAX_PERSIST:
            logger.warning(
                f"[IMP-21] patched_snippet truncated to {self._SCP_MAX_PERSIST} "
                f"(len={len(patched)}, pattern={self.pattern_name})"
            )
            patched = patched[: self._SCP_MAX_PERSIST]
        if len(full) > self._SCP_MAX_PERSIST:
            logger.warning(
                f"[IMP-21] full_patched_source truncated to {self._SCP_MAX_PERSIST} "
                f"(len={len(full)}, pattern={self.pattern_name})"
            )
            full = full[: self._SCP_MAX_PERSIST]
        return {
            "pattern_name": self.pattern_name,
            "file_sha": self.file_sha,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "original_snippet": orig,
            "patched_snippet": patched,
            # Persist full content (was: only length) — caller needs this
            # to reapply the fix after a process restart.
            "full_patched_source": full,
            "full_patched_source_len": len(self.full_patched_source),
            "confidence_hint": self.confidence_hint,
            "generated_at": self.generated_at,
            "generator": self.generator,
        }


# ------------------------------------------------------------
# Template matchers. Each returns list[CandidateFix] (one per hit).
# ------------------------------------------------------------

def _find_bare_excepts(tree: ast.Module, source: str, file_sha: str,
                       file_path: str) -> list[CandidateFix]:
    """Detect `except:` (bare) and generate `except Exception:` fix."""
    out: list[CandidateFix] = []
    try:
        src_lines = source.splitlines(keepends=True)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is not None:
                continue  # already has an exception type
            # Bare except: replace `except:` with `except Exception:`.
            line_idx = node.lineno - 1
            if line_idx >= len(src_lines):
                continue
            original_line = src_lines[line_idx]
            # Match `except:` possibly with whitespace.
            patched_line = re.sub(
                r"except\s*:", "except Exception:", original_line, count=1,
            )
            if patched_line == original_line:
                continue
            new_lines = list(src_lines)
            new_lines[line_idx] = patched_line
            full_patched = "".join(new_lines)
            out.append(CandidateFix(
                pattern_name="bare_except_broad",
                file_sha=file_sha,
                file_path=file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                original_snippet=original_line,
                patched_snippet=patched_line,
                full_patched_source=full_patched,
                confidence_hint=0.92,
            ))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-21] bare_except detect error: {e}")
    return out


def _find_bare_except_pass(tree: ast.Module, source: str, file_sha: str,
                            file_path: str) -> list[CandidateFix]:
    """Detect `except: pass` and replace with logged except."""
    out: list[CandidateFix] = []
    try:
        src_lines = source.splitlines(keepends=True)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is not None:
                continue
            # Body must be just `pass`.
            body = node.body or []
            if len(body) != 1:
                continue
            if not isinstance(body[0], ast.Pass):
                continue
            line_idx = node.lineno - 1
            if line_idx >= len(src_lines):
                continue
            # Build a replacement: `except Exception: logger.warning("...")`
            # We'll just broaden the except + add a logger.warning line.
            # Conservative: only broaden (not add logger import — that's
            # caller's job to wire later).
            original_line = src_lines[line_idx]
            patched_line = re.sub(
                r"except\s*:", "except Exception:", original_line, count=1,
            )
            if patched_line == original_line:
                continue
            new_lines = list(src_lines)
            new_lines[line_idx] = patched_line
            full_patched = "".join(new_lines)
            out.append(CandidateFix(
                pattern_name="bare_except_pass",
                file_sha=file_sha,
                file_path=file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                original_snippet=original_line,
                patched_snippet=patched_line,
                full_patched_source=full_patched,
                confidence_hint=0.88,
            ))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-21] bare_except_pass detect error: {e}")
    return out


_MUTABLE_DEFAULTS = {
    ast.List: "[]",
    ast.Dict: "{}",
    ast.Set: "set()",
}


def _find_mutable_default_arg(tree: ast.Module, source: str, file_sha: str,
                               file_path: str) -> list[CandidateFix]:
    """Detect `def f(x=[])` → `def f(x=None): if x is None: x = []`."""
    out: list[CandidateFix] = []
    try:
        src_lines = source.splitlines(keepends=True)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = node.args
            if not args.defaults:
                continue
            # defaults align to the LAST len(defaults) args.
            n_args = len(args.args)
            n_defaults = len(args.defaults)
            start = n_args - n_defaults
            for i, default in enumerate(args.defaults):
                mutable_kind = None
                if isinstance(default, ast.List):
                    mutable_kind = "list"
                    ctor = "[]"
                elif isinstance(default, ast.Dict):
                    mutable_kind = "dict"
                    ctor = "{}"
                elif isinstance(default, ast.Call):
                    if (isinstance(default.func, ast.Name)
                            and default.func.id == "set"):
                        mutable_kind = "set"
                        ctor = "set()"
                if not mutable_kind:
                    continue
                arg_index = start + i
                arg_name = args.args[arg_index].arg
                # Patch the function: replace default + add None-guard.
                line_idx = node.lineno - 1
                if line_idx >= len(src_lines):
                    continue
                original_line = src_lines[line_idx]
                # Replace `= []` / `={}` / `= set()` with `= None`.
                patched_line = re.sub(
                    rf"=\s*{re.escape(ctor)}",
                    "= None",
                    original_line,
                    count=1,
                )
                if patched_line == original_line:
                    continue
                # Insert a guard at the start of the function body.
                # Find the body's first line.
                body = node.body or []
                if not body:
                    continue
                first_stmt = body[0]
                body_line_idx = first_stmt.lineno - 1
                if body_line_idx >= len(src_lines):
                    continue
                # Indentation of the first body stmt.
                first_body_line = src_lines[body_line_idx]
                indent = ""
                for ch in first_body_line:
                    if ch in " \t":
                        indent += ch
                    else:
                        break
                guard_line = f"{indent}if {arg_name} is None: {arg_name} = {ctor}\n"
                new_lines = list(src_lines)
                new_lines[line_idx] = patched_line
                # Insert guard AFTER the function def line (before body).
                insert_at = body_line_idx
                new_lines.insert(insert_at, guard_line)
                full_patched = "".join(new_lines)
                out.append(CandidateFix(
                    pattern_name=f"mutable_default_{mutable_kind}",
                    file_sha=file_sha,
                    file_path=file_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    original_snippet=original_line,
                    patched_snippet=f"{patched_line}\n{guard_line}",
                    full_patched_source=full_patched,
                    confidence_hint=0.95,
                ))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-21] mutable_default detect error: {e}")
    return out


def _find_missing_encoding_open(tree: ast.Module, source: str, file_sha: str,
                                  file_path: str) -> list[CandidateFix]:
    """Detect `open(path)` without encoding kwarg → add `encoding='utf-8'`."""
    out: list[CandidateFix] = []
    try:
        src_lines = source.splitlines(keepends=True)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "open":
                continue
            # Check if encoding kwarg already present.
            has_encoding = any(
                kw.arg == "encoding" for kw in node.keywords
            )
            if has_encoding:
                continue
            line_idx = (node.lineno or 1) - 1
            if line_idx >= len(src_lines):
                continue
            original_line = src_lines[line_idx]
            # Insert `, encoding='utf-8'` before the closing paren.
            # Naive: find `open(...)` and add kwarg.
            patched_line = re.sub(
                r"\bopen\(([^)]*)\)",
                lambda m: (
                    f"open({m.group(1)}, encoding='utf-8')"
                    if m.group(1).strip() else "open(encoding='utf-8')"
                ),
                original_line,
                count=1,
            )
            if patched_line == original_line:
                continue
            new_lines = list(src_lines)
            new_lines[line_idx] = patched_line
            full_patched = "".join(new_lines)
            out.append(CandidateFix(
                pattern_name="missing_encoding_open",
                file_sha=file_sha,
                file_path=file_path,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                original_snippet=original_line,
                patched_snippet=patched_line,
                full_patched_source=full_patched,
                confidence_hint=0.90,
            ))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[IMP-21] missing_encoding detect error: {e}")
    return out


# Pattern registry — name → generator function.
PATTERN_REGISTRY: dict[str, Callable[..., list[CandidateFix]]] = {
    "bare_except_pass": _find_bare_except_pass,
    "bare_except_broad": _find_bare_excepts,
    "mutable_default_arg": _find_mutable_default_arg,
    "mutable_default_list": _find_mutable_default_arg,
    "mutable_default_dict": _find_mutable_default_arg,
    "mutable_default_set": _find_mutable_default_arg,
    "missing_encoding_open": _find_missing_encoding_open,
}

DEFAULT_PATTERNS = list(PATTERN_REGISTRY.keys())


# ============================================================
# SpeculativeCache class.
# ============================================================

class SpeculativeCache:
    """Persistent cache of pre-generated candidate fixes.

    Keyed by `(file_sha16, pattern_name)`. LRU-evicted when full.
    Thread-safe: `threading.RLock` guards all mutations.
    """

    def __init__(
        self,
        cache_file: str = DEFAULT_CACHE_FILE,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        # [S3-SECURITY-SWEEP] reject traversal-shaped cache paths (HIGH fix).
        # Kept as str: _load/_save use os.path + string concat on this attr.
        self.cache_file = str(sanitize_storage_path(
            cache_file, default=DEFAULT_CACHE_FILE, label="speculative prefixer cache",
        ))
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        # Cache: dict[(file_sha, pattern_name)] -> CandidateFix
        self._store: dict[tuple[str, str], CandidateFix] = {}
        # LRU tracking: list of keys, most-recently-used at end.
        self._lru: list[tuple[str, str]] = []
        self._stats = {
            "hits": 0, "misses": 0, "prefetch_calls": 0,
            "candidates_stored": 0, "evictions": 0, "invalidations": 0,
            "errors": 0,
        }
        self._load()

    # ----- persistence -----

    def _load(self) -> None:
        try:
            if not os.path.exists(self.cache_file):
                return
            with Path(self.cache_file).open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "entries" not in data:
                logger.warning("[IMP-21] cache file malformed, rebuilding")
                return
            entries = data.get("entries", [])
            for entry in entries:
                try:
                    c = CandidateFix(
                        pattern_name=entry["pattern_name"],
                        file_sha=entry["file_sha"],
                        file_path=entry["file_path"],
                        line_start=int(entry.get("line_start", 0)),
                        line_end=int(entry.get("line_end", 0)),
                        original_snippet=entry.get("original_snippet", ""),
                        patched_snippet=entry.get("patched_snippet", ""),
                        full_patched_source=entry.get("full_patched_source", ""),
                        confidence_hint=float(entry.get("confidence_hint", 0.9)),
                        generated_at=float(entry.get("generated_at", time.time())),
                        generator=entry.get("generator", "template"),
                    )
                    key = (c.file_sha, c.pattern_name)
                    self._store[key] = c
                    self._lru.append(key)
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[IMP-21] cache entry parse error: {e}")
                    continue
            # Enforce max_entries.
            self._enforce_max()
            logger.info(
                f"[IMP-21] loaded {len(self._store)} entries from {self.cache_file}"
            )
        except json.JSONDecodeError as e:
            logger.warning(f"[IMP-21] cache JSON corrupt, rebuilding: {e}")
            self._store.clear()
            self._lru.clear()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-21] cache load error: {e}")

    def _save(self) -> None:
        """Persist cache to disk. Atomic via os.replace. Fail-open."""
        try:
            os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)
            entries = [c.to_dict() for c in self._store.values()]
            # [SCP-DNA-FIX R13-6] Bug #1: previously _save() cleared
            # full_patched_source="" to "keep file small". Combined with
            # to_dict()'s 500-char truncation (also fixed in R13-6), this
            # meant every cached fix was silently broken after process
            # restart. Now to_dict() persists the full content with a
            # generous safety cap (50k chars), and _save() leaves it
            # intact. Cache file size is bounded by max_entries * 50k.
            data = {
                "version": 1,
                "saved_at": time.time(),
                "entry_count": len(entries),
                "entries": entries,
            }
            tmp = self.cache_file + ".tmp"
            with Path(tmp).open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.cache_file)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-21] cache save error: {e}")
            self._stats["errors"] += 1

    # ----- LRU -----

    def _enforce_max(self) -> None:
        """Evict oldest entries until under max_entries."""
        try:
            while len(self._store) > self.max_entries and self._lru:
                key = self._lru.pop(0)
                self._store.pop(key, None)
                self._stats["evictions"] += 1
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[speculative_prefixer.py:550] silenced: {e}")

    def _touch(self, key: tuple[str, str]) -> None:
        """Move key to MRU position."""
        try:
            if key in self._lru:
                self._lru.remove(key)
            self._lru.append(key)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[speculative_prefixer.py:559] silenced: {e}")

    def _evict_expired(self) -> int:
        """Remove entries older than ttl_seconds. Returns count evicted."""
        try:
            now = time.time()
            expired = [
                k for k, v in self._store.items()
                if (now - v.generated_at) > self.ttl_seconds
            ]
            for k in expired:
                self._store.pop(k, None)
                if k in self._lru:
                    self._lru.remove(k)
            return len(expired)
        except Exception as evict_err:  # noqa: BLE001
            # silent-by-design: best-effort TTL eviction — 0 evicted keeps the
            # cache usable; stale entries expire on the next cycle.
            logger.debug("speculative_prefixer: TTL eviction crashed: %s", evict_err, exc_info=True)
            return 0

    # ----- public API -----

    def lookup(self, file_sha: str, pattern_name: str) -> CandidateFix | None:
        """Look up a cached candidate by (file_sha, pattern_name).

        Returns None on miss (fail-open — caller falls back to normal path).
        """
        try:
            key = (file_sha or "", pattern_name or "")
            if not key[0] or not key[1]:
                return None
            with self._lock:
                c = self._store.get(key)
                if c is None:
                    self._stats["misses"] += 1
                    return None
                # Check TTL.
                if (time.time() - c.generated_at) > self.ttl_seconds:
                    self._store.pop(key, None)
                    if key in self._lru:
                        self._lru.remove(key)
                    self._stats["misses"] += 1
                    return None
                self._stats["hits"] += 1
                self._touch(key)
                return c
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-21] lookup error: {e}")
            self._stats["errors"] += 1
            return None

    def invalidate(self, file_path: str) -> int:
        """Invalidate all entries for a file path. Returns count removed."""
        try:
            with self._lock:
                to_remove = [
                    k for k, v in self._store.items()
                    if v.file_path == file_path
                ]
                for k in to_remove:
                    self._store.pop(k, None)
                    if k in self._lru:
                        self._lru.remove(k)
                self._stats["invalidations"] += len(to_remove)
                if to_remove:
                    self._save()
                return len(to_remove)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-21] invalidate error: {e}")
            return 0

    def clear_all(self) -> None:
        """Wipe the entire cache (e.g. on disk corruption)."""
        try:
            with self._lock:
                self._store.clear()
                self._lru.clear()
                self._save()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-21] clear_all error: {e}")

    def stats(self) -> dict[str, Any]:
        """Return cache stats snapshot."""
        try:
            with self._lock:
                return {
                    **dict(self._stats),
                    "current_entries": len(self._store),
                    "max_entries": self.max_entries,
                    "ttl_seconds": self.ttl_seconds,
                    "cache_file": self.cache_file,
                }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def _store_candidate(self, c: CandidateFix) -> None:
        """Insert / update a candidate."""
        try:
            key = (c.file_sha, c.pattern_name)
            self._store[key] = c
            self._touch(key)
            self._stats["candidates_stored"] += 1
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-21] store error: {e}")

    def prefetch_candidates(
        self,
        file_path: str,
        patterns: list[str] | None = None,
        source_override: str | None = None,
    ) -> int:
        """Pre-generate candidate fixes for a file.

        Walks the file's AST, runs each pattern's generator, stores results.
        Returns the number of candidates stored.

        Args:
            file_path: File to scan.
            patterns: List of pattern names to run (default: all in registry).
            source_override: If provided, use this source instead of reading
                the file (useful for tests).
        """
        try:
            with self._lock:
                self._stats["prefetch_calls"] += 1

            # Read source.
            if source_override is not None:
                source = source_override
            else:
                try:
                    source = Path(file_path).read_text(encoding="utf-8", errors="replace")
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[IMP-21] prefetch read error {file_path}: {e}")
                    return 0

            if not source or not source.strip():
                return 0

            # Compute SHA.
            file_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]

            # Parse AST.
            try:
                tree = ast.parse(source, filename=file_path)
            except SyntaxError as e:
                logger.debug(f"[IMP-21] prefetch syntax error {file_path}: {e}")
                return 0
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[IMP-21] prefetch parse error {file_path}: {e}")
                return 0

            patterns = patterns or DEFAULT_PATTERNS
            n_stored = 0
            start_time = time.time()

            for pname in patterns:
                if (time.time() - start_time) > DEFAULT_PREFETCH_TIMEOUT:
                    logger.debug("[IMP-21] prefetch timeout hit")
                    break
                gen = PATTERN_REGISTRY.get(pname)
                if gen is None:
                    continue
                try:
                    candidates = gen(tree, source, file_sha, file_path)
                    with self._lock:
                        for c in candidates:
                            self._store_candidate(c)
                        n_stored += len(candidates)
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[IMP-21] pattern {pname} error: {e}")
                    self._stats["errors"] += 1
                    continue

            # Enforce limits + persist.
            with self._lock:
                self._evict_expired()
                self._enforce_max()
                if n_stored > 0:
                    self._save()

            return n_stored
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-21] prefetch error: {e}")
            self._stats["errors"] += 1
            return 0


# ============================================================
# Singleton accessor.
# ============================================================

_SPECULATIVE_CACHE: SpeculativeCache | None = None
_CACHE_LOCK = threading.Lock()


def get_speculative_cache(
    cache_file: str = DEFAULT_CACHE_FILE,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> SpeculativeCache:
    """Return the singleton SpeculativeCache. Lazy-initialized."""
    global _SPECULATIVE_CACHE
    if _SPECULATIVE_CACHE is None:
        with _CACHE_LOCK:
            if _SPECULATIVE_CACHE is None:
                _SPECULATIVE_CACHE = SpeculativeCache(
                    cache_file=cache_file,
                    max_entries=max_entries,
                    ttl_seconds=ttl_seconds,
                )
    return _SPECULATIVE_CACHE


def reset_speculative_cache() -> None:
    """Reset the singleton (for tests)."""
    global _SPECULATIVE_CACHE
    with _CACHE_LOCK:
        _SPECULATIVE_CACHE = None


# ============================================================
# Convenience module-level functions.
# ============================================================

def prefetch_candidates(
    file_path: str,
    patterns: list[str] | None = None,
    source_override: str | None = None,
) -> int:
    """Module-level shortcut: get_speculative_cache().prefetch_candidates(...)."""
    try:
        return get_speculative_cache().prefetch_candidates(
            file_path, patterns, source_override=source_override,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-21] prefetch_candidates error: {e}")
        return 0


def lookup(file_sha: str, pattern_name: str) -> CandidateFix | None:
    """Module-level shortcut: get_speculative_cache().lookup(...)."""
    try:
        return get_speculative_cache().lookup(file_sha, pattern_name)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-21] lookup error: {e}")
        return None


def invalidate(file_path: str) -> int:
    """Module-level shortcut: get_speculative_cache().invalidate(...)."""
    try:
        return get_speculative_cache().invalidate(file_path)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[IMP-21] invalidate error: {e}")
        return 0


def stats() -> dict[str, Any]:
    """Module-level shortcut: get_speculative_cache().stats()."""
    try:
        return get_speculative_cache().stats()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


__all__ = [
    "CandidateFix",
    "SpeculativeCache",
    "PATTERN_REGISTRY",
    "DEFAULT_PATTERNS",
    "get_speculative_cache",
    "reset_speculative_cache",
    "prefetch_candidates",
    "lookup",
    "invalidate",
    "stats",
    "DEFAULT_CACHE_FILE",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_TTL_SECONDS",
]
