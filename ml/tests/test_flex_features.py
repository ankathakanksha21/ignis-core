"""FLEX text becomes typed features without losing the link to the raw row."""

import math
import re

import pytest

from ignis_ml.features.flex import MMHG_TO_KPA, SOURCE_COLUMNS, load_flex, parse_number
from ignis_ml.raw import read_raw_table


def test_the_zero_pressure_row_is_left_out_and_says_why():
    flex = load_flex()
    assert [item.row for item in flex.excluded] == [115]
    assert "0 mmHg" in flex.excluded[0].reason
    assert 115 not in set(flex.frame["row"])
    assert len(flex.frame) == 273


def test_values_are_converted_to_contract_units():
    first = load_flex().frame.set_index("row").loc[2]
    assert first["fuel"] == "methanol"
    assert first["pressure_kpa"] == pytest.approx(757.7 * MMHG_TO_KPA)
    assert first["o2_mole_fraction"] == 0.21
    assert first["burning_rate_mm2_s"] == 0.52
    assert first["test_date"] == "2009-03-05"


def test_every_typed_row_still_points_at_its_raw_row():
    typed = load_flex().frame.set_index("row")
    raw = read_raw_table("PSI-69").set_index("row")
    assert set(typed.index) <= set(raw.index)
    assert (typed["psi_id"] == "PSI-69").all()
    for row in typed.index:
        assert typed.at[row, "fuel"] == raw.at[row, SOURCE_COLUMNS["fuel"]].strip().lower()
        assert typed.at[row, "o2_mole_fraction"] == float(raw.at[row, SOURCE_COLUMNS["o2_mole_fraction"]])


def test_a_cell_that_is_not_stated_becomes_nan_never_zero():
    for cell in ["", "  ", "-", "–"]:
        value, approximate = parse_number(cell)
        assert math.isnan(value) and not approximate
    assert parse_number("0.52") == (0.52, False)
    assert parse_number("~6") == (6.0, True)
    with pytest.raises(ValueError):
        parse_number("n/a")


def test_approximate_cells_are_recorded():
    assert load_flex().approximate == ((224, "Burn time; s"), (225, "Burn time; s"))


def test_dates_are_normalised_and_repeats_share_a_condition():
    frame = load_flex().frame
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) for text in frame["test_date"])
    assert frame["condition"].nunique() < len(frame) / 2
