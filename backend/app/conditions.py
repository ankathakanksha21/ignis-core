"""Where tests sit on oxygen against pressure, and which real test is nearest a point."""

from functools import lru_cache
from math import hypot

from . import store
from .ranking import TOLERANCE


@lru_cache(maxsize=None)
def points(psi_id: str) -> dict:
    """Where an investigation's tests sit on oxygen against pressure.

    A row is placed when it states one oxygen value or one pressure, so each
    pair is certain. A row that lists several of both (a test matrix) is not
    placed: the table does not say which pairs were run.
    """
    by_row: dict[tuple, dict[str, list]] = {}
    for line in store.conditions():
        if line["psi_id"] == psi_id and line["value"]:
            cells = by_row.setdefault((line["file_name"], int(line["row"])), {})
            ends = [float(line["value"])] + ([float(line["value_hi"])] if line["value_hi"] else [])
            cells.setdefault(line["field"], []).extend(ends)
            cells["approximate"] = cells.get("approximate", False) or line["approximate"] == "true"

    placed: dict[tuple, dict] = {}
    oxygen_only: dict[float, dict] = {}
    not_placed = burner_fed = 0
    for (file_name, row), cells in sorted(by_row.items()):
        oxygen, pressure = cells.get("o2_mole_fraction", []), cells.get("pressure_kpa", [])
        if not oxygen:
            burner_fed += "burner_o2_mole_fraction" in cells
            continue
        if not pressure:
            targets = [(oxygen_only, (file_name, o2), {"o2": o2}) for o2 in oxygen]
        elif len(oxygen) == 1 or len(pressure) == 1:
            targets = [(placed, (file_name, o2, round(kpa, 1)), {"o2": o2, "pressure_kpa": round(kpa, 1)})
                       for o2 in oxygen for kpa in pressure]  # fmt: skip
        else:
            not_placed += 1
            continue
        for group, key, values in targets:
            point = group.setdefault(key, {**values, "file_name": file_name, "rows": [], "approximate": False})
            point["rows"].append(row)
            point["approximate"] = point["approximate"] or cells["approximate"]

    entry = store.investigations()[psi_id]
    return {
        "psi_id": psi_id,
        "name": entry["name"],
        "points": list(placed.values()),
        "oxygen_only": list(oxygen_only.values()),
        "rows_not_placed": not_placed,
        "rows_burner_fed": burner_fed,
    }


def nearest(fuel_class: str, o2: float, pressure_kpa: float) -> dict | None:
    """The real test of this fuel class closest to an atmosphere.

    Distance is in tolerance units: 1 means one full tolerance away in oxygen
    or pressure. Tests that state no pressure are compared on oxygen alone,
    and are used only when the class has no test that states both.
    """
    best: dict | None = None
    for psi_id, entry in store.investigations().items():
        if not entry["in_scope"] or entry["fuel_class"] != fuel_class:
            continue
        found = points(psi_id)
        for point in found["points"] + found["oxygen_only"]:
            oxygen_gap = (point["o2"] - o2) / TOLERANCE["o2_mole_fraction"]
            stated = "pressure_kpa" in point
            distance = hypot(oxygen_gap, (point["pressure_kpa"] - pressure_kpa) / TOLERANCE["pressure_kpa"]) if stated else abs(oxygen_gap)
            rank = (not stated, distance)  # a test stating both always beats one stating oxygen only
            if best is None or rank < best["_rank"]:
                best = {"_rank": rank, "psi_id": psi_id, "name": found["name"], "file_name": point["file_name"],
                        "row": point["rows"][0], "rows": len(point["rows"]), "o2": point["o2"],
                        "pressure_kpa": point.get("pressure_kpa"), "distance": round(distance, 3)}  # fmt: skip
    if best:
        del best["_rank"]
    return best


@lru_cache(maxsize=1)
def _rows() -> list[dict]:
    """Every test and summary row with the conditions it states, as (low, high) pairs."""
    stated: dict[tuple, dict[str, list]] = {}
    for line in store.conditions():
        if line["value"] and line["field"] in TOLERANCE:
            low = float(line["value"])
            pairs = stated.setdefault((line["psi_id"], line["file_name"], line["row"]), {}).setdefault(line["field"], [])
            pairs.append((low, float(line["value_hi"]) if line["value_hi"] else low))
    names = {psi_id: entry["name"] for psi_id, entry in store.investigations().items()}
    return [
        {"psi_id": row["psi_id"], "name": names[row["psi_id"]], "file_name": row["file_name"], "row": int(row["row"]),
         "row_kind": row["row_kind"], "fuel_class": row["fuel_class"], "fuel": row["fuel"] or None,
         "stated": stated.get((row["psi_id"], row["file_name"], row["row"]), {})}
        for row in store.rows() if row["row_kind"] != "other"
    ]  # fmt: skip


def similar(query: dict[str, float], fuel_class: str | None = None, limit: int = 15) -> list[dict]:
    """The real rows closest to a set of conditions, across investigations.

    A row is compared on the conditions it states. Rows that state every
    condition asked for come first; a row that states none is left out.
    Distance is in tolerances: 1 means one full tolerance away.
    """
    found = []
    for row in _rows():
        if fuel_class and row["fuel_class"] != fuel_class:
            continue
        gaps = {}
        for field, wanted in query.items():
            pairs = row["stated"].get(field)
            if pairs:
                nearest = min(0.0 if low <= wanted <= high else min(abs(wanted - low), abs(wanted - high)) for low, high in pairs)
                gaps[field] = nearest / TOLERANCE[field]
        if not gaps:
            continue
        values = {field: {"min": min(low for low, _ in pairs), "max": max(high for _, high in pairs)}
                  for field, pairs in row["stated"].items()}  # fmt: skip
        found.append({
            **{key: row[key] for key in ("psi_id", "name", "file_name", "row", "row_kind", "fuel_class", "fuel")},
            "values": values,
            "not_stated": [field for field in query if field not in gaps],
            "distance": round(hypot(*gaps.values()), 3),
        })  # fmt: skip
    found.sort(key=lambda r: (len(r["not_stated"]), r["distance"], r["psi_id"], r["row"]))
    return found[:limit]
