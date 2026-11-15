from fastapi.testclient import TestClient

from app import earth, store
from app.main import app

client = TestClient(app)


def panel():
    response = client.get("/api/investigations/earth")
    assert response.status_code == 200, response.text
    return response.json()


def test_every_quote_is_word_for_word_in_the_record_it_cites():
    records = store.investigations()
    quotes = [quote for theme in panel()["themes"] for quote in theme["quotes"]]
    assert len(quotes) == 19
    for quote in quotes:
        for who in quote["investigations"]:
            assert quote["text"] in " ".join(records[who["psi_id"]]["research_impacts"].split())


def test_a_changed_record_fails_instead_of_showing_a_stale_quote(monkeypatch):
    changed = {**store.investigations(), "PSI-22": {**store.investigations()["PSI-22"], "research_impacts": "Edited."}}
    monkeypatch.setattr(store, "investigations", lambda: changed)
    try:
        earth.panel()
    except ValueError as error:
        assert "PSI-22" in str(error)
    else:
        raise AssertionError("a quote missing from its record was served")


def test_each_investigation_is_either_quoted_or_listed_as_not_quoted():
    body = panel()
    quoted = {who["psi_id"] for theme in body["themes"] for quote in theme["quotes"] for who in quote["investigations"]}
    left = {who["psi_id"] for who in body["not_quoted"]}
    in_scope = {psi_id for psi_id, entry in store.investigations().items() if entry["in_scope"]}
    assert not quoted & left and quoted | left == in_scope
    assert left == {"PSI-20", "PSI-26", "PSI-107", "PSI-115"}


def test_spinoff_entries_cover_the_products_the_brief_names_and_link_to_nasa():
    spinoffs = panel()["spinoffs"]
    assert [entry["product"] for entry in spinoffs] == [
        "Fine-water-mist extinguishers", "Smoke detectors", "Firefighter clothing", "Firefighter air tanks",
    ]  # fmt: skip
    for source in (source for entry in spinoffs for source in entry["sources"]):
        assert source["url"].startswith(("https://spinoff.nasa.gov/", "https://ntrs.nasa.gov/")) and source["quotes"]
