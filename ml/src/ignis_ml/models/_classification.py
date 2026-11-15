"""Scoring shared by the yes-or-no models.

Every candidate is scored out of fold with whole groups held out, beside
always answering with the training share of "yes" (the majority class once
it is turned into a label).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

CLASSES = ["yes", "no"]
BASELINE = "majority class"


@dataclass(frozen=True)
class Scores:
    accuracy: float
    balanced_accuracy: float
    macro_f1: float


def probability_of_yes(model: Pipeline, inputs: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(inputs)[:, list(model.classes_).index("yes")]


def score(measured: np.ndarray, yes: np.ndarray) -> Scores:
    predicted = np.where(yes >= 0.5, "yes", "no")
    return Scores(
        accuracy=float(accuracy_score(measured, predicted)),
        balanced_accuracy=float(balanced_accuracy_score(measured, predicted)),
        macro_f1=float(f1_score(measured, predicted, average="macro", labels=CLASSES, zero_division=0)),
    )


def cross_validate(
    train: pd.DataFrame,
    features: Sequence[str],
    target: str,
    group_column: str,
    candidates: Mapping[str, Callable[[], Pipeline]],
    n_folds: int = 5,
) -> dict[str, Scores]:
    """Out-of-fold scores for every candidate and for the baseline."""
    inputs, labels = train[list(features)], train[target].to_numpy()
    yes = {name: np.zeros(len(train)) for name in [*candidates, BASELINE]}
    for fit_rows, held_out in GroupKFold(n_splits=n_folds).split(inputs, labels, train[group_column]):
        for name, make in candidates.items():
            model = make().fit(inputs.iloc[fit_rows], labels[fit_rows])
            yes[name][held_out] = probability_of_yes(model, inputs.iloc[held_out])
        yes[BASELINE][held_out] = float(np.mean(labels[fit_rows] == "yes"))
    return {name: score(labels, values) for name, values in yes.items()}
