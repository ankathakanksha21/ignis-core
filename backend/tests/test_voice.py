import json
import re

import pytest
from fastapi.testclient import TestClient

from app import voice
from app.main import app

client = TestClient(app)
NUMBER = re.compile(r"\d+(?:\.\d+)?")


@pytest.fixture(autouse=True)
def no_keys(monkeypatch):
    """No language model and no ElevenLabs, whatever .env holds on this machine."""
    def refuse(*args, **kwargs):
        raise RuntimeError("no key in tests")

    monkeypatch.setattr(voice.llm, "chat", refuse)
    monkeypatch.setattr(voice, "_env", lambda name: "")
    voice._brief.cache_clear()
    yield
    voice._brief.cache_clear()


def explain(kind, level="student", speak=True, **params):
    response = client.post("/api/voice/explain", json={"kind": kind, "params": params, "level": level, "speak": speak})
    assert response.status_code == 200, response.text
    return response.json()


def test_without_keys_code_writes_the_script_and_the_browser_voice_is_used():
    body = explain("investigation", psi_id="PSI-69")
    assert body["written_by"] == "code" and body["voice"] is None and "browser" in body["voice_note"]
    assert "FLEX" in body["title"] and len(body["highlights"]) == 3
    # Every number the fallback script says is one of the facts.
    assert set(NUMBER.findall(body["script"])) <= set(NUMBER.findall(" ".join(body["facts"])))


def test_every_page_kind_builds_facts_from_the_data():
    compare = explain("compare", ids="PSI-69,PSI-25", mission="moon")
    assert any(line.startswith("FLEX: ") and "12 to 34 %" in line for line in compare["facts"])
    assert any(line.startswith("BASS-II: ") for line in compare["facts"])

    rank = explain("rank", mission="moon", flow_cm_s=20, fuel_class="solid")
    assert "20 cm/s flow" in rank["facts"][0] and "Rank 1: SAFFIRE-I" in " ".join(rank["facts"])
    assert any("partial gravity" in line for line in rank["facts"])

    gap = explain("gaps", habitat="moon")
    assert any("Suggested experiment 1: solid fuels at 30 to 35% oxygen" in line for line in gap["facts"])

    similar = explain("similar", o2_mole_fraction=0.3, pressure_kpa=70.3)
    assert any(line.startswith("Closest test 1: FLEX row") for line in similar["facts"])


def test_predictions_and_simulations_are_never_called_measurements():
    inputs = {"fuel": "heptane", "o2_mole_fraction": 0.21, "co2_mole_fraction": 0, "he_mole_fraction": 0,
              "pressure_kpa": 101.3, "droplet_diameter_mm": 3}  # fmt: skip
    predicted = explain("prediction", model_id="flex_burning_rate", inputs=inputs)
    assert any("model prediction, not a measurement" in line for line in predicted["facts"])
    withheld = explain("prediction", model_id="flex_burning_rate", inputs={**inputs, "o2_mole_fraction": 0.6})
    assert any("gave no answer" in line for line in withheld["facts"])
    assert any(line.startswith("Outside the tested range: o2_mole_fraction") for line in withheld["facts"])

    request = {"scenario": "droplet", "fuel": "heptane", "gravity_g": 0, "o2_mole_fraction": 0.21, "pressure_kpa": 101.3,
               "droplet_diameter_mm": 3}  # fmt: skip
    lab = explain("lab", request=request)
    assert any("simulated, not measured" in line for line in lab["facts"])
    refused = explain("lab", request={**request, "gravity_g": 0.16})
    assert any("did not simulate" in line for line in refused["facts"])


def test_a_model_script_is_used_only_when_its_numbers_are_in_the_facts(monkeypatch):
    facts = ["Rows in the test table: 274 test", "Oxygen in the atmosphere: 12 to 34 %"]
    good = {"script": "FLEX ran 274 tests, with oxygen from 12 to 34 percent. Ask me anything.", "highlights": ["274 tests"]}
    assert voice.check_script(good, facts)[0]["highlights"] == ["274 tests"]
    assert "275" in voice.check_script({**good, "script": "FLEX ran 275 tests."}, facts)[1]
    assert "safe" in voice.check_script({**good, "script": "FLEX shows 34 percent oxygen is safe."}, facts)[1]
    assert voice.check_script("not json", facts)[0] is None

    replies = iter([json.dumps({**good, "script": "FLEX ran 999 tests."}), json.dumps(good)])
    monkeypatch.setattr(voice.llm, "chat", lambda messages, **kwargs: next(replies))
    monkeypatch.setitem(voice.KINDS, "investigation", lambda params: ("The FLEX page", facts))
    body = explain("investigation", psi_id="PSI-69")
    assert body["written_by"] == "model" and "274" in body["script"]  # the retry, after the invented number was refused


def test_bad_requests_are_refused():
    assert client.post("/api/voice/explain", json={"kind": "investigation", "params": {"psi_id": "PSI-0"}}).status_code == 404
    assert client.post("/api/voice/explain", json={"kind": "weather", "params": {}}).status_code == 422
    assert client.post("/api/voice/explain", json={"kind": "similar", "params": {}}).status_code == 422


def test_a_typed_answer_is_checked_before_it_is_read_aloud(monkeypatch):
    body = {"kind": "investigation", "params": {"psi_id": "PSI-69"}, "question": "How many tests, and is 50% oxygen covered?"}
    assert client.post("/api/voice/answer", json=body).status_code == 503  # no language model in tests

    replies = iter(["FLEX ran 999 tests.", "FLEX ran 274 tests. 50% oxygen is outside what it tested."])
    seen = []
    monkeypatch.setattr(voice.llm, "chat", lambda messages, **kwargs: (seen.append(messages), next(replies))[1])
    found = client.post("/api/voice/answer", json={**body, "history": [{"role": "user", "text": "Stop there."}]}).json()
    # 999 was refused. 274 is a fact, and 50 is allowed because the listener said it.
    assert found == {"text": "FLEX ran 274 tests. 50% oxygen is outside what it tested.", "checked": True}
    assert "Number of tests: 274" in seen[0][0]["content"] and body["question"] in [turn["content"] for turn in seen[0]]

    monkeypatch.setattr(voice.llm, "chat", lambda messages, **kwargs: "It is 31337.")
    assert client.post("/api/voice/answer", json=body).json()["text"] == voice.NOT_COVERED


def test_the_pattern_explanation_measures_the_trend_it_describes():
    body = explain("pattern", x="o2_percent", y="burning_rate", group="fuel")
    facts = " ".join(body["facts"])
    assert "Tests that record both values: 258 of 274" in facts
    assert "as oxygen rises, burning rate tends to rise" in facts and "rank correlation" in facts
    assert "Points coloured by fuel, Heptane" in facts and "not proof of cause" in facts
    assert voice.rank_correlation([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert voice.rank_correlation([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert voice.rank_correlation([1, 1, 1], [1, 2, 3]) is None


def test_the_other_pages_have_facts_background_and_questions_to_ask():
    quality = explain("quality")
    assert quality["facts"][0].startswith("Table cells that look wrong: 70")
    assert "NASA says" in explain("earth")["title"] and any("Theme, " in line for line in explain("earth")["facts"])
    overview = explain("overview")
    assert overview["facts"][0].endswith(": 24") and any("SPICE ran 469 tests" in line for line in overview["facts"])
    assert len(overview["questions"]) == 4 and overview["questions"][-1] == "How do I read this page?"
    # Background is general science, so it is labelled and carries no measured value.
    background = [line for line in overview["facts"] if line.startswith("Background, general science")]
    assert background and not any(NUMBER.search(line.replace("-1 to 1", "")) for line in background)


def test_the_audience_changes_the_wording_and_never_the_facts(monkeypatch):
    seen = []
    monkeypatch.setattr(voice.llm, "chat", lambda messages, **kwargs: (seen.append(messages[0]["content"]), "{}")[1])
    student, researcher = explain("gaps", habitat="moon"), explain("gaps", habitat="moon", level="researcher")
    assert student["facts"] == researcher["facts"]
    assert any("student" in prompt for prompt in seen) and any("researcher" in prompt for prompt in seen)
    assert explain("gaps", habitat="moon", speak=False)["voice"] is None


def test_dashes_are_taken_out_of_what_is_read_aloud():
    facts = ["Oxygen in the atmosphere: 12 to 34 %"]
    answer = {"script": "Oxygen ran 12–34 percent overall—a wide range.", "highlights": ["12 – 34 percent"]}
    assert voice.check_script(answer, facts)[0] == {"script": "Oxygen ran 12 to 34 percent overall, a wide range.", "highlights": ["12 to 34 percent"]}


def test_the_guide_can_explain_how_the_page_is_read():
    moon = " ".join(line for line in explain("gaps", habitat="moon")["facts"] if line.startswith("How to read this page"))
    assert "An orange border is a separate mark and does not mean untested" in moon
    assert "30% oxygen or more, and 70.3 kPa or less" in moon and "thin orange border" in moon
    assert "its pressure is too high or its oxygen too low for this habitat" in moon
    station = " ".join(explain("gaps", habitat="station")["facts"])
    assert "single point and not a range" in station and "or more, and" not in station
    for kind, params in [("rank", {"mission": "moon"}), ("compare", {"ids": "PSI-69,PSI-25"}), ("quality", {})]:
        facts = explain(kind, **params)["facts"]
        assert any(line.startswith("How to read this page") for line in facts) and any(line.startswith("About this app") for line in facts)
    assert "How to read this page" in voice.AGENT_PROMPT and "About this app" in voice.AGENT_PROMPT
