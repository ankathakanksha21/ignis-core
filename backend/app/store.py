"""The processed data, loaded once."""

import csv
import json
from functools import lru_cache

from ignis_ml import raw

PROCESSED = raw.repo_root() / "data" / "processed"


def _csv(name: str) -> list[dict]:
    with open(PROCESSED / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def investigations() -> dict[str, dict]:
    data = json.loads((PROCESSED / "investigations.json").read_text(encoding="utf-8"))
    return {entry["psi_id"]: entry for entry in data["investigations"]}


@lru_cache(maxsize=1)
def rows() -> list[dict]:
    return _csv("rows.csv")


@lru_cache(maxsize=1)
def flags() -> list[dict]:
    return _csv("quality_flags.csv")


@lru_cache(maxsize=1)
def conditions() -> list[dict]:
    return _csv("conditions.csv")


@lru_cache(maxsize=None)
def columns(psi_id: str, file_name: str) -> list[dict]:
    """Each column of a raw table: how many test rows fill it and how many
    different values it takes. More than one value means it varied."""
    not_tests = {
        int(r["row"]) for r in rows()
        if (r["psi_id"], r["file_name"], r["row_kind"]) == (psi_id, file_name, "other")
    }  # fmt: skip
    frame = raw.read_raw_table(psi_id, file_name)
    frame = frame[~frame["row"].isin(not_tests)]
    result = []
    for name in frame.columns[3:]:
        filled = frame[name].str.strip()
        filled = filled[filled != ""]
        result.append({"name": name.strip(), "filled": len(filled), "distinct": int(filled.nunique())})
    return result
