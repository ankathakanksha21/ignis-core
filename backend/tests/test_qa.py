import json

from fastapi.testclient import TestClient

from app import llm, qa
from app.main import app

client = TestClient(app)
ITEMS = [
    {"text": "FLEX tested 274 droplets.", "source": "facts", "psi_id": "PSI-69", "name": "FLEX"},
    {"text": "BASS-II burned solids at 22.2% oxygen.", "source": "facts", "psi_id": "PSI-25", "name": "BASS-II"},
]


def test_retrieval_puts_the_right_evidence_first():
    assert "no combustion test at partial gravity" in qa.retrieve("What do we know about combustion at Moon gravity?")[0]["text"]
    rows = qa.retrieve("Has any solid fuel been tested near 30% oxygen?")[0]["text"]
    assert rows.startswith("The real solid fuel test rows closest to 30% oxygen") and "BASS-II row 2" in rows
    assert "highest, in FLEX" in qa.retrieve("What is the highest oxygen level tested with droplets?")[0]["text"]
    assert any(item["name"] == "SAME" and "approach" in item["source"] for item in qa.retrieve("How did SAME measure smoke?"))


def test_a_sentence_needs_a_citation():
    reply = {"sentences": [{"text": "FLEX tested droplets.", "cites": [1]}, {"text": "Flames are hot.", "cites": []},
                           {"text": "Cited to nothing real.", "cites": [9]}]}  # fmt: skip
    kept, _ = qa.check(reply, ITEMS)
    assert [s["text"] for s in kept] == ["FLEX tested droplets."]


def test_a_number_must_be_in_the_item_the_sentence_cites():
    reply = {"sentences": [
        {"text": "FLEX tested 274 droplets.", "cites": [1]},
        {"text": "FLEX tested 300 droplets.", "cites": [1]},  # invented
        {"text": "FLEX ran at 22.2% oxygen.", "cites": [1]},  # the number belongs to item 2, not the one cited
    ]}  # fmt: skip
    kept, _ = qa.check(reply, ITEMS)
    assert [s["text"] for s in kept] == ["FLEX tested 274 droplets."]


def test_ask_keeps_checked_sentences_and_counts_the_rest(monkeypatch):
    fake = {"sentences": [{"text": "Every test ran in microgravity.", "cites": [1]}, {"text": "There were 999 tests.", "cites": [1]}],
            "not_covered": None}  # fmt: skip
    monkeypatch.setattr(llm, "chat", lambda messages, **_: "Here you go: " + json.dumps(fake))
    monkeypatch.setattr(llm, "settings", lambda: {"LLM_MODEL": "test-model"})
    body = client.post("/api/qa/ask", json={"question": "What do we know about combustion at Moon gravity?"}).json()
    assert [s["text"] for s in body["sentences"]] == ["Every test ran in microgravity."]
    assert body["dropped"] == 1 and body["evidence"][0]["n"] == 1 and body["model"] == "test-model"
    # The model saw only the numbered evidence and the question.
    assert all("source" in item for item in body["evidence"])


def test_an_unusable_reply_becomes_not_covered(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda messages, **_: "I think the answer is probably yes.")
    monkeypatch.setattr(llm, "settings", lambda: {"LLM_MODEL": "test-model"})
    body = client.post("/api/qa/ask", json={"question": "Is PMMA safe on the Moon?"}).json()
    assert body["sentences"] == [] and body["not_covered"]


def test_a_missing_key_is_reported_plainly(monkeypatch):
    def no_key(messages, **_):
        raise RuntimeError("Set LLM_API_KEY in .env (see .env.example)")

    monkeypatch.setattr(llm, "chat", no_key)
    response = client.post("/api/qa/ask", json={"question": "What did FLEX test?"})
    assert response.status_code == 503 and "LLM_API_KEY" in response.json()["detail"]
    assert client.post("/api/qa/ask", json={"question": "?"}).status_code == 422
