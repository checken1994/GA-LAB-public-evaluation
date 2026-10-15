from datetime import datetime, timedelta, timezone

import pytest

from scp.knowledge.knowledge_control_db import KnowledgeControlDB
from scp.knowledge.revalidation_authority import (
    RevalidationAuthority,
    RevalidationPolicy,
    VolatilityClass,
)


@pytest.fixture
def db(tmp_path):
    return KnowledgeControlDB(tmp_path / "test_knowledge.sqlite")

@pytest.fixture
def auth(db):
    return RevalidationAuthority(db)

def test_assess_staleness(auth):
    policy = RevalidationPolicy(
        volatility_class=VolatilityClass.HIGH,
        review_after_seconds=3600,
        max_staleness_seconds=7200
    )
    
    now = datetime.now(timezone.utc)
    
    # Fresh (1 hour old)
    fresh_dt = (now - timedelta(minutes=30)).isoformat()
    assert auth.assess_staleness(fresh_dt, policy) == False
    
    # Stale (2 hours old)
    stale_dt = (now - timedelta(hours=2)).isoformat()
    assert auth.assess_staleness(stale_dt, policy) == True

def test_schedule_revalidation(auth):
    policy = RevalidationPolicy(volatility_class="MEDIUM", review_after_seconds=86400, max_staleness_seconds=172800)
    job_id = auth.schedule_revalidation("k1", policy, "2026-01-01T00:00:00Z")
    assert job_id.startswith("revj_")
