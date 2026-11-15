"""Ingest's quality flags, read from data/processed/quality_flags.csv.

The dashboard side writes that file (format in docs/CONTRACTS.md), one line
per suspicious cell. The models leave flagged rows out of training, so both
halves agree on which rows are bad. Before ingest has run the file does not
exist, and this returns nothing.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from .raw import repo_root

FLAGS_PATH = ("data", "processed", "quality_flags.csv")


@dataclass(frozen=True)
class Flag:
    row: int
    column: str
    check: str
    detail: str


def quality_flags(psi_id: str, file_name: str) -> list[Flag]:
    """Every flag ingest raised on one table, in file order."""
    path = repo_root().joinpath(*FLAGS_PATH)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            Flag(int(line["row"]), line["column"], line["check"], line["detail"])
            for line in csv.DictReader(handle)
            if line["psi_id"] == psi_id and line["file_name"] == file_name
        ]
