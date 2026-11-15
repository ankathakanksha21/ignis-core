"""Tests from a NASA report outside PSI, used only to check the burning-rate model."""

import csv

import pytest

from ignis_ml import api
from ignis_ml.models import flex_burning_rate
from ignis_ml.outside import PATH, load_outside_tests
from ignis_ml.raw import repo_root


@pytest.fixture(scope="module")
def card():
    return next(card for card in api.model_cards() if card.model_id == "flex_burning_rate")


def test_the_copied_table_is_complete_and_keeps_cells_as_printed():
    with repo_root().joinpath(*PATH).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [int(row["test"]) for row in rows] == list(range(1, 54))
    assert {row["report_page"] for row in rows} == {"17", "18", "19"}
    by_test = {int(row["test"]): row for row in rows}
    assert by_test[1]["k_overall_mm2_s"] == "1.26" and by_test[1]["footnotes"] == "a"
    assert by_test[17]["initial_diameter_mm"] == "1.18 ± 0.25" and by_test[17]["k_overall_mm2_s"] == "f"
    assert by_test[36]["oxygen"] == "Air" and by_test[36]["k_final_mm2_s"] == "e"
    assert by_test[39]["pressure_bar"] == ""  # Table 2 states no pressure


def test_only_tests_with_an_exact_diameter_and_a_burning_rate_are_typed():
    tests = load_outside_tests()
    assert len(tests) == 50
    assert not set(tests["test"]) & {17, 27, 33}
    assert dict(tests["atmosphere"].value_counts()) == {"helium-oxygen": 31, "air": 19}
    first = tests.set_index("test").loc[1]
    assert (first["o2_mole_fraction"], first["he_mole_fraction"], first["pressure_kpa"]) == (0.35, 0.65, 100.0)
    assert (first["droplet_diameter_mm"], first["burning_rate_mm2_s"]) == (3.93, 1.26)
    air = tests.set_index("test").loc[40]
    assert (air["o2_mole_fraction"], air["he_mole_fraction"], air["pressure_kpa"]) == (0.21, 0.0, 100.0)


def test_outside_tests_are_never_training_rows():
    train = flex_burning_rate.fitted().train
    assert len(train) == 255 and set(train["psi_id"]) == {"PSI-69"}


def test_the_check_scores_only_what_the_model_would_answer():
    check = flex_burning_rate.outside_check()
    assert (check.tests, check.answered) == (50, 9)
    assert sum(n for n, _ in check.by_experiment.values()) == 9
    assert set(check.by_experiment) == {"DCE", "FSDC"}
    # Every helium-oxygen test has more helium than FLEX ran with heptane, so none is answered.
    fit = flex_burning_rate.fitted()
    heptane = fit.train[fit.train["fuel"] == "heptane"]
    outside = load_outside_tests()
    assert outside.loc[outside["atmosphere"] == "helium-oxygen", "he_mole_fraction"].min() > heptane["he_mole_fraction"].max()


def test_the_card_reports_the_outside_check_even_though_it_is_weak(card):
    check = flex_burning_rate.outside_check()
    metric = next(metric for metric in card.evaluation if "outside check" in metric.name)
    assert metric.value == check.mae and metric.baseline_value == check.mean_mae
    assert "not used in training" in metric.name
    cross_validated = next(metric for metric in card.evaluation if metric.name == "mae")
    assert metric.value > 2 * cross_validated.value  # the weak result is shown, not hidden
    assert "Outside check, not used in training" in card.notes
    assert "NASA/TM-2003-212553" in card.notes and "would be withheld" in card.notes
