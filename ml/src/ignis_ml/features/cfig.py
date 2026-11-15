"""ACME CFI-G Normal Flames (PSI-159) as typed, unit-converted features.

Only the Normal Flames table is read. The Inverse Flames table feeds oxygen
through the burner into a fuel atmosphere, so its columns mean different
things and the two do not stack.

Two columns describe the fuel. `Fuel` names the bottle ("30% butane",
"propane"), and `Xf` is the fuel mole fraction actually fed to the burner
after any further dilution. The species is taken from `Fuel` and the fraction
from `Xf`, so tests on the same species at different dilutions sit together.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from ..flags import quality_flags
from ..raw import KEY_COLUMNS, read_raw_table
from .flex import Exclusion, parse_number

PSI_ID = "PSI-159"
FILE_NAME = "PSI-159_Experimental table_CFI-G_Normal Flames.csv"
BAR_TO_KPA = 100.0

# canonical name -> column header exactly as PSI published it (note the leading space)
SOURCE_COLUMNS: dict[str, str] = {
    "fuel": "Fuel",
    "o2_mole_fraction": " XO2 before test",
    "pressure_kpa": "approx p (bar)",
    "fuel_mole_fraction": "Xf",
    "fuel_flow_mg_s": "mHC (mg/s)",
    "hot_ignition": "Hot ignition",
    "day": "Day",
}
NUMERIC = ["o2_mole_fraction", "pressure_kpa", "fuel_mole_fraction", "fuel_flow_mg_s"]


@dataclass(frozen=True)
class CfigTable:
    """`frame` is shared and cached: copy it before changing it."""

    frame: pd.DataFrame
    excluded: tuple[Exclusion, ...]
    file_name: str


def _oxygen_level(o2: float) -> str:
    """CFI-G ran near air, near 40 percent oxygen, and a few tests between."""
    return "near air" if o2 < 0.25 else "mid" if o2 < 0.34 else "high"


def setup_key(fuel: str, pressure_kpa: float, fraction: float, flow: float, o2: float) -> str:
    """Tests that share fuel, pressure level, fuel fraction, fuel flow and oxygen
    level are repeats of one setup. Oxygen is a level, not a value, because it
    drifts down a little from one run to the next as the chamber is reused."""
    return f"{fuel}|{pressure_kpa:.0f} kPa|Xf {fraction:.3f}|{flow:.2f} mg/s|O2 {_oxygen_level(o2)}"


@lru_cache(maxsize=1)
def load_cfig() -> CfigTable:
    raw = read_raw_table(PSI_ID, FILE_NAME)
    typed = raw[KEY_COLUMNS].copy()
    typed["day"] = raw[SOURCE_COLUMNS["day"]].str.strip().astype(int)
    typed["bottle"] = raw[SOURCE_COLUMNS["fuel"]].str.strip().str.lower()
    typed["fuel"] = typed["bottle"].str.split().str[-1]
    for name in NUMERIC:
        typed[name] = [parse_number(cell)[0] for cell in raw[SOURCE_COLUMNS[name]]]
    typed["pressure_kpa"] = typed["pressure_kpa"] * BAR_TO_KPA

    ignition = raw[SOURCE_COLUMNS["hot_ignition"]].str.strip().str.lower()
    unexpected = sorted(set(ignition) - {"yes", "no"})
    if unexpected:
        raise ValueError(f"'Hot ignition' holds values other than Yes and No: {unexpected}")
    typed["hot_ignition"] = ignition

    flagged: dict[int, list[str]] = {}
    for flag in quality_flags(PSI_ID, FILE_NAME):
        flagged.setdefault(flag.row, []).append(f"{flag.check} in '{flag.column}': {flag.detail}")

    excluded: list[Exclusion] = []
    keep = pd.Series(True, index=typed.index)
    for index, row in typed.iterrows():
        if int(row["row"]) in flagged:
            reason = "flagged by ingest, " + "; ".join(flagged[int(row["row"])])
        elif not row["fuel_flow_mg_s"] > 0:
            reason = "no fuel was flowing (mHC is 0), so it was not an ignition attempt"
        elif typed.loc[index, NUMERIC].isna().any():
            reason = "an input is not stated"
        else:
            continue
        keep[index] = False
        excluded.append(Exclusion(int(row["row"]), reason))

    typed = typed.loc[keep].reset_index(drop=True)
    typed["setup"] = [
        setup_key(r.fuel, r.pressure_kpa, r.fuel_mole_fraction, r.fuel_flow_mg_s, r.o2_mole_fraction)
        for r in typed.itertuples()
    ]
    return CfigTable(frame=typed, excluded=tuple(excluded), file_name=FILE_NAME)
