# INTENTIONAL CANARY FIXTURE — DO NOT FIX, DO NOT MOVE, DO NOT DELETE.
# Used by the /v105 autofix observe probe (ast_scan undefined-name visitor) to
# prove the scanner really runs at runtime. Path is pinned by the M07 circuit
# closure (docs/evidence-summary/M07-closure.json, probe commit 1f00d00):
# ast_scan must keep finding scp/hello_bug.py as a live finding.
def hello():
    x = unknown_var  # noqa: F821,F841,F841 -- intentional canary bug, see header above
