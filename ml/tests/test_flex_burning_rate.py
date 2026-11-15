"""The FLEX burning-rate model, through the public api."""

import pytest

from ignis_ml import api
from ignis_ml.contract import PredictRequest
from ignis_ml.models import flex_burning_rate
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
    request = PredictRequest(model_id="flex_burning_rate", inputs={**IN_RANGE, **changes}, n_nearest=n_nearest)
    return api.predict(request)


@pytest.fixture(scope="module")
def card():
    return next(card for card in api.model_cards() if card.model_id == "flex_burning_rate")


def test_the_card_is_available_and_says_what_it_was_trained_on(card):
    assert card.status == "available"
    table = card.trained_on[0]
    assert (table.psi_id, table.file_name) == ("PSI-69", "PSI-69_Experimental table_FLEX.csv")
    assert table.doi == "10.60555/mbq8-0451"
    assert table.n_rows == 257


def test_the_card_ranges_are_the_training_rows_own(card):
    train = flex_burning_rate.fitted().train
    for feature in card.features:
        if feature.kind == "numeric":
            assert feature.tested_min == train[feature.name].min()
            assert feature.tested_max == train[feature.name].max()
        else:
            assert feature.categories == sorted(train[feature.name].unique())
    assert {feature.name for feature in card.features} == set(IN_RANGE)


def test_the_card_reports_evaluation_against_the_mean_and_both_candidates(card):
    by_name = {metric.name: metric for metric in card.evaluation}
    assert by_name["mae"].baseline_name == "mean"
    assert by_name["mae"].value < by_name["mae"].baseline_value
    assert {"mae, ridge regression", "mae, gradient-boosted trees"} <= set(by_name)
    assert by_name["mae"].value == min(
        by_name["mae, ridge regression"].value, by_name["mae, gradient-boosted trees"].value
    )
    assert "grouped by test condition" in card.cv_scheme


def test_the_card_lists_every_row_left_out(card):
    fit = flex_burning_rate.fitted()
    assert len(fit.train) + len(fit.left_out) == 274
    assert "row 115" in card.notes
    for item in fit.left_out:
        assert str(item.row) in card.notes


def test_an_in_range_query_is_ok():
    response = ask()
    assert response.status == "ok"
    prediction = response.prediction
    assert prediction.unit == "mm^2/s"
    assert 0 < prediction.low < prediction.value < prediction.high
    train = flex_burning_rate.fitted().train
    assert train["burning_rate_mm2_s"].min() <= prediction.value <= train["burning_rate_mm2_s"].max()
    assert len(response.nearest_tests) == 5


def test_every_training_condition_gets_a_positive_prediction():
    fit = flex_burning_rate.fitted()
    predicted = fit.model.predict(fit.train[flex_burning_rate.FEATURES])
    assert (predicted > 0).all()


def test_an_out_of_range_query_is_withheld_and_names_the_input():
    response = ask(o2_mole_fraction=0.5)
    assert response.status == "withheld" and response.prediction is None
    violation = response.out_of_range[0]
    assert violation.feature == "o2_mole_fraction"
    assert (violation.tested_min, violation.tested_max) == (0.12, 0.34)


def test_an_untested_fuel_is_withheld():
    response = ask(fuel="ethanol")
    assert response.status == "withheld"
    assert response.out_of_range[0].feature == "fuel"
    assert response.out_of_range[0].categories == ["heptane", "methanol"]
    assert response.nearest_tests == []


def test_co2_with_helium_is_withheld_because_flex_never_ran_both():
    response = ask(co2_mole_fraction=0.1, he_mole_fraction=0.1)
    assert response.status == "withheld"
    assert {violation.feature for violation in response.out_of_range} == {"co2_mole_fraction", "he_mole_fraction"}


def test_a_range_is_checked_for_the_chosen_fuel():
    assert ask(pressure_kpa=300.0).status == "ok"
    response = ask(fuel="heptane", pressure_kpa=300.0)
    assert response.status == "withheld"
    assert response.out_of_range[0].feature == "pressure_kpa"


def test_a_thinly_tested_combination_is_answered_with_a_caution():
    assert "Caution" not in ask().message
    assert "Caution" in ask(pressure_kpa=253.0).message


@pytest.mark.parametrize(
    "inputs",
    [
        {"fuel": "methanol"},
        {**IN_RANGE, "o2_mole_fraction": "0.21"},
        {**IN_RANGE, "gravity_g": 0.0},
        {**IN_RANGE, "o2_mole_fraction": 0.34, "co2_mole_fraction": 0.7},
    ],
    ids=["missing inputs", "number sent as text", "unknown input", "gases add up to more than 1"],
)
def test_a_malformed_request_is_invalid_input(inputs):
    response = api.predict(PredictRequest(model_id="flex_burning_rate", inputs=inputs))
    assert response.status == "invalid_input" and response.prediction is None
    assert response.message


def test_every_cited_row_exists_and_its_cells_are_verbatim():
    raw = read_raw_table("PSI-69").set_index("row")
    queries = [ask(n_nearest=25), ask(n_nearest=25, fuel="heptane", o2_mole_fraction=0.3, pressure_kpa=71.0)]
    for response in queries:
        assert len(response.nearest_tests) == 25
        distances = [test.distance for test in response.nearest_tests]
        assert distances == sorted(distances)
        for test in response.nearest_tests:
            assert (test.psi_id, test.file_name) == ("PSI-69", "PSI-69_Experimental table_FLEX.csv")
            assert test.doi == "10.60555/mbq8-0451"
            for column, cell in test.values.items():
                assert raw.at[test.row, column] == cell


def test_nearest_tests_are_the_same_fuel_and_can_be_switched_off():
    assert all(test.values["Fuel"] == "Heptane" for test in ask(fuel="heptane").nearest_tests)
    assert ask(n_nearest=0).nearest_tests == []


def test_training_is_deterministic():
    first = ask().prediction
    flex_burning_rate.fitted.cache_clear()
    assert ask().prediction == first
