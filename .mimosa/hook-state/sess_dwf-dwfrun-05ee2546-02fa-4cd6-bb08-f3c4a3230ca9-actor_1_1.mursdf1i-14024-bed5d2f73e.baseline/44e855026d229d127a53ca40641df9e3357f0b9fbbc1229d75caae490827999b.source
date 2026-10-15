"""Persistence authority (26-P0.4).

Named `scp.persistence` (NOT `scp.foundation` - that package is already taken
by the AIParser/BatchAPIProcessor utilities): one migration authority for the
P0 databases so subsystems never open SQLite directly or invent their own
transaction semantics.
"""
from scp.persistence.db import FoundationDB, MigrationError

__all__ = ["FoundationDB", "MigrationError"]
