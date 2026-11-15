"""One spec per PSI experimental table: where each condition is written.

Adding a table means adding a spec here. Nothing else in ingest names a
column. Every mapping below was checked against the table's own header and
values; where a header is ambiguous the `note` says how it was read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import checks
from .cells import Reading, read_numbers, read_o2_percent_in_text

ATM_TO_KPA = 101.325
MMHG_TO_KPA = 101.325 / 760
BAR_TO_KPA = 100.0
PERCENT = 0.01

# Canonical fields, in output order. Units follow docs/CONTRACTS.md.
FIELDS = (
    "o2_mole_fraction",  # oxygen in the atmosphere around the flame
    "burner_o2_mole_fraction",  # oxygen in the gas fed through the burner (inverse flames)
    "pressure_kpa",
    "flow_cm_s",
    "n2_mole_fraction",
    "co2_mole_fraction",
    "he_mole_fraction",
)


@dataclass(frozen=True)
class Source:
    """A condition read from a column, or stated once in a table note."""

    column: str
    scale: float = 1.0  # multiply the cell's number by this to get canonical units
    source_unit: str = ""
    units: tuple[str, ...] = ()  # unit words that may appear inside the cell
    reader: Callable[[str, tuple[str, ...]], Reading] = read_numbers
    approximate: bool = False  # the header itself says the values are approximate
    note: str = ""
    # Set for a value stated in a note that applies to every row of the table.
    note_contains: str = ""
    note_value: float | None = None


# A row is a `test`, a `summary` of several tests, or `other` (not a test).
Kind = tuple[str, str]  # (kind, why)


def _all_tests(row: dict) -> Kind:
    return "test", ""


def _summary(why: str) -> Callable[[dict], Kind]:
    return lambda row: ("summary", why)


def _test_if_filled(column: str, otherwise: Kind) -> Callable[[dict], Kind]:
    return lambda row: ("test", "") if row[column].strip() else otherwise


@dataclass(frozen=True)
class Table:
    psi_id: str
    fuel_class: str  # solid | droplet | gas | smoke | dust
    fuel_column: str | None = None
    file_name: str | None = None  # only needed when the investigation has two tables
    fuel_constant: str = ""
    fuel_note: str = ""
    fields: dict[str, Source] = field(default_factory=dict)
    kind: Callable[[dict], Kind] = _all_tests
    tests_in_row: str | None = None  # column that counts the tests a summary row covers
    checks: tuple[Callable, ...] = ()


def _saffire_kind(row: dict) -> Kind:
    if row["Air Flow (cm/s)"].strip():
        return "test", ""
    first = next((cell for cell in row.values() if isinstance(cell, str) and cell.startswith("Note ")), "")
    return ("other", "table footnote") if first else ("other", "flow visualisation files, not a burn")


TABLES: tuple[Table, ...] = (
    Table(
        "PSI-10", "gas", "Fuel",
        file_name="PSI-10_Experimental table_Flame Design_Normal Flame.csv",
        fields={
            "o2_mole_fraction": Source("XO2 (init)", source_unit="mole fraction"),
            "pressure_kpa": Source("pinit (atm)", ATM_TO_KPA, "atm"),
        },
        checks=(checks.after_not_above_before("XO2 (init)", "XO2 (final)", max_rise=0.005),),
    ),
    Table(
        "PSI-10", "gas",
        file_name="PSI-10_Experimental table_Flame Design_Inverse Flame.csv",
        fuel_constant="C2H4",
        fuel_note="The table has no fuel column. The fuel is named in the header 'XC2H4 initial'.",
        fields={
            "burner_o2_mole_fraction": Source(
                "XO2", source_unit="mole fraction",
                note="Inverse flame: oxygen flows from the burner into a fuel atmosphere.",
            ),
            "pressure_kpa": Source("pinit (atm)", ATM_TO_KPA, "atm"),
        },
    ),
    Table(
        "PSI-20", "gas", "Fuel Bottle",
        fields={
            "o2_mole_fraction": Source(
                "Oxygen Conc (percent)", PERCENT, "percent", units=("%",), approximate=True,
                note="Each row lists the approximate oxygen levels of the flames that ignited that day.",
            ),
        },
        kind=_summary("one test day"),
        tests_in_row="Flames Ignited",
    ),
    Table(
        "PSI-21", "gas", "Fuel Bottle",
        kind=_summary("one test day"),
        tests_in_row="Flames ignited",
        checks=(checks.known_species("Fuel Bottle"),),
    ),
    Table(
        "PSI-22", "gas", "Fuel Bottle",
        kind=lambda row: ("summary", "one test day") if row["Test Day"].strip()
        else ("other", "continues the test day above with one more fuel concentration"),
        tests_in_row="Flames Ignited",
        checks=(checks.no_repeated_rows(),),
    ),
    Table(
        "PSI-23", "gas", "Fuel Bottle",
        fields={
            "o2_mole_fraction": Source("Atmosphere*", PERCENT, "percent", reader=read_o2_percent_in_text),
            "pressure_kpa": Source(
                "Notes", ATM_TO_KPA, "atm", approximate=True,
                note_contains="~1 atm", note_value=1.0,
                note="Stated once for the whole table, in a note.",
            ),
        },
        kind=_summary("one test day"),
        tests_in_row="Flames Ignited*",
        checks=(checks.known_species("Atmosphere*"), checks.known_species("Fuel Bottle")),
    ),
    Table(
        "PSI-25", "solid", "Fuel Sample Material",
        fields={
            "o2_mole_fraction": Source("Calibrated  initial O2 % by vol ", PERCENT, "percent by volume"),
            "co2_mole_fraction": Source("Initial CO2 % by vol", PERCENT, "percent by volume"),
        },
        checks=(
            checks.after_not_above_before(
                "Calibrated  initial O2 % by vol ", "Calibrated final O2 % by vol", max_rise=0.5, min_ratio=0.5
            ),
            checks.not_negative("Initial CO (ppm)"),
            checks.not_negative("Final CO (ppm)"),
        ),
    ),
    Table(
        "PSI-26", "solid", "Fuel Sample Material",
        kind=_test_if_filled("Test #", ("other", "no test number: a maintenance entry, not a burn")),
    ),
    Table(
        "PSI-39", "droplet", "Fuel ",
        fields={
            "o2_mole_fraction": Source("Oxygen", source_unit="mole fraction"),
            "pressure_kpa": Source("Pressure", ATM_TO_KPA, "atm", units=("atm",)),
            "n2_mole_fraction": Source("Nitrogen", source_unit="mole fraction"),
            "he_mole_fraction": Source("Helium", source_unit="mole fraction"),
        },
    ),
    Table("PSI-47", "dust", "Sample Material", kind=_summary("one measurement session")),
    Table(
        "PSI-68", "droplet", "Sample (Fuel Type)",
        fields={
            "o2_mole_fraction": Source("Oxygen Mole Fraction", source_unit="mole fraction"),
            "pressure_kpa": Source("Ambient Pressure (atm)", ATM_TO_KPA, "atm"),
            "flow_cm_s": Source("Flow Velocity (cm/s)", source_unit="cm/s"),
        },
        kind=_summary("the test matrix for one fuel; single tests are not listed"),
    ),
    Table(
        "PSI-69", "droplet", "Fuel",
        fields={
            "o2_mole_fraction": Source(
                "O initial ambient composition; mole fraction", source_unit="mole fraction",
                note="The header lost its subscript. Read as O2.",
            ),
            "pressure_kpa": Source("Ambient pressure; mmHg", MMHG_TO_KPA, "mmHg"),
            "n2_mole_fraction": Source(
                "N initial ambient composition; mole fraction", source_unit="mole fraction",
                note="The header lost its subscript. Read as N2.",
            ),
            "co2_mole_fraction": Source(
                "CO initial ambient composition; mole fraction", source_unit="mole fraction",
                note="The header lost its subscript. Read as CO2, not carbon monoxide: "
                "values reach 0.7 and FLEX diluted with CO2 and helium.",
            ),
            "he_mole_fraction": Source("He initial ambient composition; mole fraction", source_unit="mole fraction"),
        },
        checks=(checks.unique("FLEX Identifier"),),
    ),
    Table(
        "PSI-98", "solid", "Material",
        fields={
            "o2_mole_fraction": Source("Percent O2", PERCENT, "percent"),
            "flow_cm_s": Source("Air Flow (cm/s)", source_unit="cm/s"),
        },
        kind=_saffire_kind,
    ),
    Table(
        "PSI-99", "solid", "Material",
        fields={
            "o2_mole_fraction": Source("Percent O2 (Note 1)", PERCENT, "percent"),
            "flow_cm_s": Source("Air Flow (cm/s)", source_unit="cm/s", units=("cm/s",)),
        },
        kind=_saffire_kind,
    ),
    Table(
        "PSI-100", "solid", "Material",
        fields={"flow_cm_s": Source("Air Flow ", source_unit="cm/s", units=("cm/s",))},
    ),
    Table(
        "PSI-101", "smoke", "Sample Type",
        fields={"flow_cm_s": Source("Inlet velocity (cm/s)", source_unit="cm/s")},
    ),
    Table(
        "PSI-102", "smoke", "Sample Material  ",
        fields={"flow_cm_s": Source("Air Flow (cm/s)", source_unit="cm/s")},
        kind=_test_if_filled(
            "Air Flow (cm/s)", ("summary", "one material, run under the conditions of samples 1 to 4")
        ),
    ),
    Table("PSI-106", "gas", "Fuel Type", kind=_summary("one test day")),
    Table(
        "PSI-107", "gas", "Fuel",
        fields={
            "flow_cm_s": Source("Air Rate (cm/s)", source_unit="cm/s", note="Speed of the co-flowing air."),
        },
    ),
    Table(
        "PSI-142", "gas", None,
        kind=lambda row: ("other", "points to a figure in a publication, not a test"),
    ),
    Table(
        "PSI-159", "gas", "Fuel",
        file_name="PSI-159_Experimental table_CFI-G_Normal Flames.csv",
        fields={
            "o2_mole_fraction": Source(" XO2 before test", source_unit="mole fraction"),
            "pressure_kpa": Source("approx p (bar)", BAR_TO_KPA, "bar", approximate=True),
        },
        checks=(checks.after_not_above_before(" XO2 before test", "XO2  after test", max_rise=0.005),),
    ),
    Table(
        "PSI-159", "gas", "Fuel",
        file_name="PSI-159_Experimental table_CFI-G_Inverse Flames.csv",
        fields={
            "burner_o2_mole_fraction": Source(
                "XO2", source_unit="mole fraction",
                note="Inverse flame: oxygen flows from the burner into a fuel atmosphere.",
            ),
            "pressure_kpa": Source("approx p (bar)", BAR_TO_KPA, "bar", approximate=True),
        },
    ),
)  # fmt: skip

# In the search results but not combustion.
OUT_OF_SCOPE = {
    "PSI-108": "Surface tension driven convection in a fluid. No flame.",
    "PSI-181": "Solder microstructure. No flame.",
}
