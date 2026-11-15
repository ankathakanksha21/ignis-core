"""Run every table spec over the raw snapshot and produce the processed files.

    rows.csv             every non-empty raw row, once: test, summary or other
    conditions.csv       every condition value read from a cell, with its source
    quality_flags.csv    every suspicious cell
    investigations.json  one entry per investigation: record text, tables, ranges

The build is deterministic: same snapshot in, same bytes out. The files are
committed, and a test fails when they no longer match the code.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from ignis_ml import raw

from . import checks
from .specs import FIELDS, OUT_OF_SCOPE, TABLES, Table

PROCESSED = raw.repo_root() / "data" / "processed"

ROW_COLUMNS = [
    "psi_id", "file_name", "row", "acronym", "row_kind", "kind_note", "tests_in_row",
    "fuel_class", "fuel", "gravity_g",
    *[f"{name}_{end}" for name in FIELDS for end in ("min", "max")],
]  # fmt: skip
CONDITION_COLUMNS = [
    "psi_id", "file_name", "row", "field", "value", "value_hi", "form", "approximate",
    "source_column", "source_row", "raw",
]  # fmt: skip
FLAG_COLUMNS = ["psi_id", "file_name", "row", "column", "check", "detail"]
GAS_NAMES = {"o2_mole_fraction": "O2", "n2_mole_fraction": "N2", "co2_mole_fraction": "CO2", "he_mole_fraction": "He"}
FRACTIONS = tuple(GAS_NAMES)


@dataclass(frozen=True)
class Outputs:
    rows: list[dict]
    conditions: list[dict]
    flags: list[dict]
    investigations: list[dict]

    def files(self) -> dict[str, str]:
        return {
            "rows.csv": _csv(self.rows, ROW_COLUMNS),
            "conditions.csv": _csv(self.conditions, CONDITION_COLUMNS),
            "quality_flags.csv": _csv(self.flags, FLAG_COLUMNS),
            "investigations.json": json.dumps({"investigations": self.investigations}, indent=2, ensure_ascii=False)
            + "\n",
        }


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format(value, ".6g")
    return str(value)


def _csv(records: list[dict], columns: list[str]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    for record in records:
        writer.writerow([_cell(record.get(column)) for column in columns])
    return out.getvalue()


def _psi_number(psi_id: str) -> int:
    return int(psi_id.split("-")[1])


def _record(psi_id: str) -> dict:
    path = raw.repo_root() / raw.investigation(psi_id)["record_file"]
    return json.loads(path.read_text(encoding="utf-8"))


def _whole_number(text: str) -> int | None:
    return int(text) if text.strip().isdigit() else None


def _read_table(spec: Table, record: dict):
    """Rows, conditions and flags of one table."""
    frame = raw.read_raw_table(spec.psi_id, spec.file_name)
    file_name = frame["file_name"].iloc[0]
    key = {"psi_id": spec.psi_id, "file_name": file_name}
    in_microgravity = record.get("projectType") == "Microgravity Investigation"
    rows, conditions, flags = [], [], []

    # A condition stated once in a note applies to every test row.
    from_note = {}
    for field, source in spec.fields.items():
        if source.note_contains:
            note = frame[frame[source.column].str.contains(source.note_contains, regex=False)].iloc[0]
            from_note[field] = (note["row"], note[source.column])

    def flag(row: int, column: str, check: str, detail: str) -> None:
        flags.append({**key, "row": row, "column": column, "check": check, "detail": detail})

    for cells in frame.to_dict("records"):
        row = cells["row"]
        kind, why = spec.kind(cells)
        entry = {
            **key, "row": row, "acronym": record.get("investigationAcronym") or None,
            "row_kind": kind, "kind_note": why or None, "tests_in_row": None,
            "fuel_class": spec.fuel_class, "fuel": None,
            "gravity_g": 0.0 if in_microgravity else None,
        }  # fmt: skip
        rows.append(entry)
        if kind == "other":
            continue
        entry["fuel"] = spec.fuel_constant or (cells[spec.fuel_column].strip() if spec.fuel_column else "") or None
        if kind == "test":
            entry["tests_in_row"] = 1
        elif spec.tests_in_row:
            entry["tests_in_row"] = _whole_number(cells[spec.tests_in_row])

        single: dict[str, float] = {}
        for field in FIELDS:
            source = spec.fields.get(field)
            if source is None:
                continue
            if field in from_note:
                note_row, note_text = from_note[field]
                value = source.note_value * source.scale
                conditions.append({
                    **key, "row": row, "field": field, "value": value, "value_hi": None, "form": "single",
                    "approximate": True, "source_column": source.column, "source_row": note_row, "raw": note_text,
                })  # fmt: skip
                continue

            text = cells[source.column]
            reading = source.reader(text, source.units)
            if reading.status == "missing":
                continue
            if reading.status == "not_a_number":
                flag(row, source.column, "not_a_number", f"{text.strip()!r} is not a number")
                continue
            line = {**key, "row": row, "field": field, "source_column": source.column, "source_row": row, "raw": text}
            if reading.status == "varied":
                conditions.append({**line, "value": None, "value_hi": None, "form": "varied", "approximate": False})
                continue
            for low, high in reading.values:
                value = low * source.scale
                value_hi = None if high is None else high * source.scale
                broken = checks.out_of_bounds(field, value) or (
                    value_hi is not None and checks.out_of_bounds(field, value_hi)
                )
                if broken:
                    flag(row, source.column, "non_physical", f"{text.strip()!r} in {source.source_unit}: {broken}")
                    continue
                conditions.append({
                    **line, "value": value, "value_hi": value_hi, "form": reading.form,
                    "approximate": reading.approximate or source.approximate,
                })  # fmt: skip
                if reading.form == "single":
                    single[field] = value

        # Where a table states the whole gas mixture, the parts should add up to 1.
        mixture = [name for name in FRACTIONS if name in spec.fields]
        if "n2_mole_fraction" in mixture and all(name in single for name in mixture):
            total = sum(single[name] for name in mixture)
            if abs(total - 1) > 0.02 + 1e-9:
                gases = ", ".join(GAS_NAMES[name] for name in mixture)
                flag(row, spec.fields["o2_mole_fraction"].column, "fractions_do_not_sum",
                     f"{gases} add up to {total:.2f}, not 1")  # fmt: skip

    real_rows = frame[frame["row"].isin([r["row"] for r in rows if r["row_kind"] != "other"])]
    for check in spec.checks:
        flags.extend({**key, **found} for found in check(real_rows))

    by_row: dict[int, dict[str, list[float]]] = {}
    for line in conditions:
        if line["value"] is not None:
            values = by_row.setdefault(line["row"], {}).setdefault(line["field"], [])
            values.extend(v for v in (line["value"], line["value_hi"]) if v is not None)
    for entry in rows:
        for field, values in by_row.get(entry["row"], {}).items():
            entry[f"{field}_min"], entry[f"{field}_max"] = min(values), max(values)

    return file_name, rows, conditions, flags


def _table_summary(spec: Table, file_name: str, rows: list[dict], conditions: list[dict], flags: list[dict]) -> dict:
    fields = {}
    for field, source in spec.fields.items():
        lines = [c for c in conditions if c["field"] == field and c["value"] is not None]
        values = [v for c in lines for v in (c["value"], c["value_hi"]) if v is not None]
        fields[field] = {
            "source_column": source.column,
            "source_unit": source.source_unit,
            "multiplied_by": source.scale,
            "note": source.note or None,
            "rows_with_value": len({c["row"] for c in lines}),
            "min": float(format(min(values), ".6g")) if values else None,
            "max": float(format(max(values), ".6g")) if values else None,
        }
    repeated = {f["row"] for f in flags if f["check"] == "duplicate_row"}
    counted = [r["tests_in_row"] for r in rows if r["tests_in_row"] is not None and r["row"] not in repeated]
    return {
        "file_name": file_name,
        "rows": dict(Counter(r["row_kind"] for r in rows)),
        "tests_counted": sum(counted),
        "fuel_source": spec.fuel_column or spec.fuel_note or None,
        "fields": fields,
        "flags": dict(sorted(Counter(f["check"] for f in flags).items())),
    }


def _iso_date(text: str | None) -> str | None:
    """PSI writes dates as MM-DD-YYYY."""
    try:
        return datetime.strptime(text or "", "%m-%d-%Y").date().isoformat()
    except ValueError:
        return text or None


def _investigation(entry: dict, record: dict, tables: list[dict], fuel_class: str | None) -> dict:
    psi_id = entry["psi_id"]
    ranges: dict[str, dict] = {}
    for table in tables:
        for field, info in table["fields"].items():
            if info["min"] is None:
                continue
            seen = ranges.setdefault(field, {"min": info["min"], "max": info["max"]})
            seen["min"], seen["max"] = min(seen["min"], info["min"]), max(seen["max"], info["max"])
    in_microgravity = record.get("projectType") == "Microgravity Investigation"
    return {
        "psi_id": psi_id,
        "acronym": record.get("investigationAcronym") or None,
        "name": record.get("investigationAcronym") or record.get("title"),
        "title": record.get("title") or None,
        "in_scope": psi_id not in OUT_OF_SCOPE,
        "out_of_scope_reason": OUT_OF_SCOPE.get(psi_id),
        "doi": record.get("doi") or None,
        "license": record.get("licenseIdentifier") or None,
        "record_url": entry["record_url"],
        "project_type": record.get("projectType") or None,
        "platform": record.get("flightProgram") or None,
        "gravity_g": 0.0 if in_microgravity else None,
        "fuel_class": fuel_class,
        "nasa_center": record.get("managingNasaCenter") or None,
        "research_area": record.get("researchArea") or None,
        "sub_research_area": record.get("subResearchArea") or None,
        "start_date": _iso_date(record.get("investigationStartDate")),
        "end_date": _iso_date(record.get("investigationEndDate")),
        "objective": record.get("objective") or None,
        "approach": record.get("approach") or None,
        "hypothesis": record.get("hypothesis") or None,
        "hardware": record.get("experimentHardware") or None,
        "research_impacts": record.get("researchImpacts") or None,
        "related": re.findall(r"PSI-\d+", record.get("related_glds") or ""),
        "publications": [
            {"title": p.get("title") or None, "authors": p.get("authorList") or None, "doi": p.get("doi") or None}
            for p in record.get("publications") or []
        ],
        "condition_ranges": ranges,
        "tables": tables,
    }


def build() -> Outputs:
    rows, conditions, flags = [], [], []
    summaries: dict[str, list[dict]] = {}
    fuel_classes: dict[str, str] = {}
    records = {entry["psi_id"]: _record(entry["psi_id"]) for entry in raw.manifest()["investigations"]}

    for spec in TABLES:
        file_name, table_rows, table_conditions, table_flags = _read_table(spec, records[spec.psi_id])
        rows += table_rows
        conditions += table_conditions
        flags += table_flags
        fuel_classes[spec.psi_id] = spec.fuel_class
        summaries.setdefault(spec.psi_id, []).append(
            _table_summary(spec, file_name, table_rows, table_conditions, table_flags)
        )

    flags.sort(key=lambda f: (_psi_number(f["psi_id"]), f["file_name"], f["row"], f["column"], f["check"]))
    investigations = [
        _investigation(entry, records[entry["psi_id"]], summaries.get(entry["psi_id"], []),
                       fuel_classes.get(entry["psi_id"]))
        for entry in raw.manifest()["investigations"]
    ]  # fmt: skip
    return Outputs(rows, conditions, flags, investigations)


def write(outputs: Outputs | None = None) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, text in (outputs or build()).files().items():
        (PROCESSED / name).write_text(text, encoding="utf-8", newline="")


def check(outputs: Outputs | None = None) -> list[str]:
    """Names of committed files that no longer match what the code builds."""
    stale = []
    for name, text in (outputs or build()).files().items():
        path = PROCESSED / name
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append(name)
    return stale
