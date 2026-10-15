"""Goal/policy Drift Guard (26-P0.11).

Normal self-modification cannot silently weaken DNA, tests, capability/security,
evidence/Reality authority, release gates, or rollback.
Path protection is necessary but insufficient, so the guard also evaluates
semantic invariants and treats unparseable protected changes as UNKNOWN.
"""
from __future__ import annotations

import ast
import fnmatch
import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)



class DriftDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_GOVERNANCE = "REQUIRE_GOVERNANCE"
    DENY = "DENY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DriftResult:
    decision: DriftDecision
    reasons: tuple[str, ...]
    invariant_ids: tuple[str, ...] = ()


_SEVERITY = {
    DriftDecision.ALLOW: 0,
    DriftDecision.REQUIRE_GOVERNANCE: 1,
    DriftDecision.UNKNOWN: 2,
    DriftDecision.DENY: 3,
}


class DriftGuard:
    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)
        doc = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8")) or {}
        if doc.get("schema_version") != 1:
            raise ValueError("unsupported protected invariant manifest schema")
        self._protected = list(doc.get("protected") or [])

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        normalized = str(path).replace("\\", "/").lstrip("./")
        pat = str(pattern).replace("\\", "/").lstrip("./")
        if pat.endswith("/**"):
            root = pat[:-3].rstrip("/")
            return normalized == root or normalized.startswith(root + "/")
        return fnmatch.fnmatch(normalized, pat)

    def matching_invariants(self, path: str) -> list[dict]:
        return [
            item
            for item in self._protected
            if any(self._matches(path, pat) for pat in (item.get("path_patterns") or []))
        ]

    @staticmethod
    def _semantic_value(path: str, text: str):
        suffix = Path(path).suffix.lower()
        if suffix == ".py":
            tree = ast.parse(text)
            return ast.dump(tree, annotate_fields=True, include_attributes=False)
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_load(text)
        if suffix == ".json":
            return json.loads(text)
        # For env/text/workflow snippets, strip blank/comment-only lines. This
        # intentionally does NOT attempt to prove general semantic equivalence.
        lines = []
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
        return lines

    @classmethod
    def _semantically_equivalent(cls, path: str, old_text: str, new_text: str) -> bool:
        try:
            return cls._semantic_value(path, old_text) == cls._semantic_value(path, new_text)
        except Exception:
            logger.warning('DriftGuard._semantically_equivalent: Exception not handled', exc_info=True)
            return False

    @staticmethod
    def _hard_invariant_violations(path: str, old_text: str, new_text: str) -> list[str]:
        violations: list[str] = []
        normalized = path.replace("\\", "/")

        # Mandatory-test weakening patterns: only flag NEW introduction, not a
        # legacy token already present in both versions.
        if normalized.startswith("tests/"):
            weakening = (
                "pytest.skip(",
                "pytest.mark.skip",
                "pytest.mark.xfail",
                "@pytest.mark.skip",
                "@pytest.mark.xfail",
                "assert True",
            )
            for token in weakening:
                if token in new_text and token not in old_text:
                    violations.append(f"test-integrity invariant: introduced {token!r}")

        return violations

    def inspect_change(
        self,
        *,
        path: str,
        old_text: str,
        new_text: str,
        governance_authorized: bool = False,
    ) -> DriftResult:
        hard = self._hard_invariant_violations(path, old_text, new_text)
        matched = self.matching_invariants(path)
        invariant_ids = tuple(str(item.get("id")) for item in matched)
        if hard:
            return DriftResult(DriftDecision.DENY, tuple(hard), invariant_ids)
        if old_text == new_text or self._semantically_equivalent(path, old_text, new_text):
            return DriftResult(DriftDecision.ALLOW, ("no semantic change",), invariant_ids)
        if not matched:
            return DriftResult(DriftDecision.ALLOW, ("path is outside protected invariants",), ())

        # For protected structured files, parse failure is an epistemic UNKNOWN,
        # not an implicit approval.
        try:
            self._semantic_value(path, new_text)
        except Exception as exc:
            logger.debug(f"DriftGuard.inspect_change: exception ignored: {exc}", exc_info=True)
            return DriftResult(
                DriftDecision.UNKNOWN,
                (f"protected change cannot be semantically parsed: {type(exc).__name__}",),
                invariant_ids,
            )

        if governance_authorized:
            return DriftResult(
                DriftDecision.ALLOW,
                ("protected semantic change has explicit governance authorization",),
                invariant_ids,
            )
        return DriftResult(
            DriftDecision.REQUIRE_GOVERNANCE,
            ("protected semantic change requires explicit governance workflow",),
            invariant_ids,
        )

    def inspect_changes(
        self,
        changes: Iterable[tuple[str, str, str]],
        *,
        governance_authorized: bool = False,
    ) -> DriftResult:
        results = [
            self.inspect_change(
                path=path,
                old_text=old,
                new_text=new,
                governance_authorized=governance_authorized,
            )
            for path, old, new in changes
        ]
        if not results:
            return DriftResult(DriftDecision.ALLOW, ("no changes",), ())
        worst = max(results, key=lambda result: _SEVERITY[result.decision])
        reasons = tuple(reason for result in results for reason in result.reasons)
        ids = tuple(dict.fromkeys(i for result in results for i in result.invariant_ids))
        return DriftResult(worst.decision, reasons, ids)
