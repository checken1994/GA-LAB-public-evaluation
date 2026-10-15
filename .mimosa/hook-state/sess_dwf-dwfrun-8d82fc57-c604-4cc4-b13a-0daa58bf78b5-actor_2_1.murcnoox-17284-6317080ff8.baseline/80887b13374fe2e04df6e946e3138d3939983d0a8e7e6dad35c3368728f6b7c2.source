"""Unified chat memory persistence for SCP sessions across /ask and /chat.

Re-exports and provides access to ChatMemoryStore.
"""
from __future__ import annotations

from scp.core.chat_memory_store import ChatMemoryStore

_store_singleton: ChatMemoryStore | None = None


def get_chat_memory_store() -> ChatMemoryStore:
    """Get or create singleton ChatMemoryStore instance."""
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = ChatMemoryStore()
    return _store_singleton


__all__ = ["ChatMemoryStore", "get_chat_memory_store"]
