import sys

sys.path.insert(0, ".")


from scp.llm_gateway import client as cl
from scp.llm_gateway import free_catalog as fc

original_allowlist = list(cl.OPENROUTER_FREE_MODELS)

# [P0-14 Z1 rewrite 2026-09-02] The catalog refresh now produces AUTHORITATIVE
# pricing proofs (immutable PricingProofStore records with expiry), not just a
# name allowlist. The hardcoded model-name list is a DISCOVERY HINT only:
# "the name used to be free" is never authorization. These tests encode the
# new contract - superseding the old keep-hardcoded-on-failure semantics.


def _reset() -> None:
    fc._fetched = False
    fc._last_ok = None
    cl.OPENROUTER_FREE_MODELS = list(original_allowlist)


def _catalog_entry(model_id: str, prompt="0", completion="0", modality="text"):
    pricing = {"prompt": prompt, "completion": completion}
    return {"id": model_id, "context_length": 8000, "output_modalities": [modality], "pricing": pricing}


def test_text_capable_rejects_audio_video() -> None:
    assert fc._text_capable({"output_modalities": ["audio"]}) is False
    assert fc._text_capable({"output_modalities": ["video"]}) is False


def test_text_capable_accepts_text_and_absent() -> None:
    assert fc._text_capable({"output_modalities": ["text"]}) is True
    assert fc._text_capable({}) is True


def test_text_capable_supports_nested_architecture_schema() -> None:
    assert fc._text_capable({"architecture": {"output_modalities": ["text"]}}) is True
    assert fc._text_capable({"architecture": {"output_modalities": ["audio"]}}) is False


def test_refresh_replaces_allowlist_and_filters_audio(monkeypatch, tmp_path) -> None:
    _reset()
    cat = [_catalog_entry("m/a:free", modality="audio"), _catalog_entry("m/x:free")]
    monkeypatch.setattr(fc, "_fetch_catalog_models", lambda timeout=None: cat)
    monkeypatch.setattr(fc, "_FOUNDATION", tmp_path)
    assert fc.refresh_free_catalog() is True
    assert cl.OPENROUTER_FREE_MODELS == ["m/x:free"]


def test_refresh_replaces_client_allowlist_not_fc_module(monkeypatch, tmp_path) -> None:
    _reset()
    cat = [_catalog_entry("m/y:free")]
    monkeypatch.setattr(fc, "_fetch_catalog_models", lambda timeout=None: cat)
    monkeypatch.setattr(fc, "_FOUNDATION", tmp_path)
    assert fc.refresh_free_catalog() is True
    assert cl.OPENROUTER_FREE_MODELS == ["m/y:free"]
    assert not hasattr(fc, "OPENROUTER_FREE_MODELS")


def test_refresh_network_fail_authorizes_nothing(monkeypatch, tmp_path) -> None:
    """No fresh proof -> refresh fails; the discovery list is untouched and
    stale proofs expire naturally (the guard denies them)."""
    _reset()
    before = list(cl.OPENROUTER_FREE_MODELS)
    monkeypatch.setattr(fc, "_fetch_catalog_models", lambda timeout=None: None)
    monkeypatch.setattr(fc, "_FOUNDATION", tmp_path)
    assert fc.refresh_free_catalog() is False
    assert cl.OPENROUTER_FREE_MODELS == before


def test_refresh_empty_catalog_authorizes_nothing(monkeypatch, tmp_path) -> None:
    _reset()
    before = list(cl.OPENROUTER_FREE_MODELS)
    monkeypatch.setattr(fc, "_fetch_catalog_models", lambda timeout=None: [])
    monkeypatch.setattr(fc, "_FOUNDATION", tmp_path)
    assert fc.refresh_free_catalog() is False
    assert cl.OPENROUTER_FREE_MODELS == before


def test_refresh_unknown_pricing_gets_paid_sentinel(monkeypatch, tmp_path) -> None:
    """Unknown pricing must yield a conservative non-zero sentinel proof so a
    newer catalog can never leave an older free proof authoritative."""
    _reset()
    before = list(cl.OPENROUTER_FREE_MODELS)
    cat = [_catalog_entry("m/u:free", prompt=None, completion=None), _catalog_entry("m/p:paid", prompt="0.001", completion="0.002")]
    monkeypatch.setattr(fc, "_fetch_catalog_models", lambda timeout=None: cat)
    monkeypatch.setattr(fc, "_FOUNDATION", tmp_path)
    assert fc.refresh_free_catalog() is False, "no exact-$0 text model in this catalog"
    assert cl.OPENROUTER_FREE_MODELS == before


def test_refresh_force_bypasses_fetched_flag(monkeypatch, tmp_path) -> None:
    _reset()
    cat = [_catalog_entry("m/z:free")]
    monkeypatch.setattr(fc, "_fetch_catalog_models", lambda timeout=None: cat)
    monkeypatch.setattr(fc, "_FOUNDATION", tmp_path)
    assert fc.refresh_free_catalog(force=True) is True
    assert cl.OPENROUTER_FREE_MODELS == ["m/z:free"]


def test_start_background_refresh_is_idempotent() -> None:
    _reset()
    fc._refresh_thread_started = True
    fc.start_background_refresh()
    fc.start_background_refresh()
    assert fc._refresh_thread_started is True
