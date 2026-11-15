import csv
import io

import pytest

from app.ingest import build, check
from app.ingest.build import FLAG_COLUMNS
from app.ingest.cells import read_numbers, read_o2_percent_in_text
from ignis_ml import raw

FLEX = "PSI-69_Experimental table_FLEX.csv"
CFIG_INVERSE = "PSI-159_Experimental table_CFI-G_Inverse Flames.csv"


@pytest.mark.parametrize(
    "text,units,form,approximate,values",
    [
        ("0.21", (), "single", False, [(0.21, None)]),
        ("~ 21.5", (), "single", True, [(21.5, None)]),
        ("20 cm/s", ("cm/s",), "single", False, [(20.0, None)]),
        ("1 atm ", ("atm",), "single", False, [(1.0, None)]),
        ("-0.28", (), "single", False, [(-0.28, None)]),
        ("21; 26.5; 40", (), "listed", False, [(21.0, None), (26.5, None), (40.0, None)]),
        ("0.5; 1.0; 1.5; 2.0; or 3.0 ", (), "listed", False, [(0.5, None), (1.0, None), (1.5, None), (2.0, None), (3.0, None)]),
        ("21.5 - 21.7", (), "range", False, [(21.5, 21.7)]),
        ("22.1 to 22.0", (), "range", False, [(22.0, 22.1)]),
        ("3400%", ("%",), "single", False, [(3400.0, None)]),
    ],
)  # fmt: skip
def test_cells_are_read_as_written(text, units, form, approximate, values):
    reading = read_numbers(text, units)
    assert (reading.status, reading.form, reading.approximate) == ("ok", form, approximate)
    assert list(reading.values) == values


@pytest.mark.parametrize("text,status", [("", "missing"), ("n/a", "missing"), ("–", "missing"), ("none", "missing"),
                                         ("RAMPED", "varied"), ("LOW O2", "not_a_number"), ("See Fig. 5", "not_a_number")])  # fmt: skip
def test_cells_without_a_number_are_never_guessed(text, status):
    assert read_numbers(text).status == status


def test_oxygen_is_read_from_an_atmosphere_phrase():
    reading = read_o2_percent_in_text("~30% and ~21% O2 with He")
    assert list(reading.values) == [(30.0, None), (21.0, None)] and reading.approximate
    assert read_o2_percent_in_text("air").status == "not_a_number"


@pytest.fixture(scope="module")
def out():
    return build()


def _conditions(out, psi_id, row, field, file_name=None):
    return [
        c for c in out.conditions
        if (c["psi_id"], c["row"], c["field"]) == (psi_id, row, field) and file_name in (None, c["file_name"])
    ]  # fmt: skip


def _flags(out, psi_id, row):
    return [f for f in out.flags if (f["psi_id"], f["row"]) == (psi_id, row)]


def test_every_raw_row_appears_exactly_once(out):
    keys = [(r["psi_id"], r["file_name"], r["row"]) for r in out.rows]
    assert len(keys) == len(set(keys))
    in_scope = [e for e in raw.manifest()["investigations"] if e["psi_id"] not in ("PSI-108", "PSI-181")]
    assert len(keys) == sum(table["data_rows"] for entry in in_scope for table in entry["tables"])


def test_conditions_and_flags_point_at_real_rows(out):
    keys = {(r["psi_id"], r["file_name"], r["row"]) for r in out.rows}
    assert {(c["psi_id"], c["file_name"], c["row"]) for c in out.conditions} <= keys
    assert {(f["psi_id"], f["file_name"], f["row"]) for f in out.flags} <= keys


def test_units_are_converted(out):
    # FLEX row 2: 757.7 mmHg, oxygen 0.21
    assert _conditions(out, "PSI-69", 2, "pressure_kpa")[0]["value"] == pytest.approx(101.018, abs=1e-3)
    assert _conditions(out, "PSI-69", 2, "o2_mole_fraction")[0]["value"] == 0.21
    # BASS-II row 2: 22.2 percent by volume
    assert _conditions(out, "PSI-25", 2, "o2_mole_fraction")[0]["value"] == pytest.approx(0.222)
    # CFI row 2: "1 atm"
    assert _conditions(out, "PSI-39", 2, "pressure_kpa")[0]["value"] == pytest.approx(101.325)


def test_a_non_physical_value_is_flagged_and_left_out(out):
    assert _conditions(out, "PSI-69", 115, "pressure_kpa") == []
    assert [f["check"] for f in _flags(out, "PSI-69", 115)] == ["non_physical"]
    # ACME BRE row 6 says 3400%
    assert _conditions(out, "PSI-20", 6, "o2_mole_fraction") == []
    assert [f["check"] for f in _flags(out, "PSI-20", 6)] == ["non_physical"]


def test_a_list_stays_a_list_and_is_not_widened_to_a_range(out):
    lines = _conditions(out, "PSI-20", 2, "o2_mole_fraction")
    assert [line["value"] for line in lines] == pytest.approx([0.21, 0.265, 0.40])
    assert {line["form"] for line in lines} == {"listed"}


def test_burner_oxygen_is_kept_apart_from_atmosphere_oxygen(out):
    inverse = [c for c in out.conditions if c["file_name"] == CFIG_INVERSE]
    assert "o2_mole_fraction" not in {c["field"] for c in inverse}
    assert max(c["value"] for c in inverse if c["field"] == "burner_o2_mole_fraction") == pytest.approx(0.85)


def test_a_value_from_a_note_cites_the_note(out):
    line = _conditions(out, "PSI-23", 14, "pressure_kpa")[0]
    assert (line["source_column"], line["approximate"]) == ("Notes", True)
    assert line["source_row"] != 14 and "~1 atm" in line["raw"]


def test_rows_that_are_not_tests_are_kept_but_marked(out):
    kinds = lambda psi_id: [r["row_kind"] for r in out.rows if r["psi_id"] == psi_id]  # noqa: E731
    assert kinds("PSI-98") == ["test", "test", "other", "other"]
    assert kinds("PSI-99").count("test") == 9
    assert set(kinds("PSI-20")) == {"summary"}
    assert set(kinds("PSI-142")) == {"other"}


def test_known_problem_rows_are_flagged(out):
    checks_at = lambda psi_id, row: {f["check"] for f in _flags(out, psi_id, row)}  # noqa: E731
    assert checks_at("PSI-25", 129) == {"after_exceeds_before"}  # final oxygen 40.4, initial 20.7
    assert checks_at("PSI-25", 3) == {"implausible_drop"}  # final oxygen 1.6, initial 22.2
    assert checks_at("PSI-21", 3) == {"unrecognised_species"}  # "40% CH5"
    assert checks_at("PSI-22", 30) == {"duplicate_row"}
    assert checks_at("PSI-69", 71) == checks_at("PSI-69", 74) == {"duplicate_id"}
    assert checks_at("PSI-69", 2) == set()


def test_flag_file_keeps_the_contract_format(out):
    header = next(csv.reader(io.StringIO(out.files()["quality_flags.csv"])))
    assert header == FLAG_COLUMNS == ["psi_id", "file_name", "row", "column", "check", "detail"]


def test_investigations_cover_the_whole_search_result(out):
    by_id = {i["psi_id"]: i for i in out.investigations}
    assert len(by_id) == 26 and sum(i["in_scope"] for i in by_id.values()) == 24
    flex = by_id["PSI-69"]
    assert flex["doi"] and flex["gravity_g"] == 0.0 and flex["fuel_class"] == "droplet"
    assert flex["condition_ranges"]["o2_mole_fraction"] == {"min": 0.12, "max": 0.34}
    assert by_id["PSI-60"]["gravity_g"] is None and by_id["PSI-60"]["tables"] == []


def test_committed_files_match_the_code(out):
    assert check(out) == [], "data/processed/ is stale. Run: python -m app.ingest"
