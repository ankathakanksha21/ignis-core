"""Droplet burning-rate constant, trained on FLEX (PSI-69).

Two candidates are fitted on the same rows: ridge regression and
gradient-boosted trees. Both are scored by cross-validation grouped by test
condition, so repeats of one condition never sit on both sides of a split,
and compared against predicting the mean. The candidate with the lower
grouped mean absolute error is the one that answers predict(); the card
reports both, so the choice can be checked.

Nothing is saved to disk. The model is fitted from data/raw/ on first use
(well under a second) and cached for the life of the process.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from ..contract import (
    FeatureSpec,
    Metric,
    ModelCard,
    Prediction,
    PredictRequest,
    PredictResponse,
    TableRef,
    TestRef,
)
from ..features.flex import PSI_ID, SOURCE_COLUMNS, Exclusion, load_flex
from ..guards import RANGE_MARGIN, build_specs, check_inputs
from ..nearest import nearest_tests
from ..raw import investigation, read_raw_table

MODEL_ID = "flex_burning_rate"
VERSION = "0.1.0"
SEED = 0
N_FOLDS = 5

TARGET = "burning_rate_mm2_s"
TARGET_UNIT = "mm^2/s"
CATEGORICAL = ["fuel"]
NUMERIC_UNITS: dict[str, str] = {
    "o2_mole_fraction": "mole fraction",
    "co2_mole_fraction": "mole fraction",
    "he_mole_fraction": "mole fraction",
    "pressure_kpa": "kPa",
    "droplet_diameter_mm": "mm",
}
NUMERIC = list(NUMERIC_UNITS)
FEATURES = CATEGORICAL + NUMERIC
GAS_INPUTS = ["o2_mole_fraction", "co2_mole_fraction", "he_mole_fraction"]
DILUENTS = ["co2_mole_fraction", "he_mole_fraction"]

# Share of cross-validated errors the reported low-high range is built to hold.
RANGE_COVERAGE = 0.80
# Scaled distance to the closest real test above which the answer carries a
# caution. A project heuristic: 1.0 is one whole tested range on one input.
FAR_DISTANCE = 0.15

CITED_COLUMNS = [
    "FLEX Test #",
    "FLEX Identifier",
    "Test Date",
    *(SOURCE_COLUMNS[name] for name in [*FEATURES, TARGET, "test_end"]),
]


def _ridge() -> Pipeline:
    prepare = ColumnTransformer([("fuel", OneHotEncoder(), CATEGORICAL), ("numeric", StandardScaler(), NUMERIC)])
    return Pipeline([("prepare", prepare), ("model", Ridge(alpha=1.0))])


def _boosted_trees() -> Pipeline:
    prepare = ColumnTransformer([("fuel", OrdinalEncoder(), CATEGORICAL), ("numeric", "passthrough", NUMERIC)])
    model = GradientBoostingRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=3, min_samples_leaf=5, subsample=0.8, random_state=SEED
    )
    return Pipeline([("prepare", prepare), ("model", model)])


CANDIDATES: dict[str, Callable[[], Pipeline]] = {
    "ridge regression": _ridge,
    "gradient-boosted trees": _boosted_trees,
}


@dataclass(frozen=True)
class Scores:
    mae: float
    rmse: float
    r2: float
    residuals: np.ndarray  # measured minus predicted, out of fold


@dataclass(frozen=True)
class Fitted:
    train: pd.DataFrame
    raw: pd.DataFrame
    specs: list[FeatureSpec]
    scales: dict[str, float]
    served: str
    model: Pipeline
    by_condition: dict[str, Scores]  # candidate name, or "mean", -> scores
    by_test_date: dict[str, Scores]
    ranges: dict[str, tuple[float, float]]  # fuel -> (low, high) offsets added to a prediction
    reference: np.ndarray | None  # the average training test, as the linear model sees it
    table: TableRef
    left_out: tuple[Exclusion, ...]


def _score(measured: np.ndarray, predicted: np.ndarray) -> Scores:
    residuals = measured - predicted
    return Scores(
        mae=float(mean_absolute_error(measured, predicted)),
        rmse=float(np.sqrt(np.mean(residuals**2))),
        r2=float(r2_score(measured, predicted)),
        residuals=residuals,
    )


def _cross_validate(train: pd.DataFrame, group_column: str) -> dict[str, Scores]:
    """Out-of-fold scores for every candidate and for predicting the training mean."""
    inputs, target = train[FEATURES], train[TARGET].to_numpy()
    predicted = {name: np.zeros(len(train)) for name in [*CANDIDATES, "mean"]}
    for fit_rows, held_out in GroupKFold(n_splits=N_FOLDS).split(inputs, target, train[group_column]):
        for name, make in CANDIDATES.items():
            model = make().fit(inputs.iloc[fit_rows], target[fit_rows])
            predicted[name][held_out] = model.predict(inputs.iloc[held_out])
        predicted["mean"][held_out] = target[fit_rows].mean()
    return {name: _score(target, values) for name, values in predicted.items()}


def _dense(matrix) -> np.ndarray:
    return np.asarray(matrix.todense()) if hasattr(matrix, "todense") else np.asarray(matrix)


_PLAIN_NAMES = {
    "fuel": "fuel",
    "o2_mole_fraction": "oxygen",
    "co2_mole_fraction": "CO2",
    "he_mole_fraction": "helium",
    "pressure_kpa": "pressure",
    "droplet_diameter_mm": "droplet size",
}


def contributions(fit: "Fitted", values: dict[str, float | str]) -> tuple[float, dict[str, float]] | None:
    """How far each input moves the answer from the average FLEX test.

    Exact for the linear model: the average test's prediction plus these
    amounts is the prediction. None when the served model is not linear.
    """
    if fit.reference is None:
        return None
    prepare, linear = fit.model.named_steps["prepare"], fit.model.named_steps["model"]
    row = _dense(prepare.transform(pd.DataFrame([values])[FEATURES]))[0]
    moved: dict[str, float] = {}
    for name, amount in zip(prepare.get_feature_names_out(), linear.coef_ * (row - fit.reference)):
        key = "fuel" if name.startswith("fuel__") else name.split("__", 1)[1]
        moved[key] = moved.get(key, 0.0) + float(amount)
    return float(linear.intercept_ + linear.coef_ @ fit.reference), moved


def _why(fit: "Fitted", values: dict[str, float | str]) -> str:
    explained = contributions(fit, values)
    if explained is None:
        return ""
    average, moved = explained
    shown = sorted(((key, amount) for key, amount in moved.items() if abs(amount) >= 0.005), key=lambda item: -abs(item[1]))
    if not shown:
        return f" Why: every input is close to the average FLEX test ({average:.2f} {TARGET_UNIT})."
    parts = ", ".join(
        f"{'no ' if key in DILUENTS and values[key] == 0 else ''}{_PLAIN_NAMES[key]} {amount:+.2f}"
        for key, amount in shown
    )
    return f" Why: starting from the average FLEX test ({average:.2f} {TARGET_UNIT}), {parts}."


@lru_cache(maxsize=1)
def fitted() -> Fitted:
    flex = load_flex()
    frame = flex.frame
    left_out = list(flex.excluded)

    no_target = frame[TARGET].isna()
    left_out += [Exclusion(int(row), "no burning rate recorded") for row in frame.loc[no_target, "row"]]
    no_input = ~no_target & frame[NUMERIC].isna().any(axis=1)
    left_out += [Exclusion(int(row), "an input is not stated") for row in frame.loc[no_input, "row"]]
    train = frame.loc[~no_target & ~no_input].reset_index(drop=True)

    by_condition = _cross_validate(train, "condition")
    by_test_date = _cross_validate(train, "test_date")
    served = min(CANDIDATES, key=lambda name: by_condition[name].mae)
    model = CANDIDATES[served]().fit(train[FEATURES], train[TARGET].to_numpy())

    # Heptane scatters about twice as much as methanol between repeats, so one
    # shared range would be too wide for one fuel and too narrow for the other.
    tail = (1 - RANGE_COVERAGE) / 2
    residuals = by_condition[served].residuals
    ranges = {
        fuel: tuple(float(edge) for edge in np.quantile(residuals[(train["fuel"] == fuel).to_numpy()], [tail, 1 - tail]))
        for fuel in sorted(train["fuel"].unique())
    }
    linear = hasattr(model.named_steps["model"], "coef_")
    reference = _dense(model.named_steps["prepare"].transform(train[FEATURES])).mean(axis=0) if linear else None

    specs = build_specs(
        train,
        categorical={name: SOURCE_COLUMNS[name] for name in CATEGORICAL},
        numeric={name: (unit, SOURCE_COLUMNS[name]) for name, unit in NUMERIC_UNITS.items()},
    )
    return Fitted(
        train=train,
        raw=read_raw_table(PSI_ID),
        specs=specs,
        scales={spec.name: spec.tested_max - spec.tested_min for spec in specs if spec.kind == "numeric"},
        served=served,
        model=model,
        by_condition=by_condition,
        by_test_date=by_test_date,
        ranges=ranges,
        reference=reference,
        table=TableRef(
            psi_id=PSI_ID, file_name=flex.file_name, doi=investigation(PSI_ID)["doi"], n_rows=len(train)
        ),
        left_out=tuple(sorted(left_out, key=lambda item: item.row)),
    )


def _notes(fit: Fitted) -> str:
    by_reason: dict[str, list[int]] = {}
    for item in fit.left_out:
        by_reason.setdefault(item.reason, []).append(item.row)
    rows_left_out = "; ".join(
        f"{'row' if len(rows) == 1 else 'rows'} {', '.join(map(str, rows))} ({reason})"
        for reason, rows in by_reason.items()
    )
    others = [name for name in CANDIDATES if name != fit.served]
    return " ".join(
        [
            f"Trained on {len(fit.train)} of {len(fit.train) + len(fit.left_out)} FLEX tests, microgravity only.",
            f"Left out: {rows_left_out}.",
            f"Answers come from {fit.served}, which had the lower error under grouped cross-validation;"
            f" {' and '.join(others)} was fitted on the same rows and is reported beside it.",
            f"The low-high range holds {RANGE_COVERAGE:.0%} of the cross-validated errors for that fuel: "
            + ", ".join(f"{fuel} {low:+.2f} to {high:+.2f}" for fuel, (low, high) in fit.ranges.items())
            + f" {TARGET_UNIT}.",
            "Column headers lost their subscripts in PSI: O, N and CO are read as O2, N2 and CO2,"
            " and 'Burning rate; mm' is read as mm^2/s. Nitrogen is the balance gas and is not an input.",
            "Inputs are also checked per fuel, and CO2 with helium is withheld because FLEX never tested them together.",
            f"A value up to {RANGE_MARGIN:.0%} of the tested width beyond either end of a range is accepted,"
            " to allow for the spread between repeats of one set point.",
        ]
    )


def card() -> ModelCard:
    fit = fitted()
    served, mean = fit.by_condition[fit.served], fit.by_condition["mean"]
    evaluation = [
        Metric(name="mae", value=served.mae, baseline_name="mean", baseline_value=mean.mae),
        Metric(name="rmse", value=served.rmse, baseline_name="mean", baseline_value=mean.rmse),
        Metric(name="r2", value=served.r2, baseline_name="mean", baseline_value=mean.r2),
    ]
    evaluation += [
        Metric(
            name=f"mae, {name}", value=fit.by_condition[name].mae, baseline_name="mean", baseline_value=mean.mae
        )
        for name in CANDIDATES
    ]
    evaluation.append(
        Metric(
            name="mae, grouped by test date",
            value=fit.by_test_date[fit.served].mae,
            baseline_name="mean",
            baseline_value=fit.by_test_date["mean"].mae,
        )
    )
    return ModelCard(
        model_id=MODEL_ID,
        title="Droplet burning rate",
        status="available",
        fuel_class="droplet",
        task="regression",
        target="burning rate constant",
        target_unit=TARGET_UNIT,
        features=fit.specs,
        trained_on=[fit.table],
        evaluation=evaluation,
        cv_scheme=(
            f"GroupKFold, {N_FOLDS} folds, grouped by test condition (fuel, pressure level, gas mixture):"
            f" {fit.train['condition'].nunique()} conditions across {len(fit.train)} tests"
        ),
        version=VERSION,
        notes=_notes(fit),
    )


def estimate(fit: Fitted, values: dict[str, float | str]) -> float:
    """The served model's burning-rate constant for checked inputs, in mm^2/s."""
    return float(fit.model.predict(pd.DataFrame([values])[FEATURES])[0])


def _nearest(fit: Fitted, values: dict[str, float | str], n: int) -> list[TestRef]:
    return nearest_tests(
        fit.train, fit.raw, values, fit.scales, n, CITED_COLUMNS, match=CATEGORICAL, doi=fit.table.doi
    )


def predict(request: PredictRequest) -> PredictResponse:
    fit = fitted()
    checked = check_inputs(fit.specs, request.inputs, fit.train, presence_groups=[DILUENTS])

    errors = list(checked.errors)
    if not errors and sum(checked.values[name] for name in GAS_INPUTS) > 1 + 1e-9:
        errors.append("oxygen, CO2 and helium mole fractions add up to more than 1")
    if errors:
        return PredictResponse(
            status="invalid_input", model_id=MODEL_ID, message="; ".join(errors) + ".", model_version=VERSION
        )

    if checked.violations:
        untested_fuel = any(violation.feature in CATEGORICAL for violation in checked.violations)
        message = "Outside the conditions NASA tested in FLEX, so no prediction is given."
        return PredictResponse(
            status="withheld",
            model_id=MODEL_ID,
            out_of_range=list(checked.violations),
            nearest_tests=[] if untested_fuel else _nearest(fit, checked.values, request.n_nearest),
            message=" ".join([message, *checked.notes]),
            model_version=VERSION,
        )

    value = estimate(fit, checked.values)
    closest = _nearest(fit, checked.values, max(request.n_nearest, 1))
    low, high = fit.ranges[checked.values["fuel"]]
    message = f"Predicted by {fit.served} trained on {len(fit.train)} FLEX tests in microgravity."
    message += _why(fit, checked.values)
    if closest[0].distance > FAR_DISTANCE:
        message += (
            f" Caution: the closest real test is not close to these inputs (scaled distance"
            f" {closest[0].distance:.2f}), so this sits in a thinly tested part of the range."
        )
    return PredictResponse(
        status="ok",
        model_id=MODEL_ID,
        prediction=Prediction(
            value=round(value, 4),
            unit=TARGET_UNIT,
            low=round(max(value + low, 0.0), 4),
            high=round(value + high, 4),
        ),
        nearest_tests=closest[: request.n_nearest],
        message=message,
        model_version=VERSION,
    )
