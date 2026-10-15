"""PostgreSQL event bus — durable table + NOTIFY wake-up (Track C2).

ADOPT-AND-FIX Track C2: inter-container event delivery on PostgreSQL
(psycopg 3), following the V2 "borrow the platform" plan.

Design contract (mandatory, from the audit lesson that NOTIFY is NOT a queue):

    The durable ``scp_events`` TABLE is the source of truth. PostgreSQL
    LISTEN/NOTIFY is ONLY a wake-up bell that makes the next poll happen
    sooner. ``publish()`` commits the row and raises ``pg_notify`` inside the
    SAME transaction, so the two are atomic: an event is visible in the table
    if and only if its bell could ring. A NOTIFY that is never heard
    (listener down at publish time, restart, network blip, wake-up lost)
    loses nothing — the row is already committed and is recovered by
    ``replay_undelivered()`` (or by a subscriber started with
    ``start_at="beginning"``). Nobody may treat NOTIFY itself as delivery.

Delivery semantics:

- At-least-once per subscriber cursor. ``subscribe_poll()`` polls rows with
  ``id > cursor`` in id order, calls the handler, then marks the row
  ``delivered_at``. If the process dies between the handler call and the
  delivered-at update, the event is processed again on restart — handlers
  MUST be idempotent.
- Handler failure: logged (with traceback), the row is NOT marked delivered,
  its ``attempts`` counter is incremented, and the channel cursor does not
  advance past it (retry on the next wake-up/poll — in-order delivery with
  bounded head-of-line blocking). After ``max_attempts`` consecutive
  failures the row is marked ``dead = TRUE`` and logged at CRITICAL
  (poison-message guard), and the cursor advances past it so one poison
  payload can never block the channel forever.
- ``delivered_at`` is a channel-level acknowledgement ("at least one
  subscriber processed it"), used by ``replay_undelivered()`` to repair the
  window when a listener was down. Per-subscriber fan-out correctness comes
  from independent cursors, not from ``delivered_at``.

Security/robustness invariants:

- 100% parameterized DML: every value (including the channel string and
  notification payload) goes through bind parameters, and the LISTEN statement
  is a compile-time constant (fixed wake channel, see ``_WAKE_CHANNEL``):
  this module constructs no SQL text from variables at all — no f-strings,
  no concatenation, no psycopg sql composition. Fail-closed.
- Fail-closed: ``publish()`` never swallows an error (raise on any failure);
  a broken listen/poll connection propagates loudly (fail loudly), because
  events are durable in the table and a supervisor restart + replay is the
  recovery path, not silent reconnection.
- Channel names are validated (1-63 chars of ``[A-Za-z0-9._:-]``) so a channel
  is always safe as data (table filter + NOTIFY channel argument); DSNs are
  never logged (only a redacted form is used in messages).
"""
from __future__ import annotations

import logging
import os
import re
import select as _select
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

logger = logging.getLogger(__name__)

_SCHEMA_FILE = Path(__file__).with_name("event_bus_pg_schema.sql")

_CHANNEL_RE = re.compile(r"^[A-Za-z0-9._:-]{1,63}$")
# Fixed wake-up bell channel. LISTEN is a PostgreSQL utility statement: it
# accepts an identifier and NO bind parameters, so a per-event-channel LISTEN
# would force the SQL statement text to be built from a variable (the exact
# dynamic-SQL shape the security gate flags). The design contract above makes
# NOTIFY a pure optimization — the durable table is the source of truth and
# every poll re-filters by the subscriber's own channel — so ONE constant bell
# channel for the whole bus preserves every delivery semantic: any publish
# wakes every listener, each listener's (indexed) poll selects only its own
# channel's rows, and a bell that carries unrelated news just causes one
# empty poll. The name is a compile-time constant that satisfies
# _CHANNEL_RE, so it can never collide with user-channel quoting concerns.
_WAKE_CHANNEL = "scp_bus_wake"
# Upper bound on one select.wait slice: bounds subscriber stop() latency and
# re-checks stop_event without changing table-poll frequency (NOTIFY wakes
# immediately regardless).
_SELECT_SLICE_SECONDS = 0.25

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """One durable event handed to a handler."""

    id: int
    channel: str
    payload: Any
    correlation_id: str | None
    created_at: Any
    attempts: int = 0


def _validate_channel(channel: str) -> None:
    if not isinstance(channel, str) or not _CHANNEL_RE.fullmatch(channel):
        raise ValueError(
            f"invalid event bus channel {channel!r}: must be 1-63 chars of "
            "[A-Za-z0-9._:-] (fail-closed: channel is used as a NOTIFY identifier)"
        )


# --------------------------------------------------------------------------- #
# SQL (identifiers are compile-time constants; values are always bound)       #
# --------------------------------------------------------------------------- #
_SQL_INSERT_EVENT = (
    "INSERT INTO scp_events (channel, payload, correlation_id) "
    "VALUES (%s, %s, %s) RETURNING id"
)
_SQL_NOTIFY_EVENT = "SELECT pg_notify(%s, %s)"
_SQL_MAX_ID = (
    "SELECT coalesce(max(id), 0) AS max_id FROM scp_events WHERE channel = %s"
)
_SQL_POLL_BATCH = (
    "SELECT id, channel, payload, correlation_id, created_at, attempts "
    "FROM scp_events WHERE channel = %s AND id > %s AND dead = FALSE "
    "ORDER BY id LIMIT %s"
)
_SQL_MARK_DELIVERED = "UPDATE scp_events SET delivered_at = now() WHERE id = %s"
_SQL_BUMP_ATTEMPTS = "UPDATE scp_events SET attempts = %s WHERE id = %s"
_SQL_MARK_DEAD = "UPDATE scp_events SET attempts = %s, dead = TRUE WHERE id = %s"
_SQL_REPLAY_BATCH = (
    "SELECT id, channel, payload, correlation_id, created_at, attempts "
    "FROM scp_events WHERE channel = %s AND delivered_at IS NULL AND dead = FALSE "
    "AND id > %s ORDER BY id LIMIT %s"
)


class PgEventBus:
    """Durable PostgreSQL event bus (table = source of truth, NOTIFY = bell)."""

    def __init__(self, dsn: str, *, connect_timeout: int = 5) -> None:
        self.dsn = str(dsn)
        self.connect_timeout = int(connect_timeout)
        self._conn_local = threading.local()
        self._all_conns: list[Any] = []
        self._conn_guard = threading.Lock()
        self._closed = False

    # ------------------------------------------------------------------ #
    # connection lifecycle                                                #
    # ------------------------------------------------------------------ #
    def redacted_dsn(self) -> str:
        """DSN with the password masked — the only form safe for logs."""
        try:
            info = psycopg.conninfo.conninfo_to_dict(self.dsn)
            if info.get("password"):
                info["password"] = "***"
            return psycopg.conninfo.make_conninfo(**info)
        except Exception:
            logger.debug("redacted_dsn ignored", exc_info=True)
            return "<redacted-dsn>"

    def _make_conn(self, *, row_factory: Any = None) -> Any:
        kwargs: dict[str, Any] = {
            "autocommit": True,
            "connect_timeout": self.connect_timeout,
        }
        if row_factory is not None:
            kwargs["row_factory"] = row_factory
        return psycopg.connect(self.dsn, **kwargs)

    def _publish_conn(self) -> Any:
        conn = getattr(self._conn_local, "conn", None)
        if conn is None:
            conn = self._make_conn()
            self._conn_local.conn = conn
            with self._conn_guard:
                self._all_conns.append(conn)
        return conn

    def close(self) -> None:
        with self._conn_guard:
            for conn in self._all_conns:
                try:
                    conn.close()
                except psycopg.Error:
                    logger.debug("PgEventBus.close: psycopg.Error ignored", exc_info=True)
            self._all_conns.clear()
            self._conn_local = threading.local()
            self._closed = True

    # ------------------------------------------------------------------ #
    # schema                                                              #
    # ------------------------------------------------------------------ #
    def ensure_schema(self) -> None:
        """Apply the canonical DDL (``event_bus_pg_schema.sql``); idempotent."""
        ddl = _SCHEMA_FILE.read_text(encoding="utf-8")
        conn = self._publish_conn()
        with conn.transaction():
            conn.execute(ddl)

    # ------------------------------------------------------------------ #
    # publish (durable row + bell, atomic)                                #
    # ------------------------------------------------------------------ #
    def publish(self, channel: str, payload: Any, correlation_id: str | None = None) -> int:
        """Insert the event row and raise ``pg_notify`` in the SAME transaction.

        Returns the assigned event id. Fail-closed: any error propagates
        (raise); the transaction is rolled back by the server so a failed
        publish never leaves a half state (row without bell or vice versa —
        the row IS the delivery guarantee, the bell is only an optimization).
        """
        _validate_channel(channel)
        conn = self._publish_conn()
        try:
            with conn.transaction():
                cur = conn.execute(
                    _SQL_INSERT_EVENT, (channel, Json(payload), correlation_id)
                )
                event_id = int(cur.fetchone()[0])
                # The bell carries only the id: the table row is the message.
                # (Fixed bell channel — see _WAKE_CHANNEL; still parameterized
                # and still inside the SAME transaction as the insert.)
                conn.execute(_SQL_NOTIFY_EVENT, (_WAKE_CHANNEL, str(event_id)))
            return event_id
        except Exception:
            # Cleanup, not swallowing: clear the aborted transaction state so
            # this connection stays usable, then re-raise the original error.
            try:
                if conn.info.transaction_status not in (0, 1):  # not IDLE
                    conn.rollback()
            except psycopg.Error:
                logger.debug("PgEventBus.publish: rollback cleanup failed", exc_info=True)
            raise

    # ------------------------------------------------------------------ #
    # subscribe (poll cursor; NOTIFY only accelerates the next poll)      #
    # ------------------------------------------------------------------ #
    def subscribe_poll(
        self,
        channel: str,
        handler: EventHandler,
        poll_interval: float,
        stop_event: threading.Event,
        *,
        start_at: str = "tail",
        max_attempts: int = 3,
        batch_limit: int = 200,
        ready_event: threading.Event | None = None,
    ) -> dict[str, int]:
        """Blocking subscribe loop; returns stats when ``stop_event`` is set.

        Loop: poll the durable table with an id cursor (last_seen_id), call
        ``handler(event)`` per row in id order, mark ``delivered_at`` on
        success. A dedicated LISTEN connection waits via ``select.select``;
        receiving a NOTIFY (the bell) only moves the next poll earlier —
        correctness never depends on it.

        ``start_at="tail"`` (default) begins at the current max id — a new
        live subscriber; history/missed events are repaired by
        ``replay_undelivered()``. ``start_at="beginning"`` processes the whole
        non-dead channel history through the handler.

        A broken connection propagates loudly (fail loudly): events stay
        durable in the table; the supervisor restarts the listener and
        ``replay_undelivered()`` recovers the window.
        """
        _validate_channel(channel)
        if poll_interval <= 0:
            raise ValueError("poll_interval must be > 0")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if batch_limit < 1:
            raise ValueError("batch_limit must be >= 1")
        if start_at not in ("tail", "beginning"):
            raise ValueError("start_at must be 'tail' or 'beginning'")

        stats: dict[str, int] = {
            "poll_cycles": 0,
            "notify_wakes": 0,
            "processed": 0,
            "failed": 0,
            "dead_lettered": 0,
        }
        poll_conn = self._make_conn(row_factory=dict_row)
        listen_conn = self._make_conn()
        try:
            # 1. LISTEN first, 2. THEN snapshot the cursor: any event published
            # after the snapshot rings the bell, so the tail start has no gap.
            # The statement is a compile-time constant (fixed wake channel —
            # see _WAKE_CHANNEL): no variable ever enters SQL text here.
            listen_conn.execute("LISTEN scp_bus_wake")
            if start_at == "tail":
                row = poll_conn.execute(_SQL_MAX_ID, (channel,)).fetchone()
                cursor = int(row["max_id"])
            else:
                cursor = 0
            if ready_event is not None:
                ready_event.set()

            deadline = time.monotonic()  # first poll cycle immediately
            while not stop_event.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    cursor, batch_full = self._poll_cycle(
                        channel, handler, cursor, poll_conn, max_attempts, batch_limit, stats
                    )
                    # Full batch -> more backlog likely: drain again at once.
                    deadline = time.monotonic() + (0.0 if batch_full else poll_interval)
                    continue
                timeout = min(remaining, _SELECT_SLICE_SECONDS)
                try:
                    ready, _, _ = _select.select([listen_conn], [], [], timeout)
                except (OSError, ValueError):
                    # Broken listen socket: fail loudly (events are durable;
                    # recovery = restart + replay, not silent reconnect).
                    raise
                if ready:
                    stats["notify_wakes"] += 1
                    received = 0
                    for _ in listen_conn.notifies(timeout=0):  # non-blocking drain
                        received += 1
                    if received:
                        deadline = 0.0  # bell rang -> poll immediately
            return stats
        finally:
            for conn in (listen_conn, poll_conn):
                try:
                    conn.close()
                except psycopg.Error:
                    logger.debug("PgEventBus.subscribe_poll: close ignored", exc_info=True)

    def _poll_cycle(
        self,
        channel: str,
        handler: EventHandler,
        cursor: int,
        poll_conn: Any,
        max_attempts: int,
        batch_limit: int,
        stats: dict[str, int],
    ) -> tuple[int, bool]:
        rows = poll_conn.execute(
            _SQL_POLL_BATCH, (channel, cursor, batch_limit)
        ).fetchall()
        batch_full = len(rows) >= batch_limit
        for row in rows:
            event = Event(
                id=int(row["id"]),
                channel=str(row["channel"]),
                payload=row["payload"],
                correlation_id=row["correlation_id"],
                created_at=row["created_at"],
                attempts=int(row["attempts"]),
            )
            outcome = self._attempt(event, row["attempts"], handler, poll_conn, max_attempts, stats)
            if outcome == "retry":
                # Head-of-line blocking until success or dead: cursor stays.
                return cursor, batch_full
            cursor = event.id
        return cursor, batch_full

    def _attempt(
        self,
        event: Event,
        row_attempts: Any,
        handler: EventHandler,
        conn: Any,
        max_attempts: int,
        stats: dict[str, int],
    ) -> str:
        """Run the handler once; update delivery state. Returns ok|retry|dead."""
        try:
            handler(event)
        except Exception:
            attempts = int(row_attempts) + 1
            logger.exception(
                "event bus: handler failed for channel=%s id=%s (attempt %s/%s) — "
                "event NOT marked delivered, will retry",
                event.channel,
                event.id,
                attempts,
                max_attempts,
            )
            if attempts >= max_attempts:
                conn.execute(_SQL_MARK_DEAD, (attempts, event.id))
                logger.critical(
                    "event bus: event id=%s channel=%s marked dead=TRUE after %s "
                    "consecutive handler failures (poison-message guard; no "
                    "infinite retry loop)",
                    event.id,
                    event.channel,
                    attempts,
                )
                stats["dead_lettered"] += 1
                return "dead"
            conn.execute(_SQL_BUMP_ATTEMPTS, (attempts, event.id))
            stats["failed"] += 1
            return "retry"
        conn.execute(_SQL_MARK_DELIVERED, (event.id,))
        stats["processed"] += 1
        return "ok"

    # ------------------------------------------------------------------ #
    # replay (repair window when the listener was down)                   #
    # ------------------------------------------------------------------ #
    def replay_undelivered(
        self,
        channel: str,
        handler: EventHandler,
        *,
        max_attempts: int = 3,
        batch_limit: int = 200,
    ) -> int:
        """Single pass over every ``delivered_at IS NULL`` (non-dead) event.

        This is the recovery path that makes lost NOTIFYs harmless: events
        published while the listener was down are still in the table and are
        replayed here in id order. Handler failures are NOT marked delivered
        (they stay for the next replay, bounded by ``attempts``/``dead``).
        Each row is visited at most once per call (the fetch cursor advances
        past failed rows; retry happens on the NEXT replay call).
        Returns the number of events delivered by this call.
        """
        _validate_channel(channel)
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if batch_limit < 1:
            raise ValueError("batch_limit must be >= 1")
        conn = self._make_conn(row_factory=dict_row)
        recovered = 0
        stats: dict[str, int] = {"processed": 0, "failed": 0, "dead_lettered": 0}
        try:
            fetch_cursor = 0
            while True:
                rows = conn.execute(
                    _SQL_REPLAY_BATCH, (channel, fetch_cursor, batch_limit)
                ).fetchall()
                if not rows:
                    break
                for row in rows:
                    fetch_cursor = int(row["id"])  # advance the fetch window
                    event = Event(
                        id=int(row["id"]),
                        channel=str(row["channel"]),
                        payload=row["payload"],
                        correlation_id=row["correlation_id"],
                        created_at=row["created_at"],
                        attempts=int(row["attempts"]),
                    )
                    outcome = self._attempt(
                        event, row["attempts"], handler, conn, max_attempts, stats
                    )
                    if outcome == "ok":
                        recovered += 1
                    # retry -> stays undelivered for the next replay call;
                    # dead -> skipped by the query from now on.
        finally:
            try:
                conn.close()
            except psycopg.Error:
                logger.debug("PgEventBus.replay_undelivered: close ignored", exc_info=True)
        return recovered


# --------------------------------------------------------------------------- #
# factory (opt-in, mirroring make_storage from Track C1)                      #
# --------------------------------------------------------------------------- #
_TRUTHY = ("1", "true", "yes", "on")


def make_event_bus() -> PgEventBus | None:
    """Create the event bus from env; **default disabled** (opt-in like C1).

    Resolution:
      - ``SCP_EVENT_BUS_ENABLED`` unset/falsey (``0/false/no/off``) -> ``None``
        (feature off; callers MUST handle ``None`` — nothing is silently
        started).
      - truthy + ``SCP_EVENT_BUS_DSN`` -> :class:`PgEventBus`.
      - truthy but DSN missing -> ``RuntimeError`` (fail-closed: no silent
        fallback to an in-process bus or to the kernel DSN).
    """
    enabled = os.environ.get("SCP_EVENT_BUS_ENABLED", "").strip().lower()
    if enabled not in _TRUTHY:
        return None
    dsn = os.environ.get("SCP_EVENT_BUS_DSN", "").strip()
    if not dsn:
        raise RuntimeError(
            "SCP_EVENT_BUS_ENABLED is set but SCP_EVENT_BUS_DSN is missing "
            "(fail-closed: refusing to fall back to a disabled/no-op bus)."
        )
    return PgEventBus(dsn)


__all__ = ["Event", "PgEventBus", "make_event_bus"]
