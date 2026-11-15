"""Read the PSI snapshot in data/raw/ with one agreed row numbering.

Every part of the project keys a test on (psi_id, file_name, row), so every
part must number rows the same way.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

KEY_COLUMNS = ["psi_id", "file_name", "row"]


def repo_root() -> Path:
    """The folder that holds data/. Set IGNIS_REPO_ROOT if the package is not
    installed in editable mode from a checkout (for example on Colab)."""
    override = os.environ.get("IGNIS_REPO_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def manifest() -> dict:
    path = repo_root() / "data" / "raw" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def investigation(psi_id: str) -> dict:
    for entry in manifest()["investigations"]:
        if entry["psi_id"] == psi_id:
            return entry
    raise KeyError(f"{psi_id} is not in data/raw/manifest.json")


def table_entry(psi_id: str, file_name: str | None = None) -> dict:
    tables = investigation(psi_id)["tables"]
    if file_name is None:
        if len(tables) != 1:
            names = [t["file_name"] for t in tables]
            raise ValueError(f"{psi_id} has {len(tables)} tables, pass file_name: {names}")
        return tables[0]
    for table in tables:
        if table["file_name"] == file_name:
            return table
    raise KeyError(f"{psi_id} has no table named {file_name!r}")


def read_raw_table(psi_id: str, file_name: str | None = None, *, verify: bool = True) -> pd.DataFrame:
    """One PSI experimental table, untouched, plus the three key columns.

    Every cell is the text PSI published: nothing is converted to a number and
    nothing is turned into NaN, so "n/a", "none", "~ 21.5" and an empty cell
    all stay distinguishable. Parsing is the caller's job.

    `row` is the spreadsheet row number (header = 1, first test = 2). Rows
    that are completely empty are dropped after numbering, so the numbers of
    the remaining rows still match the file.
    """
    entry = table_entry(psi_id, file_name)
    path = repo_root() / entry["path"]
    content = path.read_bytes()
    if verify and hashlib.sha256(content).hexdigest() != entry["sha256"]:
        raise ValueError(
            f"{entry['path']} does not match its sha256 in the manifest. "
            "It was edited by hand or its line endings were converted; "
            "restore it with git or re-run scripts/fetch_psi.py."
        )

    rows = list(csv.reader(content.decode(entry["encoding"]).splitlines(keepends=True)))
    header, body = rows[0], rows[1:]
    frame = pd.DataFrame(body, columns=header, dtype=str)
    frame.insert(0, "row", range(2, len(body) + 2))
    frame.insert(0, "file_name", entry["file_name"])
    frame.insert(0, "psi_id", psi_id)

    blank = frame[header].apply(lambda column: column.str.strip() == "").all(axis=1)
    return frame.loc[~blank].reset_index(drop=True)
