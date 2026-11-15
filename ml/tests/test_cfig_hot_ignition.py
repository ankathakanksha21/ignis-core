"""The CFI-G hot-ignition model, through the public api."""

import pytest

from ignis_ml import api
from ignis_ml.contract import PredictRequest
from ignis_ml.features.cfig import FILE_NAME, load_cfig
from ignis_ml.models import cfig_hot_ignition
from ignis_ml.raw import read_raw_table

IN_RANGE = {
    "fuel": "butane",
    "o2_mole_fraction": 0.39,
    "pressure_kpa": 101.3,
    "fuel_mole_fraction": 0.3,
    "fuel_flow_mg_s": 1.0,
}


def ask(n_nearest=5, **changes):
    request = PredictRequest(model_id="cfig_hot_ignition", inputs={**IN_RANGE, **changes}, n_nearest=n_nearest)
    return api.predict(request)


@pytest.fixture(scope="module")
def card():
    return next(card for card in api.model_cards() if card.model_id == "cfig_hot_ignition")


def test_features_keep_the_row_key_and_use_contract_units():
    cfig = load_cfig()
    raw = read_raw_table("PSI-159", FILE_NAME).set_index("row")
    first = cfig.frame.set_index("row").loc[2]
    assert (first["fuel"], first["bottle"], first["hot_ignition"]) == ("ethane", "ethane", "yes")
    assert first["pressure_kpa"] == pytest.approx(float(raw.at[2, "approx p (bar)"]) * 100)
    assert first["o2_mole_fraction"] == float(raw.at[2, " XO2 before test"])
    assert set(cfig.frame["fuel"]) == {"butane", "ethane", "propane"}
    assert set(cfig.frame["row"]) <= set(raw.index)


def test_runs_with_no_fuel_flowing_are_left_out_and_say_why():
    cfig = load_cfig()
    assert [item.row for item in cfig.excluded] == [69, 77]
    assert all("no fuel was flowing" in item.reason for item in cfig.excluded)
    assert len(cfig.frame) == 177


def test_the_card_is_available_and_says_what_it_was_trained_on(card):
    assert card.status == "available" and card.classes == ["yes", "no"]
    table = card.trained_on[0]
    assert (table.psi_id, table.file_name, table.n_rows) == ("PSI-159", FILE_NAME, 177)
    assert table.doi
    for row in (69, 77):
        assert str(row) in card.notes


def test_the_card_ranges_are_the_training_rows_own(card):
    train = cfig_hot_ignition.fitted().train
    for feature in card.features:
        if feature.kind == "numeric":
            assert feature.tested_min == train[feature.name].min()
            assert feature.tested_max == train[feature.name].max()
        else:
            assert feature.categories == sorted(train[feature.name].unique())
    assert {feature.name for feature in card.features} == set(IN_RANGE)


def test_the_card_reports_both_groupings_against_the_majority_class(card):
    by_name = {metric.name: metric for metric in card.evaluation}
    assert all(metric.baseline_name == "majority class" for metric in card.evaluation)
    assert by_name["macro_f1"].value > by_name["macro_f1"].baseline_value
    assert by_name["accuracy"].value > by_name["accuracy"].baseline_value
    assert {"macro_f1, logistic regression", "macro_f1, gradient-boosted trees"} <= set(by_name)
    assert {"macro_f1, grouped by test day", "accuracy, grouped by test day"} <= set(by_name)
    assert "grouped by setup" in card.cv_scheme and "test day" in card.cv_scheme


def test_a_weak_result_is_stated_in_the_card_not_hidden(card):
    by_name = {metric.name: metric for metric in card.evaluation}
    day = by_name["accuracy, grouped by test day"]
    if day.value <= day.baseline_value:
        assert "Weak point" in card.notes


def test_an_in_range_query_is_ok_with_probabilities_that_add_to_one():
    response = ask()
    assert response.status == "ok"
    prediction = response.prediction
    assert prediction.label in ("yes", "no") and prediction.value is None
    assert set(prediction.class_probabilities) == {"yes", "no"}
    assert sum(prediction.class_probabilities.values()) == pytest.approx(1.0, abs=1e-3)
    assert prediction.label == max(prediction.class_probabilities, key=prediction.class_probabilities.get)
    assert len(response.nearest_tests) == 5


def test_the_butane_ignition_limit_in_the_data_is_reproduced():
    # At 39 percent oxygen CFI-G never lit butane at a fuel fraction of 0.027 and always lit it at 0.031.
    assert ask(fuel_mole_fraction=0.027, fuel_flow_mg_s=0.5).prediction.label == "no"
    assert ask(fuel_mole_fraction=0.031, fuel_flow_mg_s=0.5).prediction.label == "yes"


def test_an_out_of_range_query_is_withheld_and_names_the_input():
    response = ask(o2_mole_fraction=0.6)
    assert response.status == "withheld" and response.prediction is None
    assert response.out_of_range[0].feature == "o2_mole_fraction"


def test_an_untested_fuel_is_withheld():
    response = ask(fuel="methane")
    assert response.status == "withheld"
    assert response.out_of_range[0].categories == ["butane", "ethane", "propane"]
    assert response.nearest_tests == []


def test_a_range_is_checked_for_the_chosen_fuel():
    # Only propane was run at 3 atm; butane and ethane stop at 2 atm.
    assert ask(fuel="propane", pressure_kpa=300.0).status == "ok"
    response = ask(pressure_kpa=300.0)
    assert response.status == "withheld"
    assert response.out_of_range[0].feature == "pressure_kpa"
    assert response.out_of_range[0].tested_max == pytest.approx(202.66)


@pytest.mark.parametrize(
    "inputs",
    [{"fuel": "butane"}, {**IN_RANGE, "fuel_flow_mg_s": "1.0"}, {**IN_RANGE, "gravity_g": 0.0}],
    ids=["missing inputs", "number sent as text", "unknown input"],
)
def test_a_malformed_request_is_invalid_input(inputs):
    response = api.predict(PredictRequest(model_id="cfig_hot_ignition", inputs=inputs))
    assert response.status == "invalid_input" and response.prediction is None


def test_every_cited_row_exists_and_its_cells_are_verbatim():
    raw = read_raw_table("PSI-159", FILE_NAME).set_index("row")
    response = ask(n_nearest=25)
    assert len(response.nearest_tests) == 25
    for test in response.nearest_tests:
        assert (test.psi_id, test.file_name) == ("PSI-159", FILE_NAME)
        assert "butane" in test.values["Fuel"]
        for column, cell in test.values.items():
            assert raw.at[test.row, column] == cell


def test_training_is_deterministic():
    first = ask().prediction
    cfig_hot_ignition.fitted.cache_clear()
    assert ask().prediction == first
