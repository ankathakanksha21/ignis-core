"""The PSI snapshot is intact and rows are numbered the agreed way."""

import hashlib

import pytest

from ignis_ml import raw

ALL_TABLES = [
    (entry["psi_id"], table["file_name"])
    for entry in raw.manifest()["investigations"]
    for table in entry["tables"]
]


@pytest.mark.parametrize("psi_id,file_name", ALL_TABLES)
def test_table_matches_manifest(psi_id, file_name):
    entry = raw.table_entry(psi_id, file_name)
    content = (raw.repo_root() / entry["path"]).read_bytes()
    assert hashlib.sha256(content).hexdigest() == entry["sha256"]

    frame = raw.read_raw_table(psi_id, file_name)
    assert len(frame) == entry["data_rows"]
    assert list(frame.columns[:3]) == raw.KEY_COLUMNS
    assert frame["row"].is_unique and frame["row"].min() >= 2


def test_row_numbers_are_spreadsheet_rows():
    flex = raw.read_raw_table("PSI-69")
    first = flex.iloc[0]
    assert first["row"] == 2
    assert first["FLEX Test #"] == "1" and first["Fuel"] == "Methanol"
    assert len(flex) == 274


def test_blank_rows_are_dropped_without_renumbering():
    inverse = raw.read_raw_table("PSI-159", "PSI-159_Experimental table_CFI-G_Inverse Flames.csv")
    entry = raw.table_entry("PSI-159", "PSI-159_Experimental table_CFI-G_Inverse Flames.csv")
    assert entry["blank_rows"] > 0
    assert len(inverse) == entry["data_rows"]
    assert inverse["row"].max() <= entry["rows"]


def test_cells_stay_as_published_text():
    saffire = raw.read_raw_table("PSI-99")
    assert saffire["Percent O2 (Note 1)"].iloc[0] == "~ 21.5"


def test_two_table_investigations_need_a_file_name():
    with pytest.raises(ValueError):
        raw.read_raw_table("PSI-159")
