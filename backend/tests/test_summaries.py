import json

from app import store, summaries

SOURCE = "INVESTIGATION: Test (PSI-0)\n\nNASA RECORD\napproach: Two video cameras recorded 30 flames.\n\nFACTS\n- Oxygen: 21 %"
RECORD = "approach: Two video cameras recorded 30 flames."


def answer(**changes):
    return {"one_line": "It burned 30 flames.", "summary": "Flames burned at 21 % oxygen.", "measurements": [], **changes}


def test_a_number_that_is_not_in_the_material_is_rejected():
    assert summaries.validate(answer(), SOURCE, RECORD)[0] is not None
    rejected, why = summaries.validate(answer(summary="Flames burned at 40 % oxygen."), SOURCE, RECORD)
    assert rejected is None and "40" in why


def test_a_measurement_is_kept_only_when_its_quote_is_in_the_record():
    claimed = [
        {"name": "video cameras", "quote": "Two video cameras recorded"},
        {"name": "radiometer", "quote": "a radiometer measured heat flux"},  # not in the record
        {"name": "oxygen", "quote": "Oxygen: 21 %"},  # from the facts list, not the record
    ]
    kept, _ = summaries.validate(answer(measurements=claimed), SOURCE, RECORD)
    assert [item["name"] for item in kept["measurements"]] == ["video cameras"]


def test_burning_cannot_be_claimed_when_the_record_has_none():
    source = "NASA RECORD\napproach: Smoke from pyrolyzing 2 samples was measured."
    burned, why = summaries.validate(answer(one_line="It burned 2 samples.", summary="Smoke was measured."), source, source)
    assert burned is None and "burned" in why
    assert summaries.validate(answer(one_line="It heated 2 samples.", summary="Smoke was measured."), source, source)[0]


def test_malformed_or_overlong_answers_are_rejected():
    assert summaries.validate("not json", SOURCE, RECORD)[0] is None
    assert summaries.validate(answer(summary="word " * 120), SOURCE, RECORD)[0] is None
    assert summaries.validate(answer(one_line=""), SOURCE, RECORD)[0] is None


def test_a_summary_is_hidden_once_its_material_changes(monkeypatch):
    stored = {"one_line": "x", "summary": "y", "measurements": [], "source_hash": "written-from-older-data"}
    monkeypatch.setattr(summaries, "_file", lambda: {"summaries": {"PSI-69": stored}})
    assert summaries.get("PSI-69") is None
    stored["source_hash"] = summaries.source_hash(summaries.material("PSI-69"))
    assert summaries.get("PSI-69")["one_line"] == "x"


def test_the_model_sees_only_its_own_investigation():
    text = summaries.material("PSI-25")
    assert "BASS-II" in text and "13.6 to 22.2 %" in text and "Pressure: not stated" in text
    assert "FLEX" not in text and "Saffire" not in text


def test_every_stored_summary_still_passes_the_checks():
    stored = json.loads(summaries.PATH.read_text(encoding="utf-8"))["summaries"]
    for psi_id, summary in stored.items():
        if summaries.get(psi_id) is None:
            continue  # stale: not shown, to be regenerated
        record = summaries.record_text(store.investigations()[psi_id])
        checked, why = summaries.validate(summary, summaries.material(psi_id), record)
        assert checked is not None, f"{psi_id}: {why}"
        assert len(checked["measurements"]) == len(summary["measurements"]), psi_id
