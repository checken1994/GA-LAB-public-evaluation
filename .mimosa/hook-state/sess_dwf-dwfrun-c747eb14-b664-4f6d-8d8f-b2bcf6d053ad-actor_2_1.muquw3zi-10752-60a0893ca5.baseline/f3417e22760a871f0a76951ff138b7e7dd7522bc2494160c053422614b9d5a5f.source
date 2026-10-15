import pytest

from scp.world_state import (
    EntityEventAuthority,
    TemporalAuthority,
    WorldStateProjection,
)


@pytest.fixture()
def authority(tmp_path):
    return TemporalAuthority(tmp_path / "world.sqlite3")


def test_valid_time_and_system_time_are_recorded_separately_and_append_only(authority):
    first = authority.record_observation(subject="sensor:water-a", predicate="reading", value={"ppm": 40}, valid_time="2026-09-01T08:00:00+00:00", evidence_refs=["evidence:1"], actor_id="ingest-1")
    second = authority.record_observation(subject="sensor:water-a", predicate="reading", value={"ppm": 55}, valid_time="2026-09-01T09:00:00+00:00", evidence_refs=["evidence:2"], actor_id="ingest-1")
    assert first["valid_time"] != second["valid_time"]
    assert first["system_time"] <= second["system_time"]
    history = authority.history("sensor:water-a")
    assert len(history) == 2
    assert {h["value_json"] for h in history} == {'{"ppm": 40}', '{"ppm": 55}'}


def test_observation_without_evidence_refs_is_refused(authority):
    with pytest.raises(Exception, match="evidence_refs"):
        authority.record_observation(subject="sensor:x", predicate="reading", value={"v": 1}, valid_time="2026-09-01T08:00:00+00:00", evidence_refs=[], actor_id="ingest-1")


def test_correction_supersedes_and_never_rewrites_history(authority):
    original = authority.record_observation(subject="sensor:x", predicate="reading", value={"v": 1}, valid_time="2026-09-01T08:00:00+00:00", evidence_refs=["evidence:1"], actor_id="ingest-1")
    corrected = authority.correct(original["assertion_id"], new_value={"v": 2}, actor_id="ingest-1", evidence_refs=["evidence:2"])
    assert corrected["assertion_id"] != original["assertion_id"]
    history = authority.history("sensor:x")
    assert len(history) == 2
    superseded = [h for h in history if h["assertion_id"] == original["assertion_id"]][0]
    assert superseded["superseded_by"] == corrected["assertion_id"]


def test_predictor_can_never_promote_its_own_forecast_to_observed(authority):
    prediction = authority.record_prediction(subject="grid:district-a", predicate="outage", value={"likely": True}, valid_time="2026-09-02T18:00:00+00:00", predictor_id="forecaster-1")
    with pytest.raises(Exception, match="predictor"):
        authority.promote_to_observed(prediction["assertion_id"], evidence_refs=["evidence:1"], resolver_id="forecaster-1")
    resolved = authority.promote_to_observed(prediction["assertion_id"], evidence_refs=["evidence:9"], resolver_id="reality-observer-1")
    assert resolved["epistemic_status"] == "OBSERVED"
    assert {h["epistemic_status"] for h in authority.history("grid:district-a")} == {"PREDICTED", "OBSERVED"}


def test_projection_rebuild_is_deterministic_and_respects_supersede(authority):
    projection = WorldStateProjection(authority)
    a = authority.record_observation(subject="sensor:x", predicate="reading", value={"v": 1}, valid_time="2026-09-01T08:00:00+00:00", evidence_refs=["evidence:1"], actor_id="ingest-1")
    authority.correct(a["assertion_id"], new_value={"v": 2}, actor_id="ingest-1", evidence_refs=["evidence:2"])
    state_one = projection.rebuild()
    assert state_one == projection.rebuild()
    readings = state_one["sensor:x"]["reading"]
    assert len(readings) == 1 and readings[0]["value"] == {"v": 2}


def test_projection_as_of_cutoff_keeps_value_until_superseder_was_known(tmp_path, monkeypatch):
    times = iter(("2026-09-03T00:00:00+00:00", "2026-09-03T01:00:00+00:00"))
    monkeypatch.setattr("scp.world_state.temporal_authority.now_utc_iso", lambda: next(times))
    authority = TemporalAuthority(tmp_path / "asof.sqlite3")
    original = authority.record_observation(subject="sensor:x", predicate="reading", value={"v": 1}, valid_time="2026-09-01T08:00:00+00:00", evidence_refs=["evidence:1"], actor_id="ingest-1")
    authority.correct(original["assertion_id"], new_value={"v": 2}, actor_id="ingest-2", evidence_refs=["evidence:2"])
    projection = WorldStateProjection(authority)
    before_correction = projection.rebuild(as_of_system_time="2026-09-03T00:30:00+00:00")
    assert before_correction["sensor:x"]["reading"][0]["value"] == {"v": 1}
    assert projection.current("sensor:x", "reading")["value"] == {"v": 2}


def test_entity_resolution_links_identity_and_preserves_lineage(tmp_path):
    authority = TemporalAuthority(tmp_path / "world.sqlite3")
    entities = EntityEventAuthority(authority)
    for eid, text, minute in (("report-1", "water smells odd", "00"), ("report-2", "same street, same smell", "30")):
        entities.record_event(entity_id=eid, event_kind="complaint", payload={"text": text}, valid_time=f"2026-09-01T08:{minute}:00+00:00", evidence_refs=[f"evidence:{eid}"], actor_id="ingest-1")
    with pytest.raises(ValueError, match="evidence_refs"):
        entities.link_identity("report-1", "report-2", evidence_refs=[], actor_id="resolver-1")
    link = entities.link_identity("report-1", "report-2", evidence_refs=["evidence:identity-link"], actor_id="resolver-1")
    assert link["relation"] == "SAME_ENTITY"
    assert link["evidence_refs"] == ["evidence:identity-link"]
    assert {h["subject"] for h in entities.event_history("report-1")} == {"entity:report-1", "entity:report-2"}


def test_entity_identity_links_are_transitive_and_evidence_backed(tmp_path):
    authority = TemporalAuthority(tmp_path / "world.sqlite3")
    entities = EntityEventAuthority(authority)
    entities.link_identity("A", "B", evidence_refs=["evidence:ab"], actor_id="resolver")
    entities.link_identity("B", "C", evidence_refs=["evidence:bc"], actor_id="resolver")
    assert entities.linked_ids("A") == {"A", "B", "C"}


def test_same_name_different_lineage_never_silently_merged(tmp_path):
    authority = TemporalAuthority(tmp_path / "world.sqlite3")
    entities = EntityEventAuthority(authority)
    entities.record_event(entity_id="facility-alpha", event_kind="registration", payload={"name": "Central Treatment Plant", "location": "District 1"}, valid_time="2026-09-01T08:00:00+00:00", evidence_refs=["evidence:alpha"], actor_id="ingest-1")
    entities.record_event(entity_id="facility-beta", event_kind="registration", payload={"name": "Central Treatment Plant", "location": "District 9"}, valid_time="2026-09-01T08:30:00+00:00", evidence_refs=["evidence:beta"], actor_id="ingest-1")
    assert entities.linked_ids("facility-alpha") == {"facility-alpha"}
    assert entities.linked_ids("facility-beta") == {"facility-beta"}
    state = WorldStateProjection(authority).rebuild()
    assert state["entity:facility-alpha"]["event:registration"][0]["value"]["location"] == "District 1"
    assert state["entity:facility-beta"]["event:registration"][0]["value"]["location"] == "District 9"


def test_temporal_authority_persistence_across_db_restart(tmp_path):
    db_path = tmp_path / "persisted_world.sqlite3"
    authority_1 = TemporalAuthority(db_path)
    obs = authority_1.record_observation(subject="sensor:chlorine", predicate="ppm", value={"reading": 1.2}, valid_time="2026-09-01T10:00:00+00:00", evidence_refs=["evidence:sensor-1"], actor_id="ingest-1")
    authority_1.correct(obs["assertion_id"], new_value={"reading": 1.5}, actor_id="ingest-1", evidence_refs=["evidence:recalibrated"])
    state_before_restart = WorldStateProjection(authority_1).rebuild()
    authority_1.db.close()
    authority_2 = TemporalAuthority(db_path)
    state_after_restart = WorldStateProjection(authority_2).rebuild()
    assert state_before_restart == state_after_restart
    raw_history = authority_2.history("sensor:chlorine")
    assert len(raw_history) == 2
    assert any(h["superseded_by"] is not None for h in raw_history)


def test_change_detection_tracks_state_deltas_without_mutating_past(authority):
    t1 = "2026-09-01T08:00:00+00:00"
    t2 = "2026-09-01T12:00:00+00:00"
    authority.record_observation(subject="water:reservoir-1", predicate="turbidity", value={"ntu": 3.5}, valid_time=t1, evidence_refs=["evidence:t1"], actor_id="sensor-auto")
    authority.record_observation(subject="water:reservoir-1", predicate="turbidity", value={"ntu": 18.2}, valid_time=t2, evidence_refs=["evidence:t2"], actor_id="sensor-auto")
    projection = WorldStateProjection(authority)
    changes = projection.changes("water:reservoir-1", "turbidity")
    assert len(changes) == 1
    assert changes[0]["from_value"] == {"ntu": 3.5}
    assert changes[0]["to_value"] == {"ntu": 18.2}
    assert changes[0]["from_valid_time"] == t1 and changes[0]["to_valid_time"] == t2
    history = authority.history("water:reservoir-1")
    assert len(history) == 2 and history[0]["valid_time"] == t1 and history[1]["valid_time"] == t2
    assert projection.current("water:reservoir-1", "turbidity")["value"]["ntu"] == 18.2
