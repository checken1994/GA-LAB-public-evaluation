import pytest

from scp.forecast.scoring import ForecastContractError, score_binary_forecasts


def test_forecast_scoring_perfect_prediction():
    rows = [
        {"probability": 1.0, "actual": 1},
        {"probability": 0.0, "actual": 0},
    ]
    res = score_binary_forecasts(rows)
    assert res["brier_score"] == 0.0
    assert res["accuracy"] == 1.0
    assert res["n"] == 2

def test_forecast_scoring_filters_unresolved():
    rows = [
        {"probability": 0.9, "actual": 1},
        {"probability": 0.8, "outcome_code": 9},  # Unresolved
        {"probability": 0.5, "status": "UNRESOLVED"},
    ]
    res = score_binary_forecasts(rows)
    assert res["n"] == 1
    assert res["excluded_unresolved"] == 2

def test_forecast_scoring_validates_probability_bounds():
    with pytest.raises(ForecastContractError):
        score_binary_forecasts([{"probability": 1.5, "actual": 1}])
