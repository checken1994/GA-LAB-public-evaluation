#!/usr/bin/env python3
"""Validate concrete-test traceability for the active SCP Future Target.

The coverage universe is derived from the composed target (currently 138
capabilities + 60 cause-effect edges). The binding file records only reviewed
concrete-test claims. Unclaimed targets remain explicit as UNPROVEN.

Exit 0 means the traceability structure is internally valid. It does not mean
all target behavior is tested, runtime-verified, or release-ready.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from tools.verify_scp_future_target import compose_future_target
except ModuleNotFoundError:  # direct: python tools/verify_scp_target_test_coverage.py
    from verify_scp_future_target import compose_future_target

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINDING = ROOT / "spec" / "scp_target_test_coverage.yaml"
KNOWN_GATES = {f"T{i:02d}" for i in range(12)}
KNOWN_STATUSES = {
    "UNPROVEN",
    "TEST_BOUND_PARTIAL",
    "TEST_BOUND_CONTRACT",
    "BLOCKED_MISSING_IMPLEMENTATION",
    "EVIDENCE_VERIFIED",
    # Explicit non-claimed visibility state: the target row was removed from
    # the active architecture by an authority decision (e.g. GA.md B13).
    # DEPRECATED rows stay in the report but never count as claimed coverage.
    "DEPRECATED",
}
EVIDENCE_ORDER = {None: 0, "A": 1, "B": 2, "C": 3, "D": 4, "D_PLUS_RELEASE": 5}


def _yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level value must be a mapping")
    return value


def _git_blob_sha(root: Path, rel: str, path: Path) -> str:
    """Git blob SHA of the working-tree content, staged exactly as Git would
    stage it (``git hash-object`` applies the path's clean filters).

    The binding pin must bind the manifest content actually composed, not a
    committed ancestor of it: hashing ``HEAD`` while composing the working
    tree would let uncommitted manifest edits pass against a stale pin
    (fail-open). On a clean checkout the filtered hash equals the committed
    blob SHA; a dirty tree hashes differently and fails closed.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "hash-object", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        sha = proc.stdout.strip()
        if proc.returncode == 0 and len(sha) == 40:
            return sha
    except (OSError, subprocess.SubprocessError):
        pass
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()


def _safe_file(root: Path, rel: Any) -> Path:
    if not isinstance(rel, str) or not rel:
        raise ValueError(f"invalid repository-relative path: {rel!r}")
    path = (root / rel).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"file not found: {rel}")
    return path


def _systems(target: dict[str, Any]):
    for family in ("core_systems", "cross_cutting_systems"):
        mapping = target.get(family) or {}
        if not isinstance(mapping, dict):
            continue
        for system_id, system in mapping.items():
            if isinstance(system, dict):
                yield family, system_id, system


def _inventory(target: dict[str, Any]):
    caps: dict[str, dict[str, Any]] = {}
    cap_owner: dict[str, str] = {}
    edges: dict[str, dict[str, Any]] = {}
    edge_owner: dict[str, str] = {}
    for _family, system_id, system in _systems(target):
        for cap in system.get("capabilities") or []:
            if isinstance(cap, dict) and isinstance(cap.get("id"), str):
                caps[cap["id"]] = cap
                cap_owner[cap["id"]] = system_id
        for edge in system.get("cause_effect_edges") or []:
            if isinstance(edge, dict) and isinstance(edge.get("id"), str):
                edges[edge["id"]] = edge
                edge_owner[edge["id"]] = system_id
    return caps, cap_owner, edges, edge_owner


def _selector_parts(selector: Any) -> tuple[str, list[str]]:
    if not isinstance(selector, str) or "::" not in selector:
        raise ValueError(
            f"concrete test selector must be '<repo/path.py>::<test>', got {selector!r}"
        )
    first, *nodes = selector.split("::")
    if not first.endswith(".py") or not nodes or any(not node for node in nodes):
        raise ValueError(f"invalid pytest node selector: {selector!r}")
    return first, nodes


def _body_asserts_verification(func_node: ast.AST) -> bool:
    """True only when the test body itself executes an assertion at runtime.

    A plain ``assert`` statement or a ``pytest.raises(...)`` call counts.
    Assertions inside nested ``def``/``class``/``lambda`` scopes never count:
    those bodies do not run as part of the test body unless invoked explicitly,
    so a test that only defines them cannot fail on its own (fail-closed).
    """
    stack = list(ast.iter_child_nodes(func_node))
    while stack:
        current = stack.pop()
        if isinstance(
            current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            continue
        if isinstance(current, ast.Assert):
            return True
        if (
            isinstance(current, ast.Call)
            and isinstance(current.func, ast.Attribute)
            and current.func.attr == "raises"
            and isinstance(current.func.value, ast.Name)
            and current.func.value.id == "pytest"
        ):
            return True
        stack.extend(ast.iter_child_nodes(current))
    return False


def _is_executable_test_node(node: ast.AST) -> bool:
    """A bound selector must resolve to a test that can actually fail.

    Existence alone proves nothing: ``def test_x(): pass`` (no asserts) and
    helper functions without the ``test_`` prefix are rejected, as are classes
    that contain no executable test.
    """
    if isinstance(node, ast.ClassDef):
        return any(
            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name.startswith("test_")
            and _body_asserts_verification(member)
            for member in node.body
        )
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    return node.name.startswith("test_") and _body_asserts_verification(node)


def _node_exists(path: Path, nodes: list[str]) -> bool:
    """True only when the selector resolves to an executable, assertion-carrying test node.

    Intermediate nodes must still be classes; the final node must additionally
    pass ``_is_executable_test_node`` so an empty or pass-only placeholder can
    never validate a coverage claim (anti-Goodhart, T00).
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return False
    body: list[ast.stmt] = tree.body
    final: ast.AST | None = None
    for index, node_name in enumerate(nodes):
        found: ast.AST | None = None
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == node_name:
                    found = node
                    break
        if found is None:
            return False
        if index < len(nodes) - 1:
            if not isinstance(found, ast.ClassDef):
                return False
            body = found.body
        else:
            final = found
    if final is None:
        return False
    return _is_executable_test_node(final)


def _selector_gate(selector: str, gate_catalog: dict[str, str]) -> str | None:
    rel, _nodes = _selector_parts(selector)
    rel_path = Path(rel).as_posix()
    matches = []
    for gate, directory in gate_catalog.items():
        prefix = Path(directory).as_posix().rstrip("/") + "/"
        if rel_path.startswith(prefix):
            matches.append(gate)
    return matches[0] if len(matches) == 1 else None


def _capability_gates_and_edges(
    cap_id: str, edges: dict[str, dict[str, Any]]
) -> tuple[set[str], list[str]]:
    gates: set[str] = set()
    covering: list[str] = []
    for edge_id, edge in edges.items():
        if cap_id in (edge.get("covers_capabilities") or []):
            covering.append(edge_id)
            gates.update(str(g) for g in (edge.get("gates") or []))
    return gates, sorted(covering)


def _capability_required_evidence(
    cap: dict[str, Any], target: dict[str, Any]
) -> str | None:
    maturity = cap.get("target_maturity")
    floors = (target.get("maturity_model") or {}).get("evidence_floor_by_maturity") or {}
    value = floors.get(maturity)
    return str(value) if value is not None else None


def build_effective_coverage(
    binding: dict[str, Any], target: dict[str, Any]
) -> dict[str, Any]:
    caps, cap_owner, edges, edge_owner = _inventory(target)
    claims: dict[tuple[str, str], dict[str, Any]] = {}
    for claim in binding.get("claims") or []:
        if isinstance(claim, dict):
            key = (str(claim.get("target_kind")), str(claim.get("target_id")))
            if key not in claims:
                claims[key] = claim
    unclaimed = (
        (binding.get("inventory_policy") or {}).get("unclaimed_status") or "UNPROVEN"
    )

    cap_rows: list[dict[str, Any]] = []
    for cap_id in sorted(caps):
        cap = caps[cap_id]
        gates, covering_edges = _capability_gates_and_edges(cap_id, edges)
        claim = claims.get(("capability", cap_id))
        cap_rows.append(
            {
                "target_kind": "capability",
                "target_id": cap_id,
                "owner_system": cap_owner[cap_id],
                "phase": cap.get("phase"),
                "target_maturity": cap.get("target_maturity"),
                "required_evidence_level": _capability_required_evidence(cap, target),
                "applicable_gates": sorted(gates),
                "covering_edges": covering_edges,
                "status": claim.get("status") if claim else unclaimed,
                "observed_evidence_level": claim.get("observed_evidence_level") if claim else None,
                "concrete_tests": list(claim.get("concrete_tests") or []) if claim else [],
                "evidence_refs": list(claim.get("evidence_refs") or []) if claim else [],
                "snapshot_sha": claim.get("snapshot_sha") if claim else None,
                "note": claim.get("note") if claim else None,
            }
        )

    edge_rows: list[dict[str, Any]] = []
    for edge_id in sorted(edges):
        edge = edges[edge_id]
        claim = claims.get(("edge", edge_id))
        edge_rows.append(
            {
                "target_kind": "edge",
                "target_id": edge_id,
                "owner_system": edge_owner[edge_id],
                "covers_capabilities": list(edge.get("covers_capabilities") or []),
                "required_evidence_level": edge.get("evidence_target"),
                "applicable_gates": sorted(str(g) for g in (edge.get("gates") or [])),
                "status": claim.get("status") if claim else unclaimed,
                "observed_evidence_level": claim.get("observed_evidence_level") if claim else None,
                "concrete_tests": list(claim.get("concrete_tests") or []) if claim else [],
                "evidence_refs": list(claim.get("evidence_refs") or []) if claim else [],
                "snapshot_sha": claim.get("snapshot_sha") if claim else None,
                "note": claim.get("note") if claim else None,
            }
        )

    reverse: dict[str, list[str]] = defaultdict(list)
    for row in cap_rows + edge_rows:
        for selector in row["concrete_tests"]:
            reverse[selector].append(f'{row["target_kind"]}:{row["target_id"]}')
    status_counts = Counter(row["status"] for row in cap_rows + edge_rows)
    return {
        "schema_version": 1,
        "effective_target_revision": str(target.get("spec_revision")),
        "capabilities": cap_rows,
        "cause_effect_edges": edge_rows,
        "test_to_targets": {key: sorted(value) for key, value in sorted(reverse.items())},
        "summary": {
            "capabilities_total": len(cap_rows),
            "cause_effect_edges_total": len(edge_rows),
            "claims_total": len(binding.get("claims") or []),
            "status_counts": dict(sorted(status_counts.items())),
            "coverage_proven": False,
            "verdict": "TRACEABILITY_STRUCTURE_ONLY_NOT_COVERAGE_PROOF",
        },
    }


def validate_coverage_payload(
    binding: dict[str, Any],
    target: dict[str, Any],
    *,
    root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    if binding.get("schema_version") != 1:
        errors.append("coverage schema_version must be 1")
    if binding.get("binding_id") != "scp-target-test-coverage":
        errors.append("binding_id must be scp-target-test-coverage")
    if binding.get("status") != "ACTIVE":
        errors.append("coverage binding status must be ACTIVE")

    target_meta = binding.get("target") or {}
    if str(target_meta.get("effective_revision")) != str(target.get("spec_revision")):
        errors.append("coverage binding target revision is stale")
    caps, _cap_owner, edges, _edge_owner = _inventory(target)
    if target_meta.get("expected_capabilities") != len(caps):
        errors.append(
            f"expected_capabilities={target_meta.get('expected_capabilities')!r} "
            f"but composed target has {len(caps)}"
        )
    if target_meta.get("expected_cause_effect_edges") != len(edges):
        errors.append(
            f"expected_cause_effect_edges={target_meta.get('expected_cause_effect_edges')!r} "
            f"but composed target has {len(edges)}"
        )

    policy = binding.get("inventory_policy") or {}
    required_policy = {
        "universe_source": "COMPOSED_TARGET",
        "unclaimed_status": "UNPROVEN",
        "capability_gate_source": "UNION_OF_COVERING_EDGES",
        "capability_evidence_source": "MATURITY_EVIDENCE_FLOOR",
        "edge_gate_source": "EDGE_GATES",
        "edge_evidence_source": "EDGE_EVIDENCE_TARGET",
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            errors.append(f"inventory_policy.{key} must be {expected}")

    status_model = binding.get("status_model") or {}
    missing_status = KNOWN_STATUSES - set(status_model)
    if missing_status:
        errors.append(f"status_model missing statuses: {sorted(missing_status)}")

    gate_catalog = binding.get("gate_catalog") or {}
    if set(gate_catalog) != KNOWN_GATES:
        errors.append(f"gate_catalog must cover exactly T00-T11, got {sorted(gate_catalog)}")
    test_arch = target.get("test_architecture") or {}
    for gate in sorted(KNOWN_GATES):
        directory = gate_catalog.get(gate)
        expected_dir = (test_arch.get(gate) or {}).get("dir")
        if directory != expected_dir:
            errors.append(
                f"{gate}: gate directory mismatch coverage={directory!r} target={expected_dir!r}"
            )
        if isinstance(directory, str) and not (root / directory).is_dir():
            errors.append(f"{gate}: gate directory does not exist: {directory}")

    claims = binding.get("claims") or []
    if not isinstance(claims, list):
        return errors + ["claims must be a list"]

    seen_targets: set[tuple[str, str]] = set()
    for index, claim in enumerate(claims):
        label = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{label}: claim must be a mapping")
            continue
        kind = claim.get("target_kind")
        target_id = claim.get("target_id")
        key = (str(kind), str(target_id))
        if key in seen_targets:
            errors.append(f"{label}: duplicate target claim {kind}:{target_id}")
        seen_targets.add(key)

        if kind == "capability":
            target_row = caps.get(target_id)
            applicable_gates, _covering = _capability_gates_and_edges(str(target_id), edges)
            required_evidence = (
                _capability_required_evidence(target_row, target)
                if isinstance(target_row, dict)
                else None
            )
        elif kind == "edge":
            target_row = edges.get(target_id)
            applicable_gates = (
                {str(g) for g in (target_row.get("gates") or [])}
                if isinstance(target_row, dict)
                else set()
            )
            required_evidence = (
                target_row.get("evidence_target") if isinstance(target_row, dict) else None
            )
        else:
            target_row = None
            applicable_gates = set()
            required_evidence = None
            errors.append(f"{label}: target_kind must be capability or edge")

        if target_row is None:
            errors.append(f"{label}: unknown target {kind}:{target_id}")

        status = claim.get("status")
        if status not in KNOWN_STATUSES - {"UNPROVEN"}:
            errors.append(f"{label}: explicit claim status must be a claimed state, got {status!r}")

        selectors = claim.get("concrete_tests") or []
        if status in {"TEST_BOUND_PARTIAL", "TEST_BOUND_CONTRACT", "EVIDENCE_VERIFIED"}:
            if not isinstance(selectors, list) or not selectors:
                errors.append(f"{label}: {status} requires concrete_tests")
        if status == "BLOCKED_MISSING_IMPLEMENTATION" and selectors:
            errors.append(f"{label}: blocked missing implementation must not claim tests")

        observed = claim.get("observed_evidence_level")
        if status == "DEPRECATED":
            # Deprecated rows stay visible but non-claimed: they cannot carry
            # observed evidence. "N/A" (or omission) states that explicitly;
            # an A/B/C/D level would forge evidence for a removed row.
            if observed not in (None, "N/A"):
                errors.append(
                    f"{label}: DEPRECATED claim must not claim observed evidence "
                    f"(use N/A or omit), got {observed!r}"
                )
            if not str(claim.get("note") or "").strip():
                errors.append(
                    f"{label}: DEPRECATED claim must document the deprecation in note"
                )
        elif observed is not None and observed not in {"A", "B", "C", "D"}:
            errors.append(f"{label}: invalid observed_evidence_level {observed!r}")
        if status and status.startswith("TEST_BOUND") and observed is None:
            errors.append(f"{label}: test-bound claim must state observed_evidence_level")

        for selector in selectors if isinstance(selectors, list) else []:
            try:
                rel, nodes = _selector_parts(selector)
                path = _safe_file(root, rel)
            except ValueError as exc:
                errors.append(f"{label}: {exc}")
                continue
            if not _node_exists(path, nodes):
                errors.append(f"{label}: pytest node does not exist: {selector}")
            try:
                selector_gate = _selector_gate(selector, gate_catalog)
            except ValueError as exc:
                errors.append(f"{label}: {exc}")
                continue
            if selector_gate is None:
                errors.append(f"{label}: test selector is not in exactly one T00-T11 gate: {selector}")
            elif target_row is not None and selector_gate not in applicable_gates:
                errors.append(
                    f"{label}: {selector_gate} is not applicable to {kind}:{target_id}; "
                    f"allowed={sorted(applicable_gates)}"
                )

        if status == "EVIDENCE_VERIFIED":
            snapshot_sha = claim.get("snapshot_sha")
            refs = claim.get("evidence_refs") or []
            if not isinstance(snapshot_sha, str) or len(snapshot_sha) != 40:
                errors.append(f"{label}: EVIDENCE_VERIFIED requires 40-char snapshot_sha")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{label}: EVIDENCE_VERIFIED requires evidence_refs")
            if EVIDENCE_ORDER.get(observed, -1) < EVIDENCE_ORDER.get(required_evidence, 99):
                errors.append(
                    f"{label}: observed evidence {observed!r} does not meet required {required_evidence!r}"
                )

    report = build_effective_coverage(binding, target)
    cap_rows = report["capabilities"]
    edge_rows = report["cause_effect_edges"]
    if len(cap_rows) != len(caps) or {r["target_id"] for r in cap_rows} != set(caps):
        errors.append("effective coverage map does not contain every target capability exactly once")
    if len(edge_rows) != len(edges) or {r["target_id"] for r in edge_rows} != set(edges):
        errors.append("effective coverage map does not contain every target edge exactly once")
    for selector, targets in report["test_to_targets"].items():
        if not targets:
            errors.append(f"reverse mapping missing targets for {selector}")
    if report["summary"]["coverage_proven"] is not False:
        errors.append("coverage report must not claim coverage_proven from binding integrity")

    must_not = set((binding.get("coverage_verdict_policy") or {}).get("must_not_claim") or [])
    required_forbidden_claims = {
        "all_target_capabilities_tested",
        "all_target_edges_tested",
        "runtime_verified",
        "release_ready",
        "no_missing_piece",
    }
    if not required_forbidden_claims.issubset(must_not):
        errors.append("coverage verdict policy must forbid broad completion/runtime claims")
    return errors


def load_and_validate(
    binding_path: Path = DEFAULT_BINDING,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    errors: list[str] = []
    binding_path = binding_path.resolve()
    root = binding_path.parents[1]
    try:
        binding = _yaml(binding_path)
        target_meta = binding.get("target") or {}
        manifest_rel = target_meta.get("manifest_path")
        manifest_path = _safe_file(root, manifest_rel)
    except (OSError, ValueError) as exc:
        return {}, {}, {}, [f"coverage binding load error: {exc}"]

    actual_manifest_sha = _git_blob_sha(root, str(manifest_rel), manifest_path)
    if actual_manifest_sha != target_meta.get("manifest_blob_sha"):
        errors.append("coverage binding is stale: target manifest blob SHA does not match active file")

    _manifest, target, compose_errors = compose_future_target(manifest_path)
    errors.extend(compose_errors)
    if target:
        errors.extend(validate_coverage_payload(binding, target, root=root))
        report = build_effective_coverage(binding, target)
    else:
        report = {}
    return binding, target, report, errors


def validate_coverage_binding(binding_path: Path = DEFAULT_BINDING) -> list[str]:
    return load_and_validate(binding_path)[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "binding",
        nargs="?",
        type=Path,
        default=DEFAULT_BINDING,
        help="coverage binding YAML (default: spec/scp_target_test_coverage.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the generated full capability/edge coverage map",
    )
    args = parser.parse_args(argv)
    _binding, _target, report, errors = load_and_validate(args.binding)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "OK: target test traceability structure valid; "
            f"capabilities={summary['capabilities_total']} "
            f"edges={summary['cause_effect_edges_total']} "
            f"claims={summary['claims_total']} "
            f"status_counts={summary['status_counts']}"
        )
        print("VERDICT: TRACEABILITY_STRUCTURE_ONLY_NOT_COVERAGE_PROOF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
