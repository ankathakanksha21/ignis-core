"""Does a droplet flame put itself out? Trained on FLEX (PSI-69).

FLEX records how each burn ended. "Extinction" means the flame went out by
itself while fuel was left, which is the outcome fire safety hopes for. The
other two endings, the droplet burning away ("Completion") and the droplet
breaking apart while burning ("Disruption"), both mean the flame did not put
itself out, so they are grouped as "no". Telling those two apart from the
inputs does not work (it scores at the baseline), so the model does not try.

Inputs, range checks and nearest tests are the same as for the burning-rate
model. Logistic regression and gradient-boosted trees are scored by
cross-validation grouped by test condition, and by test date, against always
answering the majority class. The higher macro F1 by condition serves.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from ..contract import FeatureSpec, Metric, ModelCard, Prediction, PredictRequest, PredictResponse, TableRef
from ..features.flex import ATM_KPA, PSI_ID, SOURCE_COLUMNS, Exclusion, load_flex
from ..guards import RANGE_MARGIN, build_specs, check_inputs
from ..nearest import cite, rank_tests
from ..raw import investigation, read_raw_table
from ._classification import BASELINE, CLASSES, Scores, cross_validate, probability_of_yes
from .flex_burning_rate import (
    CATEGORICAL,
    CITED_COLUMNS,
    DILUENTS,
    FAR_DISTANCE,
    FEATURES,
    GAS_INPUTS,
    NUMERIC,
    NUMERIC_UNITS,
)

MODEL_ID = "flex_extinction"
VERSION = "0.1.0"
SEED = 0
TARGET = "self_extinguished"
N_SUMMARISED = 5  # nearest real tests whose endings are counted in the message


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


@dataclass(frozen=True)
class Fitted:
    train: pd.DataFrame
    raw: pd.DataFrame
    specs: list[FeatureSpec]
    scales: dict[str, float]
    served: str
    model: Pipeline
    by_condition: dict[str, Scores]
    by_test_date: dict[str, Scores]
    table: TableRef
    left_out: tuple[Exclusion, ...]


@lru_cache(maxsize=1)
def fitted() -> Fitted:
    flex = load_flex()
    frame = flex.frame
    no_input = frame[NUMERIC].isna().any(axis=1)
    left_out = [*flex.excluded, *(Exclusion(int(row), "an input is not stated") for row in frame.loc[no_input, "row"])]
    train = frame.loc[~no_input].reset_index(drop=True)
    train[TARGET] = ["yes" if end == "Extinction" else "no" for end in train["test_end"]]

    by_condition = cross_validate(train, FEATURES, TARGET, "condition", CANDIDATES)
    by_test_date = cross_validate(train, FEATURES, TARGET, "test_date", CANDIDATES)
    served = max(CANDIDATES, key=lambda name: by_condition[name].macro_f1)
    model = CANDIDATES[served]().fit(train[FEATURES], train[TARGET].to_numpy())

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
        table=TableRef(
            psi_id=PSI_ID, file_name=flex.file_name, doi=investigation(PSI_ID)["doi"], n_rows=len(train)
        ),
        left_out=tuple(sorted(left_out, key=lambda item: item.row)),
    )


def low_pressure_contrast(train: pd.DataFrame) -> str:
    """What FLEX measured near 0.7 atm, the pressure closest to exploration cabins."""
    low = train[train["pressure_kpa"] < 0.8 * ATM_KPA]
    air, rich = low[low["o2_mole_fraction"] <= 0.21], low[low["o2_mole_fraction"] >= 0.30]
    return (
        f"Measured, not predicted: in FLEX tests near 0.7 atm, {int((air[TARGET] == 'yes').sum())} of {len(air)}"
        f" flames put themselves out at 21% oxygen or less, and {int((rich[TARGET] == 'yes').sum())} of {len(rich)}"
        " at 30% oxygen or more."
    )


def _notes(fit: Fitted) -> str:
    by_reason: dict[str, list[int]] = {}
    for item in fit.left_out:
        by_reason.setdefault(item.reason, []).append(item.row)
    rows_left_out = "; ".join(
        f"{'row' if len(rows) == 1 else 'rows'} {', '.join(map(str, rows))} ({reason})"
        for reason, rows in by_reason.items()
    )
    ends = Counter(fit.train["test_end"])
    others = [name for name in CANDIDATES if name != fit.served]
    return " ".join(
        [
            f"Trained on {len(fit.train)} of {len(fit.train) + len(fit.left_out)} FLEX tests, microgravity only.",
            f"Left out: {rows_left_out}.",
            f"'yes' is the table's Extinction ending ({ends['Extinction']} tests): the flame went out by itself"
            f" with fuel left. 'no' groups Completion ({ends['Completion']}) and Disruption ({ends['Disruption']}):"
            " the droplet burned away or broke apart while burning. The model does not tell those two apart.",
            low_pressure_contrast(fit.train),
            f"Answers come from {fit.served}, which scored higher under grouped cross-validation;"
            f" {' and '.join(others)} was fitted on the same rows and is reported beside it.",
            "A 'yes' is not a safe verdict: it describes a single droplet in still gas and says nothing about"
            " solids, airflow or other gravity levels.",
            "Inputs are also checked per fuel, and CO2 with helium is withheld because FLEX never tested them"
            f" together. A value up to {RANGE_MARGIN:.0%} of the tested width beyond either end of a range is accepted.",
        ]
    )


def card() -> ModelCard:
    fit = fitted()
    served, baseline = fit.by_condition[fit.served], fit.by_condition[BASELINE]
    date, date_baseline = fit.by_test_date[fit.served], fit.by_test_date[BASELINE]

    def metric(name: str, value: float, against: float) -> Metric:
        return Metric(name=name, value=value, baseline_name=BASELINE, baseline_value=against)

    return ModelCard(
        model_id=MODEL_ID,
        title="Droplet flame self-extinction",
        status="available",
        fuel_class="droplet",
        task="classification",
        target="flame puts itself out",
        classes=CLASSES,
        features=fit.specs,
        trained_on=[fit.table],
        evaluation=[
            metric("macro_f1", served.macro_f1, baseline.macro_f1),
            metric("balanced_accuracy", served.balanced_accuracy, baseline.balanced_accuracy),
            metric("accuracy", served.accuracy, baseline.accuracy),
            *(metric(f"macro_f1, {name}", fit.by_condition[name].macro_f1, baseline.macro_f1) for name in CANDIDATES),
            metric("macro_f1, grouped by test date", date.macro_f1, date_baseline.macro_f1),
            metric("accuracy, grouped by test date", date.accuracy, date_baseline.accuracy),
        ],
        cv_scheme=(
            "GroupKFold, 5 folds, grouped by test condition (fuel, pressure level, gas mixture):"
            f" {fit.train['condition'].nunique()} conditions across {len(fit.train)} tests."
            " Also scored grouped by test date."
        ),
        version=VERSION,
        notes=_notes(fit),
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

    untested_fuel = any(violation.feature in CATEGORICAL for violation in checked.violations)
    ranked = (
        fit.train.iloc[0:0].assign(distance=[])
        if untested_fuel
        else rank_tests(fit.train, checked.values, fit.scales, match=CATEGORICAL)
    )
    wanted = cite(ranked.head(request.n_nearest), fit.raw, CITED_COLUMNS, doi=fit.table.doi)

    if checked.violations:
        return PredictResponse(
            status="withheld",
            model_id=MODEL_ID,
            out_of_range=list(checked.violations),
            nearest_tests=wanted,
            message=" ".join(
                ["Outside the conditions NASA tested in FLEX, so no prediction is given.", *checked.notes]
            ),
            model_version=VERSION,
        )

    yes = float(probability_of_yes(fit.model, pd.DataFrame([checked.values])[FEATURES])[0])
    closest = ranked.head(N_SUMMARISED)
    endings = ", ".join(f"{count} in {end.lower()}" for end, count in Counter(closest["test_end"]).most_common())
    message = (
        f"Predicted by {fit.served} trained on {len(fit.train)} FLEX tests in microgravity."
        f" The {len(closest)} closest real tests ended: {endings}."
    )
    if float(closest["distance"].iloc[0]) > FAR_DISTANCE:
        message += (
            f" Caution: the closest real test is not close to these inputs (scaled distance"
            f" {closest['distance'].iloc[0]:.2f}), so this sits in a thinly tested part of the range."
        )
    return PredictResponse(
        status="ok",
        model_id=MODEL_ID,
        prediction=Prediction(
            label="yes" if yes >= 0.5 else "no",
            class_probabilities={"yes": round(yes, 3), "no": round(1 - yes, 3)},
        ),
        nearest_tests=wanted,
        message=message,
        model_version=VERSION,
    )
