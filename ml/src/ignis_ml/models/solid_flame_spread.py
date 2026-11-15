"""Nearest real solid-fuel tests for a material and an oxygen level.

A matcher, not a trained model. BASS-II, by far the largest solid table, has
no column saying whether a sample burned, so there is nothing to train on.
What can be done honestly is to show the real tests of the same material
closest in oxygen, with their cells as NASA published them, and to refuse
when the request is outside what was tested for that material.

It never returns a burned or did-not-burn answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ..contract import (
    FeatureSpec,
    ModelCard,
    Prediction,
    PredictRequest,
    PredictResponse,
    TableRef,
    TestRef,
)
from ..features.solids import LeftOut, load_solids
from ..guards import RANGE_MARGIN, build_specs, check_inputs
from ..nearest import cite, rank_tests
from ..raw import KEY_COLUMNS, investigation, read_raw_table

MODEL_ID = "solid_flame_spread"
VERSION = "0.1.0"
CATEGORICAL = ["material"]
NUMERIC = ["o2_mole_fraction"]


@dataclass(frozen=True)
class Matcher:
    tests: pd.DataFrame
    raw: dict[tuple[str, str], pd.DataFrame]  # (psi_id, file_name) -> raw table
    specs: list[FeatureSpec]
    scales: dict[str, float]
    tables: list[TableRef]
    left_out: tuple[LeftOut, ...]


@lru_cache(maxsize=1)
def matcher() -> Matcher:
    solids = load_solids()
    specs = build_specs(
        solids.frame,
        categorical={"material": "material cell of each table"},
        numeric={"o2_mole_fraction": ("mole fraction", "oxygen cell of each table")},
    )
    return Matcher(
        tests=solids.frame,
        raw={(psi_id, file_name): read_raw_table(psi_id, file_name) for psi_id, file_name, _, _ in solids.tables},
        specs=specs,
        scales={spec.name: spec.tested_max - spec.tested_min for spec in specs if spec.kind == "numeric"},
        tables=[
            TableRef(psi_id=psi_id, file_name=file_name, doi=investigation(psi_id)["doi"], n_rows=n)
            for psi_id, file_name, _, n in solids.tables
        ],
        left_out=solids.left_out,
    )


def _notes(match: Matcher) -> str:
    grouped: dict[tuple[str, str], list[int]] = {}
    for item in match.left_out:
        grouped.setdefault((item.acronym, item.reason), []).append(item.row)
    left_out = "; ".join(
        f"{acronym} {'row' if len(rows) == 1 else 'rows'} {', '.join(map(str, rows))} ({reason})"
        for (acronym, reason), rows in grouped.items()
    )
    return " ".join(
        [
            "A matcher, not a trained model: it returns the real tests of the chosen material closest in"
            " oxygen and never says whether a sample would burn. BASS-II records no outcome, so there is"
            " nothing to train or evaluate.",
            f"Searches {sum(table.n_rows for table in match.tables)} tests, all in microgravity."
            f" Left out: {left_out or 'nothing'}.",
            "BASS (PSI-26) states no oxygen level and is not searched.",
            "A material family is taken only from a word in the cell. A cell that names a shape and no"
            " material (for example a rod) is filed under that shape.",
            "A cell that gives a short oxygen range is matched at its middle. Airflow is not an input:"
            " BASS-II records fan settings, not a speed.",
            f"Oxygen is checked against the range tested for the chosen material. A value up to"
            f" {RANGE_MARGIN:.0%} of the tested width beyond either end is accepted.",
        ]
    )


def card() -> ModelCard:
    match = matcher()
    return ModelCard(
        model_id=MODEL_ID,
        title="Nearest solid-fuel tests",
        status="available",
        fuel_class="solid",
        task="matcher",
        target="nearest real tests",
        features=match.specs,
        trained_on=match.tables,
        version=VERSION,
        notes=_notes(match),
    )


def _nearest(match: Matcher, values: dict[str, float | str], n: int) -> list[TestRef]:
    if n <= 0:
        return []
    ranked = rank_tests(match.tests, values, match.scales, match=CATEGORICAL).head(n)
    cited: list[TestRef] = []
    for (psi_id, file_name), group in ranked.groupby(["psi_id", "file_name"], sort=False):
        raw = match.raw[(psi_id, file_name)]
        columns = [column for column in raw.columns if column not in KEY_COLUMNS]
        cited += cite(group, raw, columns, doi=investigation(psi_id)["doi"])
    return sorted(cited, key=lambda test: (test.distance, test.psi_id, test.row))


def predict(request: PredictRequest) -> PredictResponse:
    match = matcher()
    checked = check_inputs(match.specs, request.inputs, match.tests)

    if checked.errors:
        return PredictResponse(
            status="invalid_input",
            model_id=MODEL_ID,
            message="; ".join(checked.errors) + ".",
            model_version=VERSION,
        )

    if checked.violations:
        untested_material = any(violation.feature in CATEGORICAL for violation in checked.violations)
        message = "Outside what NASA tested for solids in BASS-II and Saffire. This is a gap in the data." + (
            "" if untested_material else " The closest tests that do exist are listed."
        )
        return PredictResponse(
            status="withheld",
            model_id=MODEL_ID,
            out_of_range=list(checked.violations),
            nearest_tests=[] if untested_material else _nearest(match, checked.values, request.n_nearest),
            message=" ".join([message, *checked.notes]),
            model_version=VERSION,
        )

    return PredictResponse(
        status="ok",
        model_id=MODEL_ID,
        prediction=Prediction(),
        nearest_tests=_nearest(match, checked.values, request.n_nearest),
        message=(
            "A matcher, not a prediction: these are the real tests of this material closest in oxygen."
            " No outcome is predicted, because BASS-II records none."
        ),
        model_version=VERSION,
    )
