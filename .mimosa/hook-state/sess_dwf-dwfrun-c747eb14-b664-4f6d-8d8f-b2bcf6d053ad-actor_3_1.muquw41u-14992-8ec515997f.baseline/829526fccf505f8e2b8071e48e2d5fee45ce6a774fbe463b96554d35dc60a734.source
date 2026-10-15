from __future__ import annotations


def test_fallback_watcher_delegates_background_refresh(monkeypatch):
    from scp.llm_gateway import fallback_watcher, free_catalog

    calls = []
    monkeypatch.setattr(free_catalog, "start_background_refresh", lambda: calls.append("start"))

    fallback_watcher.start_fallback_watcher()

    assert calls == ["start"]


def test_fallback_watcher_run_once_delegates_without_task_map_mutation(monkeypatch):
    from scp.llm_gateway import client, fallback_watcher, free_catalog

    before = dict(client.OpenRouterProvider.TASK_FREE_FALLBACK_MAP)
    calls = []

    def fake_refresh(*, force=False):
        calls.append(force)
        return True

    monkeypatch.setattr(free_catalog, "refresh_free_catalog", fake_refresh)

    assert fallback_watcher._run_once() is True
    assert calls == [True]
    assert client.OpenRouterProvider.TASK_FREE_FALLBACK_MAP == before
