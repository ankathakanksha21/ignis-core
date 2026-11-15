"""The real tests closest to a query, as citations.

Distance is Euclidean over the numeric inputs, each divided by a scale (the
model passes the width of its tested range), so 1.0 means "a whole tested
range away on one input". Ties are broken by row number, so the result is
deterministic. The cell values returned are copied from the raw table, not
from the converted features.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .contract import TestRef


def nearest_tests(
    pool: pd.DataFrame,
    raw: pd.DataFrame,
    query: Mapping[str, float | str],
    scales: Mapping[str, float],
    n: int,
    value_columns: Sequence[str],
    match: Sequence[str] = (),
    doi: str | None = None,
) -> list[TestRef]:
    """`pool` is a typed feature table with the key columns; `raw` is the table
    it was built from. Rows must equal the query on every `match` column."""
    if n <= 0:
        return []
    for name in match:
        pool = pool[pool[name] == query[name]]
    if pool.empty:
        return []

    squared = np.zeros(len(pool))
    for name, scale in scales.items():
        squared += ((pool[name].to_numpy(dtype=float) - float(query[name])) / (scale or 1.0)) ** 2
    ranked = pool.assign(distance=np.sqrt(squared)).sort_values(["distance", "row"]).head(n)

    cells = raw.set_index("row")
    return [
        TestRef(
            psi_id=test.psi_id,
            file_name=test.file_name,
            row=int(test.row),
            doi=doi,
            distance=round(float(test.distance), 4),
            values={column: str(cells.at[test.row, column]) for column in value_columns},
        )
        for test in ranked.itertuples()
    ]
