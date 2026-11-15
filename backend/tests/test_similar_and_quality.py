from fastapi.testclient import TestClient

from app import quality
from app.main import app

client = TestClient(app)


def similar(**body):
    response = client.post("/api/investigations/similar", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_nearest_test_to_the_moon_base_atmosphere_is_a_flex_droplet():
    body = similar(o2_mole_fraction=0.30, pressure_kpa=70.3)
    first = body["results"][0]
    assert (first["name"], first["row"], first["not_stated"]) == ("FLEX", 42, [])
    assert first["values"]["o2_mole_fraction"] == {"min": 0.3, "max": 0.3} and first["distance"] < 0.05
    assert not body["nothing_close"]
    distances = [r["distance"] for r in body["results"] if not r["not_stated"]]
    assert distances == sorted(distances)


def test_solids_have_nothing_close_to_the_moon_base_atmosphere():
    body = similar(o2_mole_fraction=0.30, pressure_kpa=70.3, fuel_class="solid")
    first = body["results"][0]
    assert first["not_stated"] == ["pressure_kpa"]  # compared on oxygen alone
    assert first["values"]["o2_mole_fraction"]["max"] <= 0.222
    assert body["nothing_close"]


def test_flow_is_compared_when_asked_for():
    first = similar(flow_cm_s=20, fuel_class="solid")["results"][0]
    assert first["name"].startswith("SAFFIRE") and first["distance"] == 0
    assert client.post("/api/investigations/similar", json={}).status_code == 422


def test_quality_report_shows_each_flagged_cell_as_published():
    body = client.get("/api/atmospheres/quality").json()
    assert len(body["flags"]) == 70 and sum(check["count"] for check in body["checks"]) == 70
    assert {check["check"] for check in body["checks"]} == set(quality.CHECKS)  # every check is explained
    flex = next(f for f in body["flags"] if (f["psi_id"], f["row"], f["check"]) == ("PSI-69", 115, "non_physical"))
    assert flex["cell"] == "0" and flex["column"] == "Ambient pressure; mmHg"
    bre = next(f for f in body["flags"] if (f["psi_id"], f["row"]) == ("PSI-20", 6))
    assert bre["cell"] == "3400%"
    assert len(body["not_tests"]) == 28
    bass2 = next(i for i in body["investigations"] if i["psi_id"] == "PSI-25")
    assert (bass2["rows"], bass2["flags"]) == (129, 18)
