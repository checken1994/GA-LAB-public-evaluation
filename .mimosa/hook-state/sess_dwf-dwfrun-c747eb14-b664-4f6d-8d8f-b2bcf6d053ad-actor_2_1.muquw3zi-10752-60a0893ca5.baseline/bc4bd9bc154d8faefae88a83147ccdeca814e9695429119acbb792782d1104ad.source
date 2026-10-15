import asyncio
import time

from scp.core.fast_learning_engine import (
    FastLearningEngine,  # facade runs _wire_parts()
)

# ==============================================================================
# T08 - HERMETIC SCHEDULER/CONCURRENCY BENCHMARK (Bước 0.12 debt)
# ==============================================================================
# A MEASURED two-workload benchmark of the learning engine's PARALLEL
# SCHEDULER SEMANTICS (semaphore + executor fan-out), not of LLM latency:
#   workload A: sequential = N blocking work units, one after another
#   workload B: parallel   = the same N work units through _ask_llm_parallel
# Same work units (deterministic 20 ms sleep each), measured with
# time.monotonic_ns(), warmup excluded. This is the hermetic companion the
# ESTIMATE-labeled /v104/learn/fast/benchmark route must never pretend to be.
# ==============================================================================

N_UNITS = 16
UNIT_SLEEP_S = 0.02
PARALLEL_MIN_SPEEDUP = 2.0


def _bench(engine, tmp_dir: str):
    # Deterministic work unit: patch the blocking LLM seam (scheduler benchmark,
    # NOT an LLM benchmark - the LLM side of the route stays ESTIMATE-labeled).
    def _unit(_question: str) -> str:
        time.sleep(UNIT_SLEEP_S)
        return "ok"

    engine._ask_llm_sync = _unit

    async def _warmup_then_parallel() -> float:
        # Warmup (excluded from measurement) primes the lazy semaphore/executor;
        # it MUST live in the same event loop as the measurement - the engine
        # caches its asyncio.Semaphore per loop.
        await asyncio.gather(*[engine._ask_llm_parallel(f"warm{i}") for i in range(2)])
        started = time.monotonic_ns()
        await asyncio.gather(*[engine._ask_llm_parallel(f"q{i}") for i in range(N_UNITS)])
        return (time.monotonic_ns() - started) / 1e9

    seq_started = time.monotonic_ns()
    for i in range(N_UNITS):
        engine._ask_llm_sync(f"q{i}")
    sequential_s = (time.monotonic_ns() - seq_started) / 1e9

    parallel_s = asyncio.run(_warmup_then_parallel())
    return sequential_s, parallel_s


def test_parallel_scheduler_beats_sequential_on_same_work_units(tmp_path):
    engine = FastLearningEngine(
        scp_db_path=str(tmp_path / "v13.db"), data_dir=str(tmp_path)
    )
    sequential_s, parallel_s = _bench(engine, str(tmp_path))

    assert sequential_s >= N_UNITS * UNIT_SLEEP_S * 0.8, (
        f"Sequential workload shorter than its own work units - measurement broken: {sequential_s:.3f}s"
    )
    speedup = sequential_s / parallel_s if parallel_s > 0 else 0.0
    assert speedup >= PARALLEL_MIN_SPEEDUP, (
        f"Scheduler semantics regressed: sequential={sequential_s:.3f}s "
        f"parallel={parallel_s:.3f}s speedup={speedup:.2f} (< {PARALLEL_MIN_SPEEDUP})"
    )
