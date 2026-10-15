"""Regression tests for HumanConfirmationStore empty-target fail-closed.

[AUDIT-FIX 2026-09-24] is_confirmed(action, target="") used to fail OPEN:
with no target the lookup degenerated to action-only matching, so a
confirmation recorded for ANY target of that action authorized EVERY other
target (e.g. fs.delete confirmed for /tmp/a.txt also matched /home/user).
Fail-closed contract: empty target (no confirmation_id) → False; the
confirmation_id-based override is preserved.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scp.security.confirmation_store import HumanConfirmationStore


@pytest.fixture()
def store(tmp_path: Path) -> HumanConfirmationStore:
    return HumanConfirmationStore(store_path=tmp_path / "confirmations.jsonl")


def test_empty_target_is_denied_fail_closed(store):
    cid = store.record_confirmation(action="fs.delete", target="/tmp/some-file.txt")
    assert cid
    assert store.is_confirmed("fs.delete", target="") is False


def test_real_target_still_validates(store):
    store.record_confirmation(action="fs.delete", target="/tmp/some-file.txt")
    assert store.is_confirmed("fs.delete", target="/tmp/some-file.txt") is True


def test_different_target_of_same_action_does_not_inherit_confirmation(store):
    store.record_confirmation(action="fs.delete", target="/tmp/some-file.txt")
    assert store.is_confirmed("fs.delete", target="/etc/passwd") is False


def test_empty_target_with_confirmation_id_override_still_works(store):
    """The confirmation_id path proves possession of a specific operator record."""
    cid = store.record_confirmation(action="pc.write_file", target="/workspace/a.txt")
    assert store.is_confirmed("pc.write_file", target="", confirmation_id=cid) is True


def test_confirmation_id_with_wrong_target_denied(store):
    cid = store.record_confirmation(action="pc.write_file", target="/workspace/a.txt")
    assert store.is_confirmed("pc.write_file", target="/workspace/b.txt", confirmation_id=cid) is False


def test_empty_target_without_any_confirmation_denied(store):
    assert store.is_confirmed("fs.delete", target="") is False


def test_whitespace_only_target_is_denied(store):
    """A whitespace-only target must not smuggle an action-only match."""
    store.record_confirmation(action="fs.delete", target="/tmp/some-file.txt")
    assert store.is_confirmed("fs.delete", target="   ") is False
