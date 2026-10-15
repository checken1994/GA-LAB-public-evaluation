
from scp.core.budget_engine import difficulty_score, order_tiers, route_tier


def test_budget_reorders_verified_free_only():
    """Budget routing | budget chỉ reorder verified-free set, không tạo tier paid"""
    free_tier, paid_tier = "free", "paid"
    easy_text = "Fix typo in variable name"
    assert difficulty_score(easy_text) < 10.0
    assert route_tier(easy_text) == "free_first"
    assert order_tiers(easy_text) == [free_tier, paid_tier]
    
    hard_text = "Fix race condition in deadlock mutex handler with security bypass"
    assert difficulty_score(hard_text) >= 10.0
    assert route_tier(hard_text) == "paid_first"
    assert order_tiers(hard_text) == [paid_tier, free_tier]

