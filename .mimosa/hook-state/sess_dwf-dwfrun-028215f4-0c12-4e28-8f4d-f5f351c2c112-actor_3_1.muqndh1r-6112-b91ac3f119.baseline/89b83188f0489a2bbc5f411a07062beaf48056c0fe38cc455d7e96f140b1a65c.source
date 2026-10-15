"""Pytest discovery test suite for the 10 converted behavioral reality tests (R4-04)."""
import importlib.util
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parent


def _get_mod(filename: str):
    mod_name = filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(mod_name, _DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_converted_reality_4_a_003():
    mod = _get_mod("reality_4-a-003.py")
    mod.test_prediction_verify_endpoint_requires_admin_auth()
    mod.test_prediction_stats_endpoint_requires_admin_auth()


def test_converted_reality_4_a_005():
    mod = _get_mod("reality_4-a-005.py")
    mod.test_fetch_with_retry_blocks_loopback_ssrf()
    mod.test_fetch_with_retry_blocks_file_scheme()
    mod.test_safe_fetch_url_blocks_metadata_ip()
    mod.test_helpers_reexport_identity()


def test_converted_reality_4_a_009(tmp_path):
    mod = _get_mod("reality_4-a-009.py")
    mod.test_permission_gate_apply_failed_transactional_recovery(tmp_path)


def test_converted_reality_4_a_011(tmp_path):
    mod = _get_mod("reality_4-a-011.py")
    mod.test_vector_store_records_actual_file_mtime(tmp_path)


def test_converted_reality_4_a_013():
    mod = _get_mod("reality_4-a-013.py")
    mod.test_transcribe_cleans_up_temp_file_on_exception()


@pytest.mark.asyncio
async def test_converted_reality_4_a_014():
    mod = _get_mod("reality_4-a-014.py")
    mod.test_reality_4_a_014_ast()
    await mod.test_openrouter_provider_client_lock_concurrency()


def test_converted_reality_4_a_015():
    mod = _get_mod("reality_4-a-015.py")
    mod.test_reality_4_a_015_ast()
    mod.test_image_check_runs_in_worker_thread()


def test_converted_reality_4_a_017():
    mod = _get_mod("reality_4-a-017.py")
    mod.test_reality_4_a_017_ast()
    mod.test_healing_engine_like_escape_behavioral()


def test_converted_reality_4_a_018():
    mod = _get_mod("reality_4-a-018.py")
    mod.test_reality_4_a_018_ast()
    mod.test_fact_check_retract_queue_deque_eviction()


def test_converted_reality_4_b_003():
    mod = _get_mod("reality_4-b-003.py")
    mod.test_reality_4_b_003_ast()
    mod.test_external_trust_human_approved_behavioral()
