from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models_are_listed():
    cards = client.get("/api/models").json()
    assert {card["model_id"] for card in cards} >= {"flex_burning_rate", "flex_extinction"}


def test_predict_speaks_the_contract():
    response = client.post("/api/predict", json={"model_id": "flex_burning_rate", "inputs": {"o2_mole_fraction": 0.21}})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "withheld", "invalid_input", "not_implemented"}
    assert body["kind"] == "model_prediction"


def test_simulate_is_always_labelled_simulated():
    request = {"scenario": "droplet", "fuel": "heptane", "gravity_g": 0, "pressure_kpa": 101.3, "o2_mole_fraction": 0.21}
    response = client.post("/api/simulate", json=request)
    assert response.status_code == 200
    assert response.json()["kind"] == "simulated"


def test_every_combustion_investigation_has_a_card_and_a_pillar():
    body = client.get("/api/investigations").json()
    assert len(body["investigations"]) == 24 and len(body["left_out"]) == 2
    pillars = {pillar["id"] for pillar in body["pillars"]}
    assert all(card["pillar"] in pillars and card["pillar_why"] for card in body["investigations"])


def test_card_numbers_come_from_the_processed_files():
    cards = {card["psi_id"]: card for card in client.get("/api/investigations").json()["investigations"]}
    flex = cards["PSI-69"]
    assert flex["test_rows"] == 274 and flex["flag_count"] == 3
    assert flex["conditions"]["o2_mole_fraction"] == {"min": 0.12, "max": 0.34}
    assert cards["PSI-26"]["conditions"] == {}  # BASS states no conditions: shown as "not stated"
    assert cards["PSI-20"]["test_rows"] == 0 and cards["PSI-20"]["tests_counted"] == 194


def test_detail_shows_what_varied_and_where_values_came_from():
    detail = client.get("/api/investigations/PSI-69").json()
    columns = {column["name"]: column for column in detail["tables"][0]["columns"]}
    assert columns["Fuel"]["distinct"] == 2
    assert detail["tables"][0]["fields"]["pressure_kpa"]["source_column"] == "Ambient pressure; mmHg"
    assert {other["name"] for other in detail["shares_hardware"]["with"]} == {"CFI", "FLEX-2"}
    assert client.get("/api/investigations/PSI-108").status_code == 404


def test_chart_points_place_only_rows_whose_oxygen_and_pressure_pair_is_certain():
    series = {s["psi_id"]: s for s in client.get("/api/investigations/points?ids=PSI-69,PSI-25,PSI-68").json()["series"]}
    flex = series["PSI-69"]
    assert sum(len(point["rows"]) for point in flex["points"]) == 273  # 274 tests minus the one at 0 mmHg
    # FLEX burned droplets at 30% oxygen and about 10.3 psi, close to the Moon-base atmosphere
    assert any(point["o2"] == 0.3 and 70 < point["pressure_kpa"] < 73 for point in flex["points"])
    bass2 = series["PSI-25"]  # states oxygen but no pressure
    assert bass2["points"] == [] and sum(len(point["rows"]) for point in bass2["oxygen_only"]) == 129
    assert series["PSI-68"]["rows_not_placed"] == 8  # FLEX-2 lists oxygen levels and pressures separately
    cfig = client.get("/api/investigations/points?ids=PSI-159").json()["series"][0]
    assert cfig["rows_burner_fed"] == 154 and all(point["o2"] <= 0.4 for point in cfig["points"])
    assert client.get("/api/investigations/points?ids=PSI-108").status_code == 404
