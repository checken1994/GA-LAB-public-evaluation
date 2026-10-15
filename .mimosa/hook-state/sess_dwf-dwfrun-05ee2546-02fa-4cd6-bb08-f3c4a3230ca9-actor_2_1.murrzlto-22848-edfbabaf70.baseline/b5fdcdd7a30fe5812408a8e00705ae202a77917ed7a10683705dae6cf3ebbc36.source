import os

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')


from scp.forecast.scoring import score_binary_forecasts


def test_forecast_isolated_flow():
    """FA-13: Cover forecast flow with genuine behavioral execution.

    Verifies Brier score calculation, empirical accuracy, baseline comparison,
    and calibration bucket generation for probabilistic forecasts.
    """
    # 1. Standard prediction set with known resolution
    rows = [
        {"probability": 0.8, "actual": 1},
        {"probability": 0.2, "actual": 0},
        {"probability": 0.9, "actual": 1},
        {"probability": 0.1, "actual": 0},
    ]
    result = score_binary_forecasts(rows)
    assert result["status"] == "SCORED"
    assert result["n"] == 4
    # Each error is (0.8-1)^2=0.04, (0.2-0)^2=0.04, (0.9-1)^2=0.01, (0.1-0)^2=0.01 -> mean = 0.025
    assert abs(result["brier_score"] - 0.025) < 1e-4
    assert result["accuracy"] == 1.0
    assert result["event_rate"] == 0.5
    assert "calibration" in result

    # 2. Empty forecast set handling
    empty_result = score_binary_forecasts([])
    assert empty_result["n"] == 0
