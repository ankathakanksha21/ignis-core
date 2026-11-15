"""Solid-fuel tests from BASS-II and Saffire as one typed table.

The solid tables write materials and oxygen as free text ("~ 21.5",
"22.1 to 22.0", "1 cm wide PMMA 2 mm thick"). Ingest already parses them for
the dashboard, so this module reads the result, data/processed/rows.csv,
rather than parsing the same cells a second way. That file is keyed by
(psi_id, file_name, row) like everything else, so citations still point at
the raw tables.

Only tests that state both a material and an oxygen level can be matched.
BASS (PSI-26) states no oxygen at all and is not searched.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ..flags import quality_flags
from ..raw import repo_root

ROWS_PATH = ("data", "processed", "rows.csv")
SEARCHED = ("PSI-25", "PSI-98", "PSI-99", "PSI-100")  # BASS-II, Saffire-I, -II, -III

# A material family is assigned only from a word in the cell. A cell that
# names a shape and no material ("1/4 inch black rod") keeps the shape as its
# family, because the table does not say what the rod is made of.
_MATERIAL_WORDS: dict[str, tuple[str, ...]] = {
    "pmma": ("pmma",),
    "sibal": ("sibal", "cotton"),
    "nomex": ("nomex",),
    "silicone": ("silicone",),
    "wax": ("wax", "candle"),
}
_SHAPE_WORDS: dict[str, tuple[str, ...]] = {"rod": ("rod",), "film": ("film",)}
OTHER = "other"


@dataclass(frozen=True)
class LeftOut:
    acronym: str
    row: int
    reason: str


@dataclass(frozen=True)
class SolidTable:
    """`frame` is shared and cached: copy it before changing it. A test whose
    cell names two materials has one line per material."""

    frame: pd.DataFrame
    left_out: tuple[LeftOut, ...]
    tables: tuple[tuple[str, str, str, int], ...]  # (psi_id, file_name, acronym, tests kept)


def material_families(text: str) -> list[str]:
    """The families a material cell names, e.g. 'PMMA & Nomex' -> ['pmma', 'nomex']."""
    cell = text.lower()
    named = [family for family, words in _MATERIAL_WORDS.items() if any(word in cell for word in words)]
    if named:
        return named
    shapes = [family for family, words in _SHAPE_WORDS.items() if any(word in cell for word in words)]
    return shapes or [OTHER]


@lru_cache(maxsize=1)
def load_solids() -> SolidTable:
    with repo_root().joinpath(*ROWS_PATH).open(encoding="utf-8", newline="") as handle:
        rows = [line for line in csv.DictReader(handle) if line["psi_id"] in SEARCHED]

    flagged = {
        (psi_id, flag.row)
        for psi_id, file_name in {(line["psi_id"], line["file_name"]) for line in rows}
        for flag in quality_flags(psi_id, file_name)
    }

    kept: list[dict] = []
    left_out: list[LeftOut] = []
    counts: dict[tuple[str, str, str], int] = {}
    for line in rows:
        if line["row_kind"] != "test":
            continue  # footnotes and file listings are not tests
        psi_id, row, acronym = line["psi_id"], int(line["row"]), line["acronym"]
        counts.setdefault((psi_id, line["file_name"], acronym), 0)
        if (psi_id, row) in flagged:
            reason = "flagged by ingest"
        elif not line["fuel"].strip():
            reason = "material not stated"
        elif not line["o2_mole_fraction_min"]:
            reason = "oxygen not stated"
        else:
            reason = None
        if reason:
            left_out.append(LeftOut(acronym, row, reason))
            continue
        counts[(psi_id, line["file_name"], acronym)] += 1
        low, high = float(line["o2_mole_fraction_min"]), float(line["o2_mole_fraction_max"])
        for family in material_families(line["fuel"]):
            kept.append(
                {
                    "psi_id": psi_id,
                    "file_name": line["file_name"],
                    "row": row,
                    "acronym": acronym,
                    "material": family,
                    "material_text": line["fuel"].strip(),
                    # A cell that gives a short range ("22.1 to 22.0") is matched at its middle.
                    "o2_mole_fraction": round((low + high) / 2, 6),
                }
            )

    return SolidTable(
        frame=pd.DataFrame(kept),
        left_out=tuple(left_out),
        tables=tuple((psi_id, file_name, acronym, n) for (psi_id, file_name, acronym), n in counts.items() if n),
    )
