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
