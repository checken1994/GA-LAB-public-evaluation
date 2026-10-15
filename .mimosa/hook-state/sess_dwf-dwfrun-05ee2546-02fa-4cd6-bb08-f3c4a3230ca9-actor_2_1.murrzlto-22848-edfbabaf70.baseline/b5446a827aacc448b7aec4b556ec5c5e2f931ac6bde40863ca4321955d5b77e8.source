"""PgEventBus delivery suite — durable table + NOTIFY wake-up (Track C2).

Contract under test (ADOPT-AND-FIX-PLAN Track C2): the scp_events TABLE is the
source of truth and NOTIFY is only a wake-up bell. The decisive property is
(b): a listener that is DOWN at publish time loses nothing — events stay
durable in the table and a fresh listener's replay delivers all of them.

Tests (real PostgreSQL, no mocks; docker postgres:16-alpine):
  (a) publish -> poll receives exact payloads in id order
  (b) listener down during 5 publishes -> fresh listener replay_undelivered
      receives all 5 (NOTIFY-miss must be harmless)  [the key test]
  (c) handler fails twice -> retried -> succeeds on 3rd -> delivered
  (d) handler fails max_attempts times -> dead=TRUE, no infinite loop,
      channel cursor unblocked (next event still delivered)
  (e) NOTIFY wake-up: handler fires well below poll_interval, via the
      notification path (notify_wakes >= 1), not the periodic poll
  (f) two subscribers on one channel -> both receive every event (fan-out
      via independent cursors)
  (g) publish fail-closed: unserializable payload raises, no row written;
      invalid channel raises before touching the DB
  (h) schema objects: scp_events columns + (channel, id) index exist on real PG
  (i) make_event_bus factory: default disabled -> None; enabled without DSN
      -> RuntimeError fail-closed (no PG needed for these)

Infra discipline (same as Track C1 suites):
- Requires ``SCP_PG_TEST_DSN``. Absent -> declared infra-skip with the docker
  hint (no assertion hidden). Set but unreachable -> INFRA-SKIP with the
  original error visible.
- Per-test schema isolation (``scp_evb_<hex>``), dropped on teardown.
- DSNs are never printed; failures surface only redacted context.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any

import psycopg
import pytest
from psycopg import sql as pg_sql
from psycopg.rows import dict_row

from scp.event_bus_pg import Event, PgEventBus, make_event_bus

PG_DSN_ENV = "SCP_PG_TEST_DSN"
_DOCKER_HINT = (
    "docker run -d --rm --name scp-pg-test -e POSTGRES_PASSWORD=scppg "
    "-e POSTGRES_DB=scpkernel -p 55432:5432 postgres:16-alpine"
)
_WAIT_TIMEOUT = 15.0
_POLL = 0.1  # small poll interval for non-(e) tests: correctness never
            # depends on NOTIFY, so the periodic poll alone must deliver


# --------------------------------------------------------------------------- #
# fixtures                                                                    #
# --------------------------------------------------------------------------- #
def _scoped_dsn(base_dsn: str, schema: str) -> str:
    # keyword/value pairs cannot be appended to a URI conninfo; use
    # make_conninfo so the base DSN may be URI or keyword form (C1 pattern).
    return psycopg.conninfo.make_conninfo(base_dsn, options=f"-c search_path={schema}")


@pytest.fixture()
def evb() -> Any:
    """PgEventBus bound to a fresh per-test schema (real PG, no mocks)."""
    dsn = os.environ.get(PG_DSN_ENV, "").strip()
    if not dsn:
        pytest.skip(
            f"{PG_DSN_ENV} not set — PgEventBus suite needs a real PostgreSQL "
            f"({_DOCKER_HINT}); declared infra-skip (no assertion hidden)"
        )
    schema = f"scp_evb_{uuid.uuid4().hex[:10]}"
    try:
        admin = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except psycopg.OperationalError as exc:
        pytest.skip(f"INFRA-SKIP: PostgreSQL unreachable ({exc})")
    try:
        # schema name is a self-generated per-test identifier; it reaches SQL
        # only through psycopg.sql.Identifier (sanctioned dynamic-identifier
        # path, same shape as the C1 migration script)
        admin.execute(
            pg_sql.SQL("CREATE SCHEMA {}").format(pg_sql.Identifier(schema))
        )
        scoped = _scoped_dsn(dsn, schema)
        bus = PgEventBus(scoped)
        bus.ensure_schema()
        bus._test_scoped_dsn = scoped  # type: ignore[attr-defined] (test-only)
        yield bus
        bus.close()
    finally:
        try:
            admin.execute(
                pg_sql.SQL("DROP SCHEMA {} CASCADE").format(pg_sql.Identifier(schema))
            )
        finally:
            admin.close()


@pytest.fixture()
def sql_conn(evb: PgEventBus) -> Any:
    """Raw assertion connection on the same per-test schema."""
    conn = psycopg.connect(evb._test_scoped_dsn, autocommit=True, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _wait_until(predicate: Any, timeout: float = _WAIT_TIMEOUT, what: str = "condition") -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    pytest.fail(f"timed out waiting for {what} after {timeout}s")


def _run_subscriber(
    bus: PgEventBus,
    channel: str,
    handler: Any,
    poll_interval: float,
    stop_event: threading.Event,
    ready_event: threading.Event | None = None,
    **kwargs: Any,
) -> tuple[threading.Thread, dict[str, Any]]:
    """Start subscribe_poll in a daemon thread; stats/exception land in box."""
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["stats"] = bus.subscribe_poll(
                channel, handler, poll_interval, stop_event, ready_event=ready_event, **kwargs
            )
        except Exception as exc:  # surfaced to the test thread
            box["error"] = exc

    thread = threading.Thread(target=run, daemon=True, name=f"subscriber-{channel}")
    thread.start()
    return thread, box


def _stop_subscriber(thread: threading.Thread, stop_event: threading.Event, box: dict[str, Any]) -> dict[str, int]:
    stop_event.set()
    thread.join(timeout=10)
    assert not thread.is_alive(), "subscriber loop did not stop within 10s"
    if "error" in box:
        raise box["error"]
    assert "stats" in box, "subscriber ended without stats"
    return box["stats"]


def _delivered_ids(conn: Any, channel: str) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM scp_events WHERE channel = %s AND delivered_at IS NOT NULL ORDER BY id",
        (channel,),
    ).fetchall()
    return [int(r["id"]) for r in rows]


# --------------------------------------------------------------------------- #
# (a) publish -> poll: payload + order                                        #
# --------------------------------------------------------------------------- #
def test_a_publish_poll_receives_payload_in_id_order(evb: PgEventBus, sql_conn: Any) -> None:
    channel = "task.state.changed"
    received: list[Event] = []
    stop = threading.Event()
    ready = threading.Event()

    thread, box = _run_subscriber(evb, channel, received.append, _POLL, stop, ready, start_at="tail")
    assert ready.wait(10), "subscriber not ready (LISTEN + cursor snapshot)"

    published = [
        (evb.publish(channel, {"task": f"t{i}", "to": "RUNNING"}, correlation_id=f"c{i}"), {"task": f"t{i}", "to": "RUNNING"}, f"c{i}")
        for i in range(3)
    ]

    _wait_until(lambda: len(received) == 3, what="3 events delivered")
    stats = _stop_subscriber(thread, stop, box)

    assert [e.id for e in received] == [p[0] for p in published], "id order violated"
    for event, (_, payload, corr) in zip(received, published):
        assert event.payload == payload
        assert event.correlation_id == corr
        assert event.channel == channel
    assert _delivered_ids(sql_conn, channel) == [p[0] for p in published]
    assert stats["processed"] == 3


# --------------------------------------------------------------------------- #
# (b) THE KEY TEST: listener down during publish -> nothing lost              #
# --------------------------------------------------------------------------- #
def test_b_listener_down_publishes_then_replay_delivers_all(evb: PgEventBus, sql_conn: Any) -> None:
    channel = "worker.wake"
    # No subscriber exists. Publish 5 events "into the void".
    payloads = [{"seq": i, "kind": "wake", "task": f"t{i}"} for i in range(5)]
    ids = [evb.publish(channel, p, correlation_id=f"corr-{i}") for i, p in enumerate(payloads)]
    assert len(ids) == 5 and len(set(ids)) == 5

    rows = sql_conn.execute(
        "SELECT id, payload, correlation_id, delivered_at FROM scp_events "
        "WHERE channel = %s ORDER BY id",
        (channel,),
    ).fetchall()
    assert [int(r["id"]) for r in rows] == ids
    # Every event is durable, undelivered (NOTIFY rang for nobody).
    assert all(r["delivered_at"] is None for r in rows), "events must not be lost nor auto-delivered"

    # A FRESH listener (separate PgEventBus = separate connections, like a
    # restarted process) comes up and repairs the window.
    fresh_bus = PgEventBus(evb._test_scoped_dsn)
    try:
        replayed: list[Event] = []
        recovered = fresh_bus.replay_undelivered(channel, replayed.append)
        assert recovered == 5, "replay must deliver every undelivered event"
        assert [e.id for e in replayed] == ids, "replay must preserve id order"
        assert [e.payload for e in replayed] == payloads
        assert [e.correlation_id for e in replayed] == [f"corr-{i}" for i in range(5)]
    finally:
        fresh_bus.close()

    # Postcondition in the DB (independent of handler bookkeeping): all
    # delivered now, none dead, none retried.
    rows = sql_conn.execute(
        "SELECT id, delivered_at, attempts, dead FROM scp_events WHERE channel = %s ORDER BY id",
        (channel,),
    ).fetchall()
    assert all(r["delivered_at"] is not None for r in rows)
    assert all(r["attempts"] == 0 and not r["dead"] for r in rows)

    # And the channel is live again: a new publish + fresh subscriber works.
    received: list[Event] = []
    stop = threading.Event()
    ready = threading.Event()
    thread, box = _run_subscriber(evb, channel, received.append, _POLL, stop, ready, start_at="tail")
    try:
        assert ready.wait(10)
        live_id = evb.publish(channel, {"seq": "live"})
        _wait_until(lambda: [e.id for e in received] == [live_id], what="post-recovery event")
        assert received[0].payload == {"seq": "live"}
    finally:
        _stop_subscriber(thread, stop, box)


# --------------------------------------------------------------------------- #
# (c) handler fails twice -> retry -> delivered                               #
# --------------------------------------------------------------------------- #
def test_c_handler_fails_twice_then_succeeds_delivered(evb: PgEventBus, sql_conn: Any) -> None:
    channel = "attempt.reporting"
    calls = 0

    def flaky_handler(event: Event) -> None:
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise RuntimeError(f"injected failure #{calls}")

    received: list[Event] = []
    stop = threading.Event()
    ready = threading.Event()

    def handler(event: Event) -> None:
        flaky_handler(event)
        received.append(event)

    thread, box = _run_subscriber(evb, channel, handler, _POLL, stop, ready, start_at="tail", max_attempts=3)
    try:
        assert ready.wait(10)
        event_id = evb.publish(channel, {"n": 1})
        _wait_until(
            lambda: sql_conn.execute(
                "SELECT delivered_at, attempts, dead FROM scp_events WHERE id = %s", (event_id,)
            ).fetchone()["delivered_at"] is not None,
            what="event delivered after retries",
        )
        row = sql_conn.execute(
            "SELECT delivered_at, attempts, dead FROM scp_events WHERE id = %s", (event_id,)
        ).fetchone()
        assert calls == 3, f"handler must run exactly 3 times (2 fails + 1 pass), ran {calls}"
        assert received and received[0].id == event_id
        assert row["attempts"] == 2, "two failures must be recorded in attempts"
        assert not row["dead"], "must not be dead-lettered when the 3rd attempt passes"
    finally:
        stats = _stop_subscriber(thread, stop, box)
    assert stats["failed"] == 2 and stats["processed"] == 1 and stats["dead_lettered"] == 0


# --------------------------------------------------------------------------- #
# (d) poison message -> dead-letter, no infinite loop, channel unblocked      #
# --------------------------------------------------------------------------- #
def test_d_poison_message_dead_letter_then_channel_unblocked(
    evb: PgEventBus, sql_conn: Any, caplog: Any
) -> None:
    import logging

    channel = "poison.probe"

    def handler(event: Event) -> None:
        if event.payload.get("kind") == "poison":
            raise RuntimeError("poison payload")

    delivered: list[Event] = []
    stop = threading.Event()
    ready = threading.Event()

    def handler_collect(event: Event) -> None:
        handler(event)
        delivered.append(event)

    with caplog.at_level(logging.CRITICAL, logger="scp.event_bus_pg"):
        thread, box = _run_subscriber(
            evb, channel, handler_collect, _POLL, stop, ready, start_at="tail", max_attempts=3
        )
        try:
            assert ready.wait(10)
            poison_id = evb.publish(channel, {"kind": "poison"})
            _wait_until(
                lambda: sql_conn.execute(
                    "SELECT dead, attempts, delivered_at FROM scp_events WHERE id = %s", (poison_id,)
                ).fetchone()["dead"],
                what="poison event dead-lettered",
            )
            row = sql_conn.execute(
                "SELECT dead, attempts, delivered_at FROM scp_events WHERE id = %s", (poison_id,)
            ).fetchone()
            assert row["attempts"] == 3, "exactly max_attempts handler runs, then dead"
            assert row["delivered_at"] is None, "dead event must stay undelivered"

            # The channel cursor moved PAST the dead row: a healthy event flows.
            healthy_id = evb.publish(channel, {"kind": "healthy"})
            _wait_until(lambda: healthy_id in [e.id for e in delivered], what="healthy event delivered")
        finally:
            stats = _stop_subscriber(thread, stop, box)

    assert stats["dead_lettered"] == 1 and stats["processed"] == 1
    # Fail-loudly contract: the dead-lettering is CRITICAL-logged, never silent.
    criticals = [r for r in caplog.records if r.levelno >= logging.CRITICAL and "dead" in r.getMessage()]
    assert criticals, "dead-lettering must be logged at CRITICAL"


# --------------------------------------------------------------------------- #
# (e) NOTIFY wake-up: delivery well below poll_interval via the bell          #
# --------------------------------------------------------------------------- #
def test_e_notify_wakes_subscriber_below_poll_interval(evb: PgEventBus, sql_conn: Any) -> None:
    channel = "notify.bell"
    big_interval = 60.0  # >> test patience: only the bell can deliver in time
    received: list[tuple[float, Event]] = []
    stop = threading.Event()
    ready = threading.Event()

    def handler(event: Event) -> None:
        received.append((time.monotonic(), event))

    thread, box = _run_subscriber(
        evb, channel, handler, big_interval, stop, ready, start_at="tail"
    )
    try:
        assert ready.wait(10)
        time.sleep(0.5)  # let the subscriber settle into its (long) wait
        t0 = time.monotonic()
        event_id = evb.publish(channel, {"wake": True})
        _wait_until(lambda: any(e.id == event_id for _, e in received), timeout=10.0,
                    what="NOTIFY-woken delivery")
        latency = received[-1][0] - t0
        assert latency < big_interval, "delivery must beat the poll interval (NOTIFY wake)"
        assert latency < 10.0, f"NOTIFY wake took {latency:.2f}s — bell path too slow"
    finally:
        stats = _stop_subscriber(thread, stop, box)
    assert stats["notify_wakes"] >= 1, "wake must be attributed to the NOTIFY path"
    assert stats["processed"] == 1


# --------------------------------------------------------------------------- #
# (f) two subscribers on one channel: fan-out via independent cursors         #
# --------------------------------------------------------------------------- #
def test_f_two_subscribers_fan_out_both_receive_all(evb: PgEventBus, sql_conn: Any) -> None:
    channel = "fanout.check"
    got1: list[Event] = []
    got2: list[Event] = []
    stop1, stop2 = threading.Event(), threading.Event()
    ready1, ready2 = threading.Event(), threading.Event()

    thread1, box1 = _run_subscriber(evb, channel, got1.append, _POLL, stop1, ready1, start_at="tail")
    thread2, box2 = _run_subscriber(evb, channel, got2.append, _POLL, stop2, ready2, start_at="tail")
    try:
        assert ready1.wait(10) and ready2.wait(10)
        payloads = [{"i": i} for i in range(3)]
        ids = [evb.publish(channel, p, correlation_id=f"f{i}") for i, p in enumerate(payloads)]
        _wait_until(lambda: len(got1) == 3 and len(got2) == 3, what="both subscribers fan-out")
        assert [e.id for e in got1] == ids, "subscriber 1 id order"
        assert [e.id for e in got2] == ids, "subscriber 2 id order"
        assert [e.payload for e in got1] == payloads
        assert [e.payload for e in got2] == payloads
        assert _delivered_ids(sql_conn, channel) == ids
    finally:
        stats1 = _stop_subscriber(thread1, stop1, box1)
        stats2 = _stop_subscriber(thread2, stop2, box2)
    assert stats1["processed"] == 3 and stats2["processed"] == 3


# --------------------------------------------------------------------------- #
# (g) publish fail-closed                                                     #
# --------------------------------------------------------------------------- #
def test_g_publish_fail_closed(evb: PgEventBus, sql_conn: Any) -> None:
    channel = "failclosed.check"
    # Unserializable payload -> raise, and NO row survives (atomic insert).
    with pytest.raises(Exception):
        evb.publish(channel, object())
    n = sql_conn.execute("SELECT count(*) AS n FROM scp_events WHERE channel = %s", (channel,)).fetchone()["n"]
    assert n == 0, "failed publish must not leave a durable row"

    # Invalid channel -> rejected before touching the database.
    with pytest.raises(ValueError):
        evb.publish("bad channel!", {"x": 1})
    with pytest.raises(ValueError):
        evb.publish("a" * 64, {"x": 1})  # > NAMEDATALEN-1, unsafe as identifier
    n = sql_conn.execute("SELECT count(*) AS n FROM scp_events").fetchone()["n"]
    assert n == 0

    # The connection survives a failed publish (cleanup, not poison state):
    event_id = evb.publish(channel, {"ok": True})
    assert event_id > 0


# --------------------------------------------------------------------------- #
# (h) schema objects on real PG                                               #
# --------------------------------------------------------------------------- #
def test_h_schema_objects(evb: PgEventBus, sql_conn: Any) -> None:
    cols = {
        r["column_name"]: r
        for r in sql_conn.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'scp_events'"
        ).fetchall()
    }
    assert set(cols) == {
        "id", "channel", "payload", "created_at", "delivered_at",
        "correlation_id", "attempts", "dead",
    }
    assert cols["id"]["data_type"] == "bigint" and cols["id"]["is_nullable"] == "NO"
    assert cols["payload"]["data_type"] == "jsonb"
    assert cols["delivered_at"]["is_nullable"] == "YES", "delivered_at must be NULLABLE"
    assert cols["created_at"]["is_nullable"] == "NO"

    indexes = {
        r["indexdef"]
        for r in sql_conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE tablename = 'scp_events'"
        ).fetchall()
    }
    assert any("idx_scp_events_channel_id" in d for d in indexes), indexes
    assert any(
        "idx_scp_events_channel_id" in d and "(channel,id)" in d.replace(" ", "")
        for d in indexes
    ), indexes
    # the partial undelivered index targets exactly the replay hot path
    assert any(
        "idx_scp_events_undelivered" in d and "delivered_at IS NULL" in d for d in indexes
    ), indexes


# --------------------------------------------------------------------------- #
# (i) factory (no PG needed)                                                  #
# --------------------------------------------------------------------------- #
def test_i_factory_default_disabled_and_fail_closed(monkeypatch: Any) -> None:
    monkeypatch.delenv("SCP_EVENT_BUS_ENABLED", raising=False)
    monkeypatch.delenv("SCP_EVENT_BUS_DSN", raising=False)
    assert make_event_bus() is None, "event bus must be opt-in (default disabled)"

    monkeypatch.setenv("SCP_EVENT_BUS_ENABLED", "0")
    monkeypatch.setenv("SCP_EVENT_BUS_DSN", "postgresql://x:y@h/db")
    assert make_event_bus() is None

    monkeypatch.setenv("SCP_EVENT_BUS_ENABLED", "1")
    monkeypatch.delenv("SCP_EVENT_BUS_DSN", raising=False)
    with pytest.raises(RuntimeError):
        make_event_bus()  # enabled without DSN must fail closed

    monkeypatch.setenv("SCP_EVENT_BUS_DSN", "postgresql://x:y@h/db")
    bus = make_event_bus()
    assert isinstance(bus, PgEventBus)
    assert "***" in bus.redacted_dsn() or "password=" not in bus.redacted_dsn()
