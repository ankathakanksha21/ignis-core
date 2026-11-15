"""Heptane droplet tests from a 1997 Spacelab experiment, read from ml/data/external/.

They come from a NASA report, not from PSI, and they are never used for
training. They are an outside check: an experiment the FLEX models have not
seen, run on different hardware. ml/data/external/README.md gives the source
and how the table was copied and verified.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .raw import repo_root

REPORT = "NASA/TM-2003-212553"
REPORT_URL = "https://ntrs.nasa.gov/citations/20040000941"
PATH = ("ml", "data", "external", "NASA-TM-2003-212553_heptane_droplets.csv")

BAR_TO_KPA = 100.0
AIR_O2 = 0.21  # the report says "Spacelab cabin air" and gives no percentage
CABIN_BAR = 1.00  # Table 2 gives no pressure; the same cabin air is 1.00 bar in Table 1


def _number(cell: str) -> float | None:
    try:
        return float(cell)
    except ValueError:
        return None  # a footnote letter, or an approximate value such as "1.18 ± 0.25"


@lru_cache(maxsize=1)
def load_outside_tests() -> pd.DataFrame:
    """One typed row per test that states an exact diameter and an overall
    burning rate, in the same units and input names as the FLEX features."""
    table = pd.read_csv(repo_root().joinpath(*PATH), dtype=str, keep_default_na=False)
    rows = []
    for test in table.itertuples():
        diameter, rate = _number(test.initial_diameter_mm), _number(test.k_overall_mm2_s)
        if diameter is None or rate is None:
            continue
        in_air = test.oxygen == "Air"
        oxygen = AIR_O2 if in_air else float(test.oxygen) / 100
        rows.append(
            {
                "experiment": test.experiment,
                "test": int(test.test),
                "report_page": int(test.report_page),
                "atmosphere": "air" if in_air else "helium-oxygen",
                "fuel": "heptane",
                "o2_mole_fraction": oxygen,
                "co2_mole_fraction": 0.0,
                "he_mole_fraction": 0.0 if in_air else round(1 - oxygen, 6),
                "pressure_kpa": float(test.pressure_bar or CABIN_BAR) * BAR_TO_KPA,
                "droplet_diameter_mm": diameter,
                "burning_rate_mm2_s": rate,
            }
        )
    return pd.DataFrame(rows)
