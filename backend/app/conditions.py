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
