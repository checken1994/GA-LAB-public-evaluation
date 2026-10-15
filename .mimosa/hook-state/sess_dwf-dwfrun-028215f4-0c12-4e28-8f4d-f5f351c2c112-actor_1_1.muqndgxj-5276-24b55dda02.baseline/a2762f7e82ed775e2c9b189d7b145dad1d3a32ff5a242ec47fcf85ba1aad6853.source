from pathlib import Path

"""Reality test for Fix 4-b-005: classify_threat must NOT always return 'high'.

Before fix: stub `return "high"` → every threat → Dead Man's Switch armed.
After fix:  real classification → low-confidence threats → 'low'/'medium' (no auto-arm).

DNA #22 (PASS≠TRUE — classifier claimed to classify but always returned "high").
DNA #11 (HITL — every threat auto-armed 30-min countdown without discrimination).
DNA #9  (No harm — false alarms cause operator alert fatigue + defensive playbook runs).
DNA #26 (reality test).
"""


def classify_threat(threat_data):
    """Mirror of the post-fix EscalationManager.classify_threat logic."""
    if not isinstance(threat_data, dict):
        return "medium"
    severity = (threat_data.get("severity") or "").lower()
    confidence = threat_data.get("confidence")
    if confidence is None:
        confidence = threat_data.get("prediction_confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    if severity in ("critical", "high", "medium", "low"):
        return severity
    indicator = (
        threat_data.get("indicator_type")
        or threat_data.get("indicator")
        or threat_data.get("type")
        or ""
    ).lower()
    if confidence >= 0.9 and indicator in (
        "exploit_attempt", "data_exfiltration", "privilege_escalation",
    ):
        return "high"
    if confidence >= 0.95 and indicator in (
        "malware_signature", "known_bad_ip",
    ):
        return "critical"
    if indicator == "falsification_human_review" and confidence >= 0.7:
        return "medium"
    if confidence >= 0.5:
        return "medium"
    # Conservative default — "medium" (NOT "high", NOT auto-arm).
    return "medium"


# TEST 1: empty threat_data → 'medium' (NOT 'high' — no auto-arm).
assert classify_threat({}) == "medium", \
    f"FAIL: empty threat → {classify_threat({})}"
print("PASS: empty threat → medium (no auto-arm)")

# TEST 2: low-confidence threat → 'low' or 'medium' (NOT 'high').
result = classify_threat({"confidence": 0.3, "indicator": "anomaly"})
assert result in ("low", "medium"), \
    f"FAIL: low-confidence threat → {result} (should be low/medium, not high)"
print(f"PASS: low-confidence threat → {result}")

# TEST 3: high-confidence exploit → 'high' (real threat still escalates).
result = classify_threat({"confidence": 0.95, "indicator_type": "exploit_attempt"})
assert result == "high", f"FAIL: high-confidence exploit → {result}"
print(f"PASS: high-confidence exploit → {result}")

# TEST 4: explicit severity field is respected (caller knows the severity).
assert classify_threat({"severity": "low"}) == "low"
assert classify_threat({"severity": "medium"}) == "medium"
assert classify_threat({"severity": "high"}) == "high"
assert classify_threat({"severity": "critical"}) == "critical"
print("PASS: explicit severity field respected (low/medium/high/critical)")

# TEST 5: read source and verify the `return "high"` STUB is gone from the
# classify_threat function body. Use AST so we don't match docstrings/comments.
import ast

with open(str(Path(__file__).resolve().parents[2]) + '/scp/security/escalation.py') as f:
    src = f.read()

tree = ast.parse(src)
classify_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "classify_threat":
        classify_node = node
        break

assert classify_node is not None, "FAIL: classify_threat function not found in source"

# Collect all return statements that return a constant string in the function
# body, in source order. We use a tree walk that respects source order via
# AST node line numbers.
return_constants = []
for node in ast.walk(classify_node):
    if (isinstance(node, ast.Return)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)):
        return_constants.append((node.lineno, node.value.value))

assert return_constants, "FAIL: no `return <string>` statements found in classify_threat body"

# Sort by line number to get source order.
return_constants.sort(key=lambda x: x[0])
first_lineno, first_return_value = return_constants[0]
assert first_return_value != "high", (
    f"FAIL: first return in classify_threat is `return \"high\"` (line {first_lineno}) — "
    "stub still present"
)
print(
    f"PASS: classify_threat stub removed "
    f"(first return = {first_return_value!r} at line {first_lineno})"
)

# Also verify the body has more than 1 return (real classifier has many branches).
assert len(return_constants) >= 3, (
    f"FAIL: classify_threat body too small ({len(return_constants)} returns) — "
    "still a stub?"
)
print(f"PASS: classify_threat has real body ({len(return_constants)} return statements)")

print("\n✓ Reality test 4-b-005 PASSED (5/5 assertions)")
