"""The FLEX self-extinction model, through the public api."""

import pytest

from ignis_ml import api
from ignis_ml.contract import PredictRequest
from ignis_ml.models import flex_extinction
from ignis_ml.raw import read_raw_table

IN_RANGE = {
    "fuel": "methanol",
    "o2_mole_fraction": 0.21,
    "co2_mole_fraction": 0.0,
    "he_mole_fraction": 0.0,
    "pressure_kpa": 101.3,
    "droplet_diameter_mm": 3.0,
}


def ask(n_nearest=5, **changes):
    request = PredictRequest(model_id="flex_extinction", inputs={**IN_RANGE, **changes}, n_nearest=n_nearest)
    return api.predict(request)


@pytest.fixture(scope="module")
def card():
    return next(card for card in api.model_cards() if card.model_id == "flex_extinction")


def test_the_card_is_available_and_says_what_it_was_trained_on(card):
    assert card.status == "available" and card.classes == ["yes", "no"]
    table = card.trained_on[0]
    assert (table.psi_id, table.file_name, table.n_rows) == ("PSI-69", "PSI-69_Experimental table_FLEX.csv", 259)
    fit = flex_extinction.fitted()
    assert len(fit.train) + len(fit.left_out) == 274
    for item in fit.left_out:
        assert str(item.row) in card.notes


def test_yes_is_the_tables_extinction_ending_and_nothing_else():
    train = flex_extinction.fitted().train
    assert set(train.loc[train["self_extinguished"] == "yes", "test_end"]) == {"Extinction"}
    assert set(train.loc[train["self_extinguished"] == "no", "test_end"]) == {"Completion", "Disruption"}


def test_the_card_beats_the_majority_class_and_reports_both_candidates(card):
    by_name = {metric.name: metric for metric in card.evaluation}
    assert all(metric.baseline_name == "majority class" for metric in card.evaluation)
    for name in ("macro_f1", "balanced_accuracy", "accuracy", "accuracy, grouped by test date"):
        assert by_name[name].value > by_name[name].baseline_value
    assert {"macro_f1, logistic regression", "macro_f1, gradient-boosted trees"} <= set(by_name)
    assert "grouped by test condition" in card.cv_scheme


def test_the_card_states_what_flex_measured_at_low_pressure(card):
    train = flex_extinction.fitted().train
    low = train[train["pressure_kpa"] < 81]
    rich = low[low["o2_mole_fraction"] >= 0.30]
    assert len(rich) == 16 and (rich["self_extinguished"] == "yes").sum() == 0
    assert "0 of 16 at 30% oxygen or more" in card.notes
    assert "46 of 51" in card.notes
    assert "not a safe verdict" in card.notes


def test_an_in_range_query_is_ok_with_probabilities_and_the_real_endings():
    response = ask()
    assert response.status == "ok"
    prediction = response.prediction
    assert prediction.label in ("yes", "no") and prediction.value is None
    assert sum(prediction.class_probabilities.values()) == pytest.approx(1.0, abs=1e-3)
    assert prediction.label == max(prediction.class_probabilities, key=prediction.class_probabilities.get)
    assert "closest real tests ended" in response.message
    assert len(response.nearest_tests) == 5


def test_low_oxygen_extinguishes_and_exploration_air_does_not():
    assert ask(o2_mole_fraction=0.15).prediction.label == "yes"
    for fuel in ("methanol", "heptane"):
        assert ask(fuel=fuel, o2_mole_fraction=0.30, pressure_kpa=70.5).prediction.label == "no"


def test_outside_the_tested_range_is_withheld():
    response = ask(o2_mole_fraction=0.5)
    assert response.status == "withheld" and response.prediction is None
    assert response.out_of_range[0].feature == "o2_mole_fraction"
    untested = ask(fuel="ethanol")
    assert untested.status == "withheld" and untested.nearest_tests == []
    both = ask(co2_mole_fraction=0.1, he_mole_fraction=0.1)
    assert {violation.feature for violation in both.out_of_range} == {"co2_mole_fraction", "he_mole_fraction"}


@pytest.mark.parametrize(
    "inputs",
    [{"fuel": "methanol"}, {**IN_RANGE, "pressure_kpa": "101"}, {**IN_RANGE, "o2_mole_fraction": 0.34, "co2_mole_fraction": 0.7}],
    ids=["missing inputs", "number sent as text", "gases add up to more than 1"],
)
def test_a_malformed_request_is_invalid_input(inputs):
    response = api.predict(PredictRequest(model_id="flex_extinction", inputs=inputs))
    assert response.status == "invalid_input" and response.prediction is None


def test_every_cited_row_exists_and_its_cells_are_verbatim():
    raw = read_raw_table("PSI-69").set_index("row")
    response = ask(n_nearest=25, fuel="heptane")
    assert len(response.nearest_tests) == 25
    for test in response.nearest_tests:
        assert test.values["Fuel"] == "Heptane"
        for column, cell in test.values.items():
            assert raw.at[test.row, column] == cell
    assert ask(n_nearest=0).nearest_tests == []


def test_training_is_deterministic():
    first = ask().prediction
    flex_extinction.fitted.cache_clear()
    assert ask().prediction == first
