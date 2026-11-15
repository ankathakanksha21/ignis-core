import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def rank(**body):
    response = client.post("/api/investigations/rank", json={"mission": "moon", **body})
    assert response.status_code == 200, response.text
    return {result["psi_id"]: result for result in response.json()["results"]}


def factor(result, name):
    return next(f for f in result["factors"] if f["id"] == name)


def test_score_is_the_weighted_average_of_the_factors():
    for result in rank().values():
        total = sum(f["score"] * f["weight"] for f in result["factors"]) / sum(f["weight"] for f in result["factors"])
        assert result["score"] == pytest.approx(total, abs=1e-3)
        assert all(0 <= f["score"] <= 1 for f in result["factors"])


def test_oxygen_match_uses_the_nearest_tested_value():
    moon = rank()
    assert factor(moon["PSI-69"], "oxygen")["score"] == 1.0  # FLEX tested 30% oxygen
    # BASS-II stops at 22.2%, which is 7.8 points short of 30%: 1 - 0.078 / 0.10
    bass2 = factor(moon["PSI-25"], "oxygen")
    assert bass2["score"] == pytest.approx(0.22, abs=1e-3)
    assert bass2["source"]["raw"] == "22.2" and bass2["source"]["row"] >= 2


def test_pressure_match_finds_the_flex_tests_near_10_psi():
    pressure = factor(rank()["PSI-69"], "pressure")
    assert pressure["score"] > 0.99 and pressure["source"]["raw"] == "527.6"  # mmHg, which is 70.3 kPa


def test_missing_data_scores_zero_and_is_marked_unknown():
    bass = rank()["PSI-26"]  # BASS states no conditions
    for name in ("oxygen", "pressure"):
        assert factor(bass, name)["unknown"] and factor(bass, name)["score"] == 0
    ground = rank()["PSI-60"]
    assert factor(ground, "gravity")["unknown"] and factor(ground, "fuel")["unknown"]


def test_burner_oxygen_does_not_count_as_atmosphere_oxygen():
    # CFI-G fed up to 85% oxygen through the burner, but its atmosphere tops out at 40%.
    oxygen = factor(rank(o2_mole_fraction=0.85)["PSI-159"], "oxygen")
    assert oxygen["score"] == 0 and "40%" in oxygen["detail"]


def test_partial_gravity_is_never_a_full_match():
    moon = rank()
    assert factor(moon["PSI-69"], "gravity")["score"] == 0.5
    assert "Untested at 0.16 g" in factor(moon["PSI-69"], "gravity")["detail"]
    station = client.post("/api/investigations/rank", json={"mission": "station"}).json()["results"]
    assert factor(next(r for r in station if r["psi_id"] == "PSI-69"), "gravity")["score"] == 1.0


def test_weights_change_the_order():
    by_fuel = rank(weights={"oxygen": 0, "pressure": 0, "fuel": 5, "gravity": 0, "pillar": 0})
    assert by_fuel["PSI-25"]["score"] == 1.0 and by_fuel["PSI-69"]["score"] == 0.5
    assert factor(rank()["PSI-102"], "pillar")["score"] == 1.0 and factor(rank()["PSI-10"], "pillar")["score"] == 0.5
    assert all(r["score"] == 0 for r in rank(weights=dict.fromkeys(("oxygen", "pressure", "fuel", "gravity", "pillar"), 0)).values())


def test_bad_requests_are_refused():
    assert client.post("/api/investigations/rank", json={"mission": "venus"}).status_code == 404
    assert client.post("/api/investigations/rank", json={"mission": "moon", "weights": {"oxygen": 9}}).status_code == 422
    assert client.get("/api/investigations/missions").json()["missions"][2]["id"] == "moon"


def test_flow_is_scored_only_when_a_flow_is_given():
    assert all(len(result["factors"]) == 5 for result in rank().values())
    with_flow = rank(flow_cm_s=20)
    saffire = factor(with_flow["PSI-98"], "flow")  # SAFFIRE-I ran at 20 cm/s
    assert saffire["score"] == 1.0 and saffire["source"]["row"] >= 2
    flex = factor(with_flow["PSI-69"], "flow")  # FLEX records no flow
    assert flex["unknown"] and flex["score"] == 0
    assert with_flow["PSI-69"]["score"] < rank()["PSI-69"]["score"]
    response = client.post("/api/investigations/rank", json={"mission": "moon", "flow_cm_s": 20})
    assert "flow_cm_s" in response.json()["edited"]
