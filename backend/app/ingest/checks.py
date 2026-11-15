"""Validation rules. Each returns flags: one line per suspicious cell.

A flag never changes the raw data. A value that fails a physical bound is
left out of conditions.csv; everything else is kept and only marked.
The thresholds are this project's judgement, not NASA's.
"""

from __future__ import annotations

import re
from typing import Callable

import pandas as pd

Flag = dict  # row, column, check, detail
Check = Callable[[pd.DataFrame], list[Flag]]

# Canonical field -> (lowest allowed, highest allowed, lowest is itself allowed, rule in words)
BOUNDS = {
    "o2_mole_fraction": (0.0, 1.0, True, "a mole fraction is between 0 and 1"),
    "burner_o2_mole_fraction": (0.0, 1.0, True, "a mole fraction is between 0 and 1"),
    "n2_mole_fraction": (0.0, 1.0, True, "a mole fraction is between 0 and 1"),
    "co2_mole_fraction": (0.0, 1.0, True, "a mole fraction is between 0 and 1"),
    "he_mole_fraction": (0.0, 1.0, True, "a mole fraction is between 0 and 1"),
    "pressure_kpa": (0.0, None, False, "a test pressure is above 0"),
    "flow_cm_s": (0.0, None, True, "a flow speed is not negative"),
}

KNOWN_SPECIES = {"CH4", "C2H4", "C2H6", "C3H6", "C3H8", "C12H26", "H2", "N2", "O2", "CO2"}
_FORMULA = re.compile(r"\b[A-Z][A-Za-z]*\d+[A-Za-z0-9]*\b")


def out_of_bounds(field: str, value: float) -> str:
    """The rule a value breaks, or '' if it is physically possible."""
    low, high, low_allowed, rule = BOUNDS[field]
    below = value < low or (value == low and not low_allowed)
    above = high is not None and value > high
    return rule if below or above else ""


def _number(text: str) -> float | None:
    try:
        return float(text.strip())
    except ValueError:
        return None


def after_not_above_before(before: str, after: str, *, max_rise: float, min_ratio: float | None = None) -> Check:
    """Burning uses oxygen, so the reading after a test should not be higher
    than before it, nor a small fraction of it."""

    def check(frame: pd.DataFrame) -> list[Flag]:
        flags = []
        for row in frame.to_dict("records"):
            first, last = _number(row[before]), _number(row[after])
            if first is None or last is None:
                continue
            if last - first > max_rise:
                detail = f"reads {last:g} after the test and {first:g} before it; burning cannot add oxygen"
                flags.append({"row": row["row"], "column": after, "check": "after_exceeds_before", "detail": detail})
            elif min_ratio is not None and last < first * min_ratio:
                detail = f"reads {last:g} after the test and {first:g} before it; a drop this large is not plausible"
                flags.append({"row": row["row"], "column": after, "check": "implausible_drop", "detail": detail})
        return flags

    return check


def not_negative(column: str) -> Check:
    def check(frame: pd.DataFrame) -> list[Flag]:
        return [
            {"row": row["row"], "column": column, "check": "negative_value",
             "detail": f"{row[column].strip()} is below zero; a concentration cannot be negative"}
            for row in frame.to_dict("records")
            if (value := _number(row[column])) is not None and value < 0
        ]  # fmt: skip

    return check


def unique(column: str) -> Check:
    def check(frame: pd.DataFrame) -> list[Flag]:
        filled = frame[frame[column].str.strip() != ""]
        repeated = filled[filled[column].duplicated(keep=False)]
        return [
            {"row": row["row"], "column": column, "check": "duplicate_id",
             "detail": f"{row[column]!r} identifies more than one row"}
            for row in repeated.to_dict("records")
        ]  # fmt: skip

    return check


def known_species(column: str) -> Check:
    """Catches spreadsheet fill-down errors such as CH4, CH5, CH6 or N2, N3, N4."""

    def check(frame: pd.DataFrame) -> list[Flag]:
        flags = []
        for row in frame.to_dict("records"):
            unknown = [name for name in _FORMULA.findall(row[column]) if name not in KNOWN_SPECIES]
            if unknown:
                detail = f"{', '.join(unknown)} is not a gas used in these tests; likely a spreadsheet fill-down error"
                flags.append({"row": row["row"], "column": column, "check": "unrecognised_species", "detail": detail})
        return flags

    return check


def no_repeated_rows() -> Check:
    def check(frame: pd.DataFrame) -> list[Flag]:
        data = frame.drop(columns=["psi_id", "file_name", "row"])
        first_seen: dict[tuple, int] = {}
        flags = []
        for row_number, cells in zip(frame["row"], data.itertuples(index=False, name=None)):
            if cells in first_seen:
                detail = f"every cell repeats row {first_seen[cells]}"
                flags.append({"row": row_number, "column": data.columns[0], "check": "duplicate_row", "detail": detail})
            else:
                first_seen[cells] = row_number
        return flags

    return check
