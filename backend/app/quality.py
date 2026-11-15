"""The data quality view: every flagged cell with its text, and the rows that are not tests."""

from collections import Counter
from functools import lru_cache

from ignis_ml import raw

from . import store

# What each check means, in plain words. The thresholds are this project's, not NASA's.
CHECKS = {
    "non_physical": "The value is physically impossible, such as a pressure of 0 or 3400% oxygen. It is left out of every calculation.",
    "not_a_number": "A column of numbers holds text.",
    "negative_value": "A concentration below zero.",
    "after_exceeds_before": "Oxygen reads higher after the test than before it. Burning cannot add oxygen.",
    "implausible_drop": "Oxygen after the test is less than half of what it was before.",
    "fractions_do_not_sum": "The gas fractions of the atmosphere do not add up to 1.",
    "duplicate_id": "Two rows carry the same test identifier.",
    "duplicate_row": "A row repeats another row cell for cell.",
    "unrecognised_species": "A gas name that is not a real gas in these tests, such as CH5 or N3. Likely a spreadsheet fill-down error.",
}


@lru_cache(maxsize=None)
def _table(psi_id: str, file_name: str) -> dict[int, dict]:
    return {record["row"]: record for record in raw.read_raw_table(psi_id, file_name).to_dict("records")}


@lru_cache(maxsize=1)
def report() -> dict:
    names = {psi_id: entry["name"] for psi_id, entry in store.investigations().items()}
    flags = [
        {**flag, "row": int(flag["row"]), "name": names[flag["psi_id"]],
         "cell": _table(flag["psi_id"], flag["file_name"])[int(flag["row"])][flag["column"]].strip()}
        for flag in store.flags()
    ]  # fmt: skip
    not_tests = [
        {"psi_id": row["psi_id"], "name": names[row["psi_id"]], "file_name": row["file_name"],
         "row": int(row["row"]), "why": row["kind_note"]}
        for row in store.rows() if row["row_kind"] == "other"
    ]  # fmt: skip
    rows_by = Counter(row["psi_id"] for row in store.rows())
    flags_by = Counter(flag["psi_id"] for flag in flags)
    not_tests_by = Counter(row["psi_id"] for row in not_tests)
    counts = Counter(flag["check"] for flag in flags)
    return {
        "checks": [{"check": check, "count": counts[check], "meaning": meaning} for check, meaning in CHECKS.items()],
        "investigations": [
            {"psi_id": psi_id, "name": names[psi_id], "rows": rows_by[psi_id],
             "flags": flags_by[psi_id], "not_tests": not_tests_by[psi_id]}
            for psi_id in rows_by
        ],  # fmt: skip
        "flags": flags,
        "not_tests": not_tests,
    }
