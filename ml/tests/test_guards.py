"""The range check, on a small made-up table so each rule is visible."""

import pandas as pd

from ignis_ml.guards import build_specs, check_inputs

TRAIN = pd.DataFrame(
    {
        "fuel": ["a", "a", "a", "b", "b"],
        "oxygen": [0.10, 0.20, 0.30, 0.15, 0.25],
        "co2": [0.0, 0.5, 0.0, 0.0, 0.0],
        "he": [0.0, 0.0, 0.4, 0.0, 0.0],
    }
)
SPECS = build_specs(
    TRAIN,
    categorical={"fuel": "Fuel"},
    numeric={"oxygen": ("mole fraction", "O"), "co2": ("mole fraction", "CO"), "he": ("mole fraction", "He")},
)
GOOD = {"fuel": "a", "oxygen": 0.2, "co2": 0.0, "he": 0.0}


def check(**changes):
    return check_inputs(SPECS, {**GOOD, **changes}, TRAIN, presence_groups=[["co2", "he"]])


def test_ranges_and_categories_come_from_the_training_rows():
    by_name = {spec.name: spec for spec in SPECS}
    assert by_name["fuel"].categories == ["a", "b"]
    assert (by_name["oxygen"].tested_min, by_name["oxygen"].tested_max) == (0.10, 0.30)
    assert by_name["oxygen"].source_column == "O"


def test_a_good_request_passes_and_text_is_normalised():
    result = check(fuel="  A ")
    assert not result.errors and not result.violations
    assert result.values["fuel"] == "a"


def test_missing_unknown_and_malformed_inputs_are_errors():
    assert "oxygen is missing" in check_inputs(SPECS, {"fuel": "a", "co2": 0, "he": 0}, TRAIN).errors
    assert "gravity is not an input of this model" in check(gravity=0.0).errors
    assert "oxygen must be a number" in check(oxygen="0.2").errors
    assert "oxygen must be a number" in check(oxygen=float("nan")).errors
    assert "fuel must be text" in check(fuel=1.0).errors


def test_a_value_outside_the_whole_range_is_a_violation():
    violation = check(oxygen=0.5).violations[0]
    assert (violation.feature, violation.tested_min, violation.tested_max) == ("oxygen", 0.10, 0.30)


def test_a_value_a_hair_past_the_end_still_counts_as_tested():
    assert not check(oxygen=0.3015).violations
    assert check(oxygen=0.305).violations


def test_an_untested_category_is_a_violation():
    violation = check(fuel="c").violations[0]
    assert (violation.feature, violation.categories) == ("fuel", ["a", "b"])


def test_the_range_is_also_checked_for_the_chosen_category():
    result = check(fuel="b", oxygen=0.29)
    assert (result.violations[0].tested_min, result.violations[0].tested_max) == (0.15, 0.25)
    assert "fuel = b" in result.notes[0]


def test_two_diluents_never_tested_together_are_a_violation():
    result = check(co2=0.2, he=0.2)
    assert {violation.feature for violation in result.violations} == {"co2", "he"}
    assert not check(co2=0.2).violations
    assert not check(he=0.2).violations
