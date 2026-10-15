"""[S3-SECURITY-SWEEP] Path guard for autofix storage paths.

TẠI SAO module này tồn tại?
  Mimosa sweep 3 flagged HIGH path-traversal findings across the autofix
  cache/log/registry writers: caller/config-supplied paths flow into
  file writers and ``os.replace`` without normalization or containment.
  A hostile or buggy caller (finding-driven filename, corrupted config) could
  point those writers outside the intended directory.

  ROOT fix: every storage path used by a cache/log/registry writer is
  normalized here:
    - explicit parent-directory traversal components → REJECTED, fall back to
      the module's safe default (fail-closed for writes),
    - result is always an absolute, resolved Path,
    - untrusted filename stems (e.g. shadow files derived from finding
      filenames) are reduced to a safe charset with a sha256 fallback.

  Behavior for legitimate paths (absolute tmp dirs, relative project paths)
  is unchanged — only traversal-shaped input is rejected.

DNA principles applied:
  #4  (Constitution KILL) — traversal components never reach a write sink
  #7  (Autofix safe)      — reject → fall back to default, engine keeps working
  #9  (No harm)           — writes stay inside the intended directory
  #26 (Reality > Model)   — tests/T03_capability/test_security_sweep_s3.py
                            proves traversal is rejected at runtime
"""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("scp.autofix.path_guard")


def sanitize_storage_path(
    candidate: Any,
    *,
    default: str | Path,
    label: str = "storage path",
) -> Path:
    """Normalize a caller-supplied cache/log/registry path.

    Args:
        candidate: the raw path (str / Path / anything Path() accepts).
        default:   safe fallback path used when the candidate is unusable.
        label:     human-readable role of the file (for the audit warning).

    Returns:
        Absolute resolved Path, never containing ``..`` components.

    Rules:
        - ``..`` anywhere in the raw path → reject + fall back to ``default``
          (a legitimate cache/log path never needs to climb directories).
        - empty / non-path-like input → fall back to ``default``.
    """
    try:
        raw = Path(candidate)
    except (TypeError, ValueError):
        logger.warning(
            "[path_guard] %s: unusable path %r — using default %s",
            label, candidate, default,
        )
        return Path(default).resolve()
    if ".." in raw.parts or str(candidate).strip() == "":
        logger.warning(
            "[path_guard] %s: traversal-shaped path %r rejected — using default %s",
            label, str(candidate), default,
        )
        return Path(default).resolve()
    return raw.resolve()


def ensure_within(base: str | Path, candidate: str | Path) -> Path | None:
    """Resolve ``candidate`` and return it only if it stays inside ``base``.

    Returns None when the resolved path escapes the base directory — callers
    must treat None as "write refused" (fail-closed).
    """
    base_resolved = Path(base).resolve()
    try:
        cand_resolved = Path(candidate).resolve()
    except (TypeError, ValueError, OSError):
        # silent-by-design: documented fail-closed contract — None = "write refused".
        return None
    if not cand_resolved.is_relative_to(base_resolved):
        return None
    return cand_resolved


_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]")


def sanitize_filename_stem(
    name: str | None,
    *,
    fallback: str = "shadow",
    max_len: int = 40,
) -> str:
    """Turn an untrusted original filename into a safe filename stem.

    Used when a file name derived from external data (findings, bug reports)
    becomes part of a path we write to. Directory components are dropped,
    everything outside ``[A-Za-z0-9_-]`` becomes ``_``; when nothing usable
    survives (or the input was traversal-shaped), a sha256 prefix of the raw
    name is used so distinct inputs still map to distinct files.
    """
    raw = str(name or "")
    try:
        stem = Path(raw).stem
    except (TypeError, ValueError) as stem_err:
        # silent-by-design: documented default — unusable stem falls through to
        # the sha256-prefix fallback below (distinct inputs stay distinct).
        logger.debug("path_guard: stem extraction failed for %r: %s", raw, stem_err, exc_info=True)
        stem = ""
    cleaned = _FILENAME_SAFE_RE.sub("_", stem)
    cleaned = cleaned.strip("._-")
    if not cleaned:
        cleaned = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:12]
        if not cleaned:
            cleaned = fallback
    return cleaned[:max_len]


def sanitize_comment_text(text: str, max_len: int = 100) -> str:
    """Make an untrusted string safe to embed inside a generated ``#`` comment.

    Strips line breaks and control characters so injected newlines cannot turn
    a comment into executable code inside a generated source file.
    """
    cleaned = re.sub(r"[\r\n\x00-\x1f\x7f]", " ", str(text or ""))
    return cleaned[:max_len]


__all__ = [
    "sanitize_storage_path",
    "ensure_within",
    "sanitize_filename_stem",
    "sanitize_comment_text",
]
