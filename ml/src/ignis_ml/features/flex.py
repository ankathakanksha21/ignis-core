"""FLEX (PSI-69) as typed, unit-converted features.

The raw table is text. This module converts it once, in the contract's units,
and keeps (psi_id, file_name, row) on every row so anything built on it can
cite the real test. Rows that cannot be used by any model are left out here
and recorded with the reason; rows a single model cannot use (no burning rate,
say) are that model's business.

Header quirks, from data/README.md: the subscripts were lost, so "O" is O2,
"N" is N2 and "CO" is CO2, and "Burning rate; mm" is read as mm^2/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import pandas as pd

from ..flags import quality_flags
from ..raw import KEY_COLUMNS, read_raw_table

PSI_ID = "PSI-69"
MMHG_TO_KPA = 0.1333224
ATM_KPA = 101.325

# canonical name -> column header exactly as PSI published it
SOURCE_COLUMNS: dict[str, str] = {
    "fuel": "Fuel",
    "pressure_kpa": "Ambient pressure; mmHg",
    "o2_mole_fraction": "O initial ambient composition; mole fraction",
    "n2_mole_fraction": "N initial ambient composition; mole fraction",
    "co2_mole_fraction": "CO initial ambient composition; mole fraction",
    "he_mole_fraction": "He initial ambient composition; mole fraction",
    "droplet_diameter_mm": "Droplet initial diameter; mm",
    "extinction_diameter_mm": "Visible flame extinction diameter; mm",
    "burning_rate_mm2_s": "Burning rate; mm",
    "burn_time_s": "Burn time; s",
    "test_end": "Test end",
}
NUMERIC = [name for name in SOURCE_COLUMNS if name not in ("fuel", "test_end")]
GASES = ["o2_mole_fraction", "n2_mole_fraction", "co2_mole_fraction", "he_mole_fraction"]

# Cells PSI uses for "no value": empty, a hyphen, an en dash or an em dash.
_NOT_STATED = {"", "-", "–", "—"}


@dataclass(frozen=True)
class Exclusion:
    row: int
    reason: str


@dataclass(frozen=True)
class FlexTable:
    """`frame` is shared and cached: copy it before changing it."""

    frame: pd.DataFrame
    excluded: tuple[Exclusion, ...]
    approximate: tuple[tuple[int, str], ...]  # (row, column header) of cells written like "~6"
    file_name: str


def parse_number(text: str) -> tuple[float, bool]:
    """A cell as (value, was it marked approximate). Not stated becomes NaN.

    Anything else that is not a number raises, so a new kind of odd cell in a
    refreshed snapshot is noticed instead of silently becoming NaN.
    """
    cell = text.strip()
    if cell in _NOT_STATED:
        return math.nan, False
    approximate = cell.startswith("~")
    return float(cell.lstrip("~").strip()), approximate


def _iso_date(text: str) -> str:
    """'3/5/2009' and '3/5/09' both become '2009-03-05'; anything else is kept."""
    try:
        month, day, year = (int(part) for part in text.strip().split("/"))
        return date(year + 2000 if year < 100 else year, month, day).isoformat()
    except ValueError:
        return text.strip()


def condition_key(fuel: str, pressure_kpa: float, o2: float, co2: float, he: float) -> str:
    """Tests that share fuel, pressure level and gas mixture are repeats of one condition."""
    return f"{fuel}|{pressure_kpa / ATM_KPA:.1f} atm|O2 {o2:.2f}|CO2 {co2:.2f}|He {he:.2f}"


@lru_cache(maxsize=1)
def load_flex() -> FlexTable:
    raw = read_raw_table(PSI_ID)
    typed = raw[KEY_COLUMNS].copy()
    typed["test_date"] = raw["Test Date"].map(_iso_date)
    typed["fuel"] = raw[SOURCE_COLUMNS["fuel"]].str.strip().str.lower()
    typed["test_end"] = raw[SOURCE_COLUMNS["test_end"]].str.strip()

    approximate: list[tuple[int, str]] = []
    for name in NUMERIC:
        header = SOURCE_COLUMNS[name]
        parsed = [parse_number(cell) for cell in raw[header]]
        typed[name] = [value for value, _ in parsed]
        approximate += [(row, header) for row, (_, flag) in zip(raw["row"], parsed) if flag]
    typed["pressure_kpa"] = typed["pressure_kpa"] * MMHG_TO_KPA

    # Rows ingest flagged are left out, as docs/CONTRACTS.md asks. The two
    # checks below it are this module's own and only matter for a row ingest
    # did not flag, or before ingest has run at all.
    flagged: dict[int, list[str]] = {}
    for flag in quality_flags(PSI_ID, str(raw["file_name"].iloc[0])):
        flagged.setdefault(flag.row, []).append(f"{flag.check} in '{flag.column}': {flag.detail}")

    excluded: list[Exclusion] = []
    keep = pd.Series(True, index=typed.index)
    for index, row in typed.iterrows():
        pressure_text = raw.at[index, SOURCE_COLUMNS["pressure_kpa"]].strip()
        if int(row["row"]) in flagged:
            reason = "flagged by ingest, " + "; ".join(flagged[int(row["row"])])
        elif not row["pressure_kpa"] > 0:
            reason = f"ambient pressure is {pressure_text} mmHg, which is not a real pressure"
        elif abs(sum(row[gas] for gas in GASES) - 1) > 0.03:
            reason = f"gas mole fractions add up to {sum(row[gas] for gas in GASES):.2f}, not 1"
        else:
            continue
        keep[index] = False
        excluded.append(Exclusion(int(row["row"]), reason))

    typed = typed.loc[keep].reset_index(drop=True)
    typed["condition"] = [
        condition_key(r.fuel, r.pressure_kpa, r.o2_mole_fraction, r.co2_mole_fraction, r.he_mole_fraction)
        for r in typed.itertuples()
    ]
    return FlexTable(
        frame=typed,
        excluded=tuple(excluded),
        approximate=tuple(approximate),
        file_name=str(raw["file_name"].iloc[0]),
    )
