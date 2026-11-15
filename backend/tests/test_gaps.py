from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def gaps(habitat="moon"):
    response = client.get(f"/api/atmospheres/gaps?habitat={habitat}")
    assert response.status_code == 200
    return response.json()


def cells(body, fuel_class):
    found = next(k for k in body["classes"] if k["fuel_class"] == fuel_class)
    return {(cell["column"], cell["row"]): cell for cell in found["cells"]}


def test_solid_tests_state_no_pressure_so_they_sit_in_the_not_stated_row():
    body = gaps()
    not_stated = len(body["pressure_bins"]) - 1
    solid = cells(body, "solid")
    assert solid and all(row == not_stated for _, row in solid)
    assert max(column for column, _ in solid) == body["oxygen_bins"].index("20 to 25%")  # nothing above 22.2%


def test_droplets_were_tested_in_the_moon_base_cell():
    body = gaps()
    home = (body["habitat_cell"]["column"], body["habitat_cell"]["row"])
    assert (body["oxygen_bins"][home[0]], body["pressure_bins"][home[1]]) == ("30 to 35%", "50 to 75 kPa")
    assert cells(body, "droplet")[home]["from"] == {"FLEX": 17}
    nearest = next(k for k in body["classes"] if k["fuel_class"] == "droplet")["nearest"]
    assert (nearest["name"], nearest["o2"], nearest["pressure_kpa"]) == ("FLEX", 0.3, 71.2)


def test_the_first_suggestion_for_the_moon_is_a_solid_at_the_habitat():
    body = gaps()
    first = body["suggestions"][0]
    assert (first["fuel_class"], first["oxygen"], first["pressure"], first["status"]) == ("solid", "30 to 35%", "50 to 75 kPa", "untested")
    assert first["score"] == 1.0 and first["in_bounds"] and first["oxygen_never_tested"]
    for suggestion in body["suggestions"]:  # a suggested cell never holds a test
        assert (suggestion["column"], suggestion["row"]) not in cells(body, suggestion["fuel_class"])
    scores = [s["score"] for s in body["suggestions"] if s["status"] == "untested"]
    assert scores == sorted(scores, reverse=True)


def test_gravity_is_never_reported_as_covered_off_microgravity():
    assert "no combustion test at 0.16 g" in gaps("moon")["gravity_note"]
    assert "no combustion test at 0.38 g" in gaps("mars")["gravity_note"]
    assert "as this habitat is" in gaps("station")["gravity_note"]


def test_the_spacesuit_sits_beyond_every_test():
    body = gaps("suit")
    assert body["oxygen_bins"][body["habitat_cell"]["column"]] == "45% and above"
    assert all(cell["column"] < body["habitat_cell"]["column"] for k in body["classes"] for cell in k["cells"])
    assert client.get("/api/atmospheres/gaps?habitat=venus").status_code == 404
    assert len(client.get("/api/atmospheres/habitats").json()) == 7


def test_cells_say_which_rows_they_count_and_suggestions_show_their_working():
    body = gaps()
    home = (body["habitat_cell"]["column"], body["habitat_cell"]["row"])
    source = cells(body, "droplet")[home]["sources"][0]
    assert (source["psi_id"], source["name"]) == ("PSI-69", "FLEX") and len(source["rows"]) == 17
    for suggestion in body["suggestions"]:
        assert abs(suggestion["score"] - suggestion["closeness"] * suggestion["relevance"]) < 0.002
    assert body["candidates"] >= len(body["suggestions"]) and body["tolerance"] == {"oxygen_points": 10.0, "pressure_kpa": 35.0}


def test_a_link_can_open_the_rows_a_cell_counts():
    body = gaps()
    home = (body["habitat_cell"]["column"], body["habitat_cell"]["row"])
    source = cells(body, "droplet")[home]["sources"][0]
    rows = ",".join(str(number) for number in source["rows"][:3])
    found = client.get(f"/api/investigations/PSI-69/rows?rows={rows}&file={source['file_name']}").json()
    assert [line["row"] for line in found["rows"]] == source["rows"][:3] and not found["missing"]
    oxygen = found["columns"].index("O initial ambient composition; mole fraction")
    assert all(0.30 <= float(line["cells"][oxygen]) < 0.35 for line in found["rows"])  # cells are NASA's own text
    assert client.get("/api/investigations/PSI-69/rows?rows=abc").status_code == 422
    assert client.get("/api/investigations/PSI-69/rows?rows=2&file=nope.csv").status_code == 404
    assert client.get("/api/investigations/PSI-60/rows?rows=2").status_code == 404  # a study with no table
