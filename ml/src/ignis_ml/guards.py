"""Checks a prediction request before any model runs.

Two outcomes stop a prediction:

    errors      the request itself is wrong (an input is missing, not a number,
                or not one the model takes)            -> invalid_input
    violations  the request is well formed but asks about conditions NASA did
                not test                               -> withheld

A value is checked three ways, each against the rows the model was trained on:

    1. against the whole tested range of that input;
    2. against the range tested for the chosen category (heptane and methanol
       were not tested over exactly the same ranges);
    3. for inputs that are either present or absent (diluents), against the
       range tested alongside the other one. FLEX never has CO2 and helium in
       the same test, so asking for both is outside what was tested even
       though each value alone is in range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from .contract import FeatureSpec, RangeViolation

# A value this fraction of the tested width beyond either end still counts as
# tested. Repeats of one set point are not identical (FLEX runs at its lowest
# pressure level differ from each other by more than this), so without it a
# query at the nominal set point can fall a hair outside the smallest test.
RANGE_MARGIN = 0.01


@dataclass(frozen=True)
class Checked:
    values: dict[str, float | str]
    errors: tuple[str, ...] = ()
    violations: tuple[RangeViolation, ...] = ()
    notes: tuple[str, ...] = ()


def build_specs(
    train: pd.DataFrame,
    categorical: dict[str, str],
    numeric: dict[str, tuple[str | None, str]],
) -> list[FeatureSpec]:
    """Tested ranges and categories, computed from the training rows.

    categorical: name -> source column.  numeric: name -> (unit, source column).
    """
    specs = [
        FeatureSpec(name=name, kind="categorical", categories=sorted(train[name].unique()), source_column=column)
        for name, column in categorical.items()
    ]
    specs += [
        FeatureSpec(
            name=name, kind="numeric", unit=unit, source_column=column,
            tested_min=float(train[name].min()), tested_max=float(train[name].max()),
        )
        for name, (unit, column) in numeric.items()
    ]  # fmt: skip
    return specs


def _within(value: float, low: float, high: float) -> bool:
    slack = RANGE_MARGIN * (high - low) + 1e-9
    return low - slack <= value <= high + slack


def _span(low: float, high: float) -> str:
    return f"always {low:g}" if low == high else f"tested from {low:g} to {high:g}"


def check_inputs(
    specs: Sequence[FeatureSpec],
    inputs: dict[str, float | str],
    train: pd.DataFrame,
    presence_groups: Sequence[Sequence[str]] = (),
) -> Checked:
    names = [spec.name for spec in specs]
    errors = [f"{name} is not an input of this model" for name in sorted(set(inputs) - set(names))]
    errors += [f"{name} is missing" for name in names if name not in inputs]

    values: dict[str, float | str] = {}
    for spec in specs:
        if spec.name not in inputs:
            continue
        given = inputs[spec.name]
        if spec.kind == "numeric":
            if isinstance(given, bool) or not isinstance(given, (int, float)) or not math.isfinite(given):
                errors.append(f"{spec.name} must be a number")
            else:
                values[spec.name] = float(given)
        elif not isinstance(given, str) or not given.strip():
            errors.append(f"{spec.name} must be text")
        else:
            values[spec.name] = given.strip().lower()
    if errors:
        return Checked(values=values, errors=tuple(errors))

    violations: dict[str, RangeViolation] = {}
    notes: list[str] = []
    categorical = [spec for spec in specs if spec.kind == "categorical"]
    numeric = [spec for spec in specs if spec.kind == "numeric"]

    for spec in categorical:
        if values[spec.name] not in (spec.categories or []):
            violations[spec.name] = RangeViolation(
                feature=spec.name, value=values[spec.name], categories=spec.categories
            )
    for spec in numeric:
        if not _within(values[spec.name], spec.tested_min, spec.tested_max):
            violations[spec.name] = RangeViolation(
                feature=spec.name, value=values[spec.name],
                tested_min=spec.tested_min, tested_max=spec.tested_max,
            )  # fmt: skip
    if any(spec.name in violations for spec in categorical):
        return Checked(values=values, violations=tuple(violations.values()))

    subset = train
    for spec in categorical:
        subset = subset[subset[spec.name] == values[spec.name]]
    chosen = ", ".join(f"{spec.name} = {values[spec.name]}" for spec in categorical)

    for spec in numeric:
        if spec.name in violations:
            continue
        low, high = float(subset[spec.name].min()), float(subset[spec.name].max())
        if not _within(values[spec.name], low, high):
            violations[spec.name] = RangeViolation(
                feature=spec.name, value=values[spec.name], tested_min=low, tested_max=high
            )
            notes.append(f"With {chosen}, {spec.name} was {_span(low, high)}.")

    for group in presence_groups:
        present = [name for name in group if values[name] > 0]
        for anchor in present:
            alongside = subset[subset[anchor] > 0]
            if alongside.empty:
                continue
            for other in present:
                if other == anchor or other in violations:
                    continue
                low, high = float(alongside[other].min()), float(alongside[other].max())
                if not _within(values[other], low, high):
                    violations[other] = RangeViolation(
                        feature=other, value=values[other], tested_min=low, tested_max=high
                    )
                    notes.append(f"In tests with {anchor} above zero, {other} was {_span(low, high)}.")

    return Checked(values=values, violations=tuple(violations.values()), notes=tuple(notes))
