"""[VERIFIER-VACUITY-FIX] Regression tests — RestrictedSourceError must fail closed.

Probe BEFORE the fix (the external audit's exact probe shape):

    verify_patch_realtime("import os\\ndef f(x): return x+1",
                          "import os\\ndef f(x): return 'hijacked'",
                          func_name="f")
    -> ok=True "N inputs tested, 0 violations"

Root cause: compile_restricted_function() raises RestrictedSourceError on
BOTH legs for any real file (module-level imports are forbidden in the
sandbox), and _safe_exec_callable() returns (None, exc) for both. The two
promotion checks ("orig OK but fixed raised" / "return type changed") both
require one leg to be error-free, so nothing fired and the return-type
hijack was promoted. Fail-closed contract (DNA #2/#22): a check that cannot
execute is NOT a pass.
"""
from scp.autofix.realtime_verifier import verify_patch_realtime


class TestRestrictedSourceFailsClosed:
    def test_import_bearing_module_return_type_hijack_is_not_promoted(self):
        orig = "import os\ndef f(x): return x + 1\n"
        hijacked = "import os\ndef f(x): return 'hijacked'\n"
        result = verify_patch_realtime(orig, hijacked, func_name="f")

        assert result.ok is False, (
            f"return-type hijack in an import-bearing module was promoted: "
            f"ok={result.ok} reason={result.reason!r}"
        )
        assert result.violations, "expected an explicit sandbox violation"
        assert "unverified" in result.reason.lower()
        assert "sandbox" in result.reason.lower()

    def test_orig_leg_only_restricted_still_fails_closed(self):
        # Fixed leg is sandbox-clean but the ORIGINAL source cannot compile
        # in the sandbox — without a runnable baseline the patch is unverified.
        orig = "import os\ndef f(x): return x + 1\n"
        fixed = "def f(x): return x + 1\n"
        result = verify_patch_realtime(orig, fixed, func_name="f")
        assert result.ok is False
        assert result.violations

    def test_sandbox_compatible_legitimate_patch_still_verifies(self):
        # Guard against over-blocking: a patch both legs can execute must
        # still be verified with real inputs.
        result = verify_patch_realtime(
            "def f(x):\n    return x + 1\n",
            "def f(x):\n    return x + 2\n",
            func_name="f",
        )
        assert result.ok is True, result.reason
        assert result.inputs_tested > 0
