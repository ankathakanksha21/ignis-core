"""Whether a gas flame hot-ignites, trained on ACME CFI-G Normal Flames (PSI-159).

Two candidates are fitted on the same rows: logistic regression and
gradient-boosted trees. Both are scored two ways and compared against always
answering the majority class:

    by setup      repeats of one setup (fuel, pressure level, fuel fraction,
                  fuel flow, oxygen level) stay on one side of a split. This
                  asks: can the model fill in between settings that were run?
    by test day   a whole day stays on one side. Each day used one fuel
                  bottle, so this asks: does it carry over to a day with
                  different settings?

The candidate with the higher macro F1 by setup answers predict(). Both sets
of scores go in the card, because the second one is much weaker.

Nothing is saved to disk. The model is fitted from data/raw/ on first use and
cached for the life of the process.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
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
from ..features.cfig import PSI_ID, SOURCE_COLUMNS, load_cfig
from ..features.flex import Exclusion
from ..guards import RANGE_MARGIN, build_specs, check_inputs
from ..nearest import nearest_tests
from ..raw import investigation, read_raw_table

MODEL_ID = "cfig_hot_ignition"
VERSION = "0.1.0"
SEED = 0
N_FOLDS = 5

TARGET = "hot_ignition"
CLASSES = ["yes", "no"]
CATEGORICAL = ["fuel"]
NUMERIC_UNITS: dict[str, str] = {
    "o2_mole_fraction": "mole fraction",
    "pressure_kpa": "kPa",
    "fuel_mole_fraction": "mole fraction",
    "fuel_flow_mg_s": "mg/s",
}
NUMERIC = list(NUMERIC_UNITS)
FEATURES = CATEGORICAL + NUMERIC

# Scaled distance to the closest real test above which the answer carries a
# caution. A project heuristic: 1.0 is one whole tested range on one input.
FAR_DISTANCE = 0.15

CITED_COLUMNS = [
    "Day",
    "Test",
    *(SOURCE_COLUMNS[name] for name in [*FEATURES, TARGET]),
    "burn time (sec)",
    "Self-ext or flow term",
    "Cool flame?",
    "Comments",
]


def _logistic() -> Pipeline:
    prepare = ColumnTransformer([("fuel", OneHotEncoder(), CATEGORICAL), ("numeric", StandardScaler(), NUMERIC)])
    return Pipeline([("prepare", prepare), ("model", LogisticRegression(max_iter=1000))])


def _boosted_trees() -> Pipeline:
    prepare = ColumnTransformer([("fuel", OrdinalEncoder(), CATEGORICAL), ("numeric", "passthrough", NUMERIC)])
    model = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=2, min_samples_leaf=5, subsample=0.8, random_state=SEED
    )
    return Pipeline([("prepare", prepare), ("model", model)])


CANDIDATES: dict[str, Callable[[], Pipeline]] = {
    "logistic regression": _logistic,
    "gradient-boosted trees": _boosted_trees,
}
BASELINE = "majority class"


@dataclass(frozen=True)
class Scores:
    accuracy: float
    balanced_accuracy: float
    macro_f1: float


@dataclass(frozen=True)
class Fitted:
    train: pd.DataFrame
    raw: pd.DataFrame
    specs: list[FeatureSpec]
    scales: dict[str, float]
    served: str
    model: Pipeline
    by_setup: dict[str, Scores]  # candidate name, or the baseline, -> scores
    by_test_day: dict[str, Scores]
    table: TableRef
    left_out: tuple[Exclusion, ...]


def _probability_of_yes(model: Pipeline, inputs: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(inputs)[:, list(model.classes_).index("yes")]


def _score(measured: np.ndarray, probability_of_yes: np.ndarray) -> Scores:
    predicted = np.where(probability_of_yes >= 0.5, "yes", "no")
    return Scores(
        accuracy=float(accuracy_score(measured, predicted)),
        balanced_accuracy=float(balanced_accuracy_score(measured, predicted)),
        macro_f1=float(f1_score(measured, predicted, average="macro", labels=CLASSES, zero_division=0)),
    )


def _cross_validate(train: pd.DataFrame, group_column: str) -> dict[str, Scores]:
    """Out-of-fold scores for every candidate and for the training share of 'yes'."""
    inputs, target = train[FEATURES], train[TARGET].to_numpy()
    probability = {name: np.zeros(len(train)) for name in [*CANDIDATES, BASELINE]}
    for fit_rows, held_out in GroupKFold(n_splits=N_FOLDS).split(inputs, target, train[group_column]):
        for name, make in CANDIDATES.items():
            model = make().fit(inputs.iloc[fit_rows], target[fit_rows])
            probability[name][held_out] = _probability_of_yes(model, inputs.iloc[held_out])
        probability[BASELINE][held_out] = float(np.mean(target[fit_rows] == "yes"))
    return {name: _score(target, values) for name, values in probability.items()}


@lru_cache(maxsize=1)
def fitted() -> Fitted:
    cfig = load_cfig()
    train = cfig.frame

    by_setup = _cross_validate(train, "setup")
    by_test_day = _cross_validate(train, "day")
    served = max(CANDIDATES, key=lambda name: by_setup[name].macro_f1)
    model = CANDIDATES[served]().fit(train[FEATURES], train[TARGET].to_numpy())

    specs = build_specs(
        train,
        categorical={name: SOURCE_COLUMNS[name] for name in CATEGORICAL},
        numeric={name: (unit, SOURCE_COLUMNS[name]) for name, unit in NUMERIC_UNITS.items()},
    )
    return Fitted(
        train=train,
        raw=read_raw_table(PSI_ID, cfig.file_name),
        specs=specs,
        scales={spec.name: spec.tested_max - spec.tested_min for spec in specs if spec.kind == "numeric"},
        served=served,
        model=model,
        by_setup=by_setup,
        by_test_day=by_test_day,
        table=TableRef(
            psi_id=PSI_ID, file_name=cfig.file_name, doi=investigation(PSI_ID)["doi"], n_rows=len(train)
        ),
        left_out=cfig.excluded,
    )


def _notes(fit: Fitted) -> str:
    by_reason: dict[str, list[int]] = {}
    for item in fit.left_out:
        by_reason.setdefault(item.reason, []).append(item.row)
    rows_left_out = "; ".join(
        f"{'row' if len(rows) == 1 else 'rows'} {', '.join(map(str, rows))} ({reason})"
        for reason, rows in by_reason.items()
    )
    day, day_baseline = fit.by_test_day[fit.served], fit.by_test_day[BASELINE]
    carries_over = day.macro_f1 > day_baseline.macro_f1 and day.accuracy > day_baseline.accuracy
    others = [name for name in CANDIDATES if name != fit.served]
    return " ".join(
        [
            f"Trained on {len(fit.train)} of {len(fit.train) + len(fit.left_out)} CFI-G Normal Flames tests,"
            " microgravity only.",
            f"Left out: {rows_left_out or 'nothing'}.",
            f"Answers come from {fit.served}, which scored higher by setup;"
            f" {' and '.join(others)} was fitted on the same rows and is reported beside it.",
            (
                "It also beats the majority class when a whole test day is held out."
                if carries_over
                else "Weak point: when a whole test day is held out, it does no better than always answering"
                " the majority class. It fills in between settings that were run, and does not carry over"
                " to a day with different settings. Use it as a guide inside the tested conditions only."
            ),
            "Hot ignition means the flame lit as an ordinary hot flame. It says nothing about cool flames:"
            " only 8 rows of this table carry a cool-flame label.",
            "The Fuel column names the bottle (for example '30% butane'). The model takes the species from it"
            " and the fuel fraction actually fed from the Xf column.",
            "The Inverse Flames table is not used.",
            f"Inputs are also checked per fuel. A value up to {RANGE_MARGIN:.0%} of the tested width beyond"
            " either end of a range is accepted.",
        ]
    )


def card() -> ModelCard:
    fit = fitted()
    served, baseline = fit.by_setup[fit.served], fit.by_setup[BASELINE]
    day, day_baseline = fit.by_test_day[fit.served], fit.by_test_day[BASELINE]

    def metric(name: str, value: float, against: float) -> Metric:
        return Metric(name=name, value=value, baseline_name=BASELINE, baseline_value=against)

    evaluation = [
        metric("macro_f1", served.macro_f1, baseline.macro_f1),
        metric("balanced_accuracy", served.balanced_accuracy, baseline.balanced_accuracy),
        metric("accuracy", served.accuracy, baseline.accuracy),
        *(metric(f"macro_f1, {name}", fit.by_setup[name].macro_f1, baseline.macro_f1) for name in CANDIDATES),
        metric("macro_f1, grouped by test day", day.macro_f1, day_baseline.macro_f1),
        metric("accuracy, grouped by test day", day.accuracy, day_baseline.accuracy),
    ]
    return ModelCard(
        model_id=MODEL_ID,
        title="Gas flame hot ignition",
        status="available",
        fuel_class="gas",
        task="classification",
        target="hot ignition",
        classes=CLASSES,
        features=fit.specs,
        trained_on=[fit.table],
        evaluation=evaluation,
        cv_scheme=(
            f"GroupKFold, {N_FOLDS} folds, grouped by setup (fuel, pressure level, fuel fraction, fuel flow,"
            f" oxygen level): {fit.train['setup'].nunique()} setups across {len(fit.train)} tests."
            f" Also scored grouped by test day ({fit.train['day'].nunique()} days)."
        ),
        version=VERSION,
        notes=_notes(fit),
    )


def _nearest(fit: Fitted, values: dict[str, float | str], n: int) -> list[TestRef]:
    return nearest_tests(
        fit.train, fit.raw, values, fit.scales, n, CITED_COLUMNS, match=CATEGORICAL, doi=fit.table.doi
    )


def predict(request: PredictRequest) -> PredictResponse:
    fit = fitted()
    checked = check_inputs(fit.specs, request.inputs, fit.train)

    if checked.errors:
        return PredictResponse(
            status="invalid_input",
            model_id=MODEL_ID,
            message="; ".join(checked.errors) + ".",
            model_version=VERSION,
        )

    if checked.violations:
        untested_fuel = any(violation.feature in CATEGORICAL for violation in checked.violations)
        message = "Outside the conditions NASA tested in CFI-G Normal Flames, so no prediction is given."
        return PredictResponse(
            status="withheld",
            model_id=MODEL_ID,
            out_of_range=list(checked.violations),
            nearest_tests=[] if untested_fuel else _nearest(fit, checked.values, request.n_nearest),
            message=" ".join([message, *checked.notes]),
            model_version=VERSION,
        )

    yes = float(_probability_of_yes(fit.model, pd.DataFrame([checked.values])[FEATURES])[0])
    closest = _nearest(fit, checked.values, max(request.n_nearest, 1))
    message = (
        f"Predicted by {fit.served} trained on {len(fit.train)} CFI-G tests in microgravity."
        " It fills in between tested settings and is weak on settings unlike any test day."
    )
    if closest[0].distance > FAR_DISTANCE:
        message += (
            f" Caution: the closest real test is not close to these inputs (scaled distance"
            f" {closest[0].distance:.2f}), so this sits in a thinly tested part of the range."
        )
    return PredictResponse(
        status="ok",
        model_id=MODEL_ID,
        prediction=Prediction(
            label="yes" if yes >= 0.5 else "no",
            class_probabilities={"yes": round(yes, 3), "no": round(1 - yes, 3)},
        ),
        nearest_tests=closest[: request.n_nearest],
        message=message,
        model_version=VERSION,
    )
