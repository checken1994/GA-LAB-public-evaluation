"""[R8-2 FIX] Regression tests — Tier-4 evolution expiry must not silently re-arm.

BEFORE the fix, `_should_evolve` Guard 2 handled timeout with
``_evolution_enabled_at = 0.0; return False`` — the NEXT call saw 0.0,
re-armed the clock, and returned True. Net effect: Tier-4 evolution
re-enabled itself every 4h as long as SCP_EVOLUTION_ENABLED stayed "1",
with no operator intent. The fix applies the engine.py R8-2 pattern:
track first-enable time + `_evolution_expired` flag; never re-arm after
expiry (only a genuine 0/unset -> 1 env transition resets).
"""
import time

from scp.autofix.evolution import EVOLUTION_TIMEOUT_SECONDS
from scp.autofix.evolution_parts.reflectmixin import EvolutionEngineReflectMixin


class _StubEvolutionEngine(EvolutionEngineReflectMixin):
    """Minimal host for the mixin — only the state Guard 2/3 touch."""

    def __init__(self):
        self._evolution_enabled_at = 0.0
        self._evolution_timestamps = []
        self.rejected = []

    def _touches_constitution(self, action_desc: str) -> bool:
        return False

    def _write_rejected(self, action_desc: str, reason: str) -> None:
        self.rejected.append((action_desc, reason))


class TestEvolutionExpiryNoRearm:
    def test_tier4_expiry_does_not_rearm_silently(self, monkeypatch):
        monkeypatch.setenv("SCP_EVOLUTION_ENABLED", "1")
        eng = _StubEvolutionEngine()

        # First call arms the clock.
        assert eng._should_evolve("benign action") is True
        assert eng._evolution_enabled_at > 0.0

        # Force the clock past the 4h timeout.
        eng._evolution_enabled_at = time.time() - EVOLUTION_TIMEOUT_SECONDS - 5
        assert eng._should_evolve("benign action") is False
        assert getattr(eng, "_evolution_expired", False) is True

        # BEFORE THE FIX this call re-armed the clock (enabled_at was reset
        # to 0.0) and returned True — Tier-4 evolution resurrected itself.
        frozen_ts = eng._evolution_enabled_at
        assert eng._should_evolve("benign action") is False, (
            "Tier-4 evolution re-enabled itself after expiry without any "
            "operator 0->1 env transition"
        )
        assert eng._evolution_enabled_at == frozen_ts, (
            "first-enable timestamp was reset (silent re-arm)"
        )

    def test_tier4_operator_rearm_requires_unset_then_set(self, monkeypatch):
        monkeypatch.setenv("SCP_EVOLUTION_ENABLED", "1")
        eng = _StubEvolutionEngine()
        assert eng._should_evolve("benign action") is True
        eng._evolution_enabled_at = time.time() - EVOLUTION_TIMEOUT_SECONDS - 5
        assert eng._should_evolve("benign action") is False
        assert getattr(eng, "_evolution_expired", False) is True

        # Operator unsets the env var (Guard 1 denies; transition recorded)...
        monkeypatch.setenv("SCP_EVOLUTION_ENABLED", "0")
        assert eng._should_evolve("benign action") is False
        # ...then sets it again — the ONLY sanctioned re-arm path.
        monkeypatch.setenv("SCP_EVOLUTION_ENABLED", "1")
        assert eng._should_evolve("benign action") is True
        assert getattr(eng, "_evolution_expired", False) is False

    def test_tier4_env_off_means_off(self, monkeypatch):
        monkeypatch.setenv("SCP_EVOLUTION_ENABLED", "0")
        eng = _StubEvolutionEngine()
        assert eng._should_evolve("benign action") is False
