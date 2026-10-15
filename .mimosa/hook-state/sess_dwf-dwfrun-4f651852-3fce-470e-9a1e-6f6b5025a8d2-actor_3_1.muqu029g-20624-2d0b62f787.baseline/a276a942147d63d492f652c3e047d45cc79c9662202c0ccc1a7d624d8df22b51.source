from __future__ import annotations

import ast
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class SemanticGateDecision:
    status: str
    promotion_allowed: bool
    reasons: tuple[str, ...]
    source_sha256: str | None = None
    target_is_bare_except_pass: bool | None = None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _find_handler(source: str, path: str, line: int) -> ast.ExceptHandler | None:
    tree = ast.parse(source, filename=path)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and node.lineno == line
    ]
    return matches[0] if len(matches) == 1 else None


def evaluate_candidate(
    *,
    source_path: str | Path,
    source_snapshot: str | None,
    expected_source_sha256: str | None,
    bug_type: str,
    bug_line: int,
    patched_source: str | None,
    semantic_tests_passed: bool,
    independent_external_evidence: bool,
) -> SemanticGateDecision:
    reasons: list[str] = []
    path = Path(source_path)
    if not source_snapshot:
        reasons.append("REJECT_NO_SOURCE_SNAPSHOT")
    if expected_source_sha256 is None:
        reasons.append("REJECT_NO_EXPECTED_SOURCE_HASH")
    if patched_source is None:
        reasons.append("REJECT_NO_PATCHED_SOURCE")
    if not path.exists():
        reasons.append("REJECT_SOURCE_PATH_MISSING")
        return SemanticGateDecision("REJECT", False, tuple(reasons))

    try:
        current_source = path.read_text(encoding="utf-8")
    except OSError:
        logger.debug('evaluate_candidate: OSError ignored', exc_info=True)
        reasons.append("REJECT_SOURCE_READ_FAILED")
        return SemanticGateDecision("REJECT", False, tuple(reasons))
    current_hash = _sha256(current_source)
    if expected_source_sha256 is not None and current_hash != expected_source_sha256:
        reasons.append("REJECT_SOURCE_HASH_MISMATCH")
    if source_snapshot is not None and _sha256(source_snapshot) != current_hash:
        reasons.append("REJECT_SNAPSHOT_NOT_CURRENT_SOURCE")

    target_is_bare = None
    try:
        handler = _find_handler(current_source, str(path), bug_line)
        target_is_bare = bool(
            handler is not None
            and handler.type is None
            and len(handler.body) == 1
            and isinstance(handler.body[0], ast.Pass)
        )
        if bug_type == "BareExceptPass" and not target_is_bare:
            reasons.append("REJECT_CLASSIFICATION_MISMATCH")
    except SyntaxError:
        logger.debug('evaluate_candidate: SyntaxError ignored', exc_info=True)
        reasons.append("REJECT_SOURCE_SYNTAX_ERROR")

    if patched_source is not None:
        try:
            ast.parse(patched_source, filename=str(path))
        except SyntaxError:
            logger.debug('evaluate_candidate: SyntaxError ignored', exc_info=True)
            reasons.append("REJECT_PATCH_SYNTAX_ERROR")
    if not semantic_tests_passed:
        reasons.append("REJECT_SEMANTIC_TEST_NOT_PROVEN")
    if not independent_external_evidence:
        reasons.append("REJECT_NO_INDEPENDENT_EXTERNAL_EVIDENCE")

    if reasons:
        return SemanticGateDecision("REJECT", False, tuple(reasons), current_hash, target_is_bare)
    return SemanticGateDecision("PROMOTION_ELIGIBLE", True, (), current_hash, target_is_bare)


__all__ = ["SemanticGateDecision", "evaluate_candidate"]
