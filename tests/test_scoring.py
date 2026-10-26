
from engine.scoring import score_param, score_vitals, NEWS2Result


def test_normal_vitals_have_zero_scores():
    assert score_param("rr", 16) == 0
    assert score_param("spo2", 98) == 0
    assert score_param("on_oxygen", False) == 0
    assert score_param("sbp", 120) == 0
    assert score_param("hr", 75) == 0
    assert score_param("avpu", "A") == 0
    assert score_param("temp", 37.0) == 0


def test_high_risk_values_receive_three_points():
    assert score_param("rr", 8) == 3
    assert score_param("spo2", 91) == 3
    assert score_param("on_oxygen", True) == 2
    assert score_param("sbp", 90) == 3
    assert score_param("hr", 40) == 3
    assert score_param("avpu", "U") == 3
    assert score_param("temp", 35.0) == 3


def test_score_vitals_tracks_missing_values():
    result = score_vitals({
        "rr": 16,
        "spo2": 98,
    })

    assert isinstance(result, NEWS2Result)
    assert result.total == 0
    assert result.parts == {"rr": 0, "spo2": 0}
    assert "hr" in result.missing
    assert "sbp" in result.missing
    assert "temp" in result.missing


def test_score_vitals_calculates_total_and_band():
    result = score_vitals({
        "rr": 8,
        "spo2": 98,
        "on_oxygen": False,
        "sbp": 120,
        "hr": 75,
        "avpu": "A",
        "temp": 37.0,
    })

    assert result.total == 3
    assert result.any_three is True
    assert result.band == "low-medium"
    assert result.missing == []
