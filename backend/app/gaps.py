"""The knowledge-gap map: how many tests fall in each oxygen and pressure cell.

Counts are table rows. A row that lists several oxygen levels counts once in
each cell it names. Every count is microgravity: PSI has no other gravity.
"""

from __future__ import annotations

from . import conditions, store
from .ranking import FUEL_RELEVANCE, MISSIONS, PSI_TO_KPA, TOLERANCE

# Oxygen in percent and pressure in kPa. The last bin of each is open-ended.
OXYGEN_EDGES = [10, 15, 20, 25, 30, 35, 40, 45, 100]
PRESSURE_EDGES = [0, 25, 50, 75, 100, 125, 150, 1000]
NOT_STATED = len(PRESSURE_EDGES) - 1  # index of the extra "pressure not stated" row
MAPPED = ("solid", "droplet", "gas")  # the fuel classes with oxygen data

HABITATS = {
    **MISSIONS,
    "suit": {
        "label": "Spacesuit", "o2_mole_fraction": 1.0, "pressure_kpa": round(4.3 * PSI_TO_KPA, 1),
        "gravity_g": None, "open_ended": False, "basis": "100% oxygen at 4.3 psi.", "assumed": None,
    },
    "earth": {
        "label": "Earth reference", "o2_mole_fraction": 0.21, "pressure_kpa": round(14.7 * PSI_TO_KPA, 1),
        "gravity_g": 1.0, "open_ended": False, "basis": "Sea-level air.", "assumed": None,
    },
}  # fmt: skip


def _bin(value: float, edges: list[int]) -> int:
    for index in range(len(edges) - 1):
        if value < edges[index + 1]:
            return max(index, 0)
    return len(edges) - 2


def _label(index: int, edges: list[int], unit: str) -> str:
    last = index == len(edges) - 2
    return f"{edges[index]}{unit} and above" if last else f"{edges[index]} to {edges[index + 1]}{unit}"


def _counts() -> dict[str, dict[tuple[int, int], dict]]:
    """fuel class -> (oxygen bin, pressure bin) -> rows and which investigations."""
    grid: dict[str, dict[tuple[int, int], dict]] = {name: {} for name in MAPPED}
    for psi_id, entry in store.investigations().items():
        if not entry["in_scope"] or entry["fuel_class"] not in grid:
            continue
        seen: dict[tuple[int, int], set] = {}
        by_file: dict[tuple[int, int], dict[str, set]] = {}
        found = conditions.points(psi_id)
        for point in found["points"] + found["oxygen_only"]:
            pressure = point.get("pressure_kpa")
            cell = (_bin(point["o2"] * 100, OXYGEN_EDGES), NOT_STATED if pressure is None else _bin(pressure, PRESSURE_EDGES))
            seen.setdefault(cell, set()).update(point["rows"])
            by_file.setdefault(cell, {}).setdefault(point["file_name"], set()).update(point["rows"])
        for cell, rows in seen.items():
            into = grid[entry["fuel_class"]].setdefault(cell, {"rows": 0, "from": {}, "sources": []})
            into["rows"] += len(rows)
            into["from"][entry["name"]] = len(rows)
            # Which table rows these are, so the page can link straight to the tests.
            into["sources"] += [
                {"psi_id": psi_id, "name": entry["name"], "file_name": file_name, "rows": sorted(numbers)}
                for file_name, numbers in sorted(by_file[cell].items())
            ]
    return grid


def _gravity_note(gravity_g: float | None) -> str:
    if gravity_g is None:
        return "No gravity is given for this profile. Every count below is a microgravity test."
    if gravity_g == 0:
        return "Every count below is a microgravity test, as this habitat is."
    return (f"PSI has no combustion test at {gravity_g:g} g. Every count below is a microgravity test, "
            "which can only bound this habitat.")  # fmt: skip


def _centre_gap(value: float, edges: list[int], index: int, tolerance: float) -> float:
    """How far a cell is from a value, in tolerances: 0 for the cell holding it."""
    if _bin(value, edges) == index:
        return 0.0
    return abs((edges[index] + edges[index + 1]) / 2 - value) / tolerance


def gap_map(habitat_id: str) -> dict:
    habitat = HABITATS[habitat_id]
    oxygen, pressure = habitat["o2_mole_fraction"] * 100, habitat["pressure_kpa"]
    grid = _counts()
    columns, rows = len(OXYGEN_EDGES) - 1, len(PRESSURE_EDGES) - 1
    home = {"column": _bin(oxygen, OXYGEN_EDGES), "row": _bin(pressure, PRESSURE_EDGES)}

    # Empty cells near the habitat, ranked by closeness and by how close the fuel is to a cabin material.
    suggestions = []
    for fuel_class in MAPPED:
        relevance, why = FUEL_RELEVANCE[fuel_class]
        oxygen_tested = {column for column, _ in grid[fuel_class]}
        for column in range(columns):
            for row in range(rows):
                if (column, row) in grid[fuel_class]:
                    continue
                gap = max(
                    _centre_gap(oxygen, OXYGEN_EDGES, column, TOLERANCE["o2_mole_fraction"] * 100),
                    _centre_gap(pressure, PRESSURE_EDGES, row, TOLERANCE["pressure_kpa"]),
                )
                # "30% or more, 10.2 psi or less" covers every cell up and to the low-pressure side.
                in_bounds = habitat["open_ended"] and column >= home["column"] and row <= home["row"]
                if gap >= 1 and not in_bounds:
                    continue
                unplaced = grid[fuel_class].get((column, NOT_STATED), {}).get("rows", 0)
                suggestions.append({
                    "fuel_class": fuel_class, "column": column, "row": row,
                    "oxygen": _label(column, OXYGEN_EDGES, "%"), "pressure": _label(row, PRESSURE_EDGES, " kPa"),
                    "score": round(relevance * max(0.0, 1 - gap), 3), "fuel_why": why, "in_bounds": in_bounds,
                    # The two numbers the score is the product of, so the page can show the working.
                    "closeness": round(max(0.0, 1 - gap), 3), "relevance": relevance,
                    # Rows at this oxygen that state no pressure might belong here; nobody can tell.
                    "status": "pressure_unknown" if unplaced else "untested",
                    "rows_without_pressure": unplaced,
                    "oxygen_never_tested": column not in oxygen_tested,
                })  # fmt: skip
    suggestions.sort(key=lambda s: (s["status"] != "untested", -s["score"], s["fuel_class"], s["column"], s["row"]))

    by_class = []
    for fuel_class in MAPPED:
        entries = [e for e in store.investigations().values() if e["in_scope"] and e["fuel_class"] == fuel_class]
        by_class.append({
            "fuel_class": fuel_class,
            "cells": [{"column": c, "row": r, **cell} for (c, r), cell in sorted(grid[fuel_class].items())],
            "nearest": conditions.nearest(fuel_class, habitat["o2_mole_fraction"], pressure),
            "rows_not_placed": sum(conditions.points(e["psi_id"])["rows_not_placed"] for e in entries),
            "rows_burner_fed": sum(conditions.points(e["psi_id"])["rows_burner_fed"] for e in entries),
        })  # fmt: skip

    return {
        "habitat": {"id": habitat_id, **habitat},
        "gravity_note": _gravity_note(habitat["gravity_g"]),
        "oxygen_bins": [_label(i, OXYGEN_EDGES, "%") for i in range(columns)],
        "pressure_bins": [_label(i, PRESSURE_EDGES, " kPa") for i in range(rows)] + ["not stated"],
        "habitat_cell": home,
        "classes": by_class,
        "suggestions": suggestions[:8],
        "candidates": len(suggestions),
        "fuel_relevance": {fuel_class: FUEL_RELEVANCE[fuel_class][0] for fuel_class in MAPPED},
        "tolerance": {"oxygen_points": TOLERANCE["o2_mole_fraction"] * 100, "pressure_kpa": TOLERANCE["pressure_kpa"]},
        "unmapped": sorted({e["fuel_class"] for e in store.investigations().values()
                            if e["in_scope"] and e["fuel_class"] and e["fuel_class"] not in MAPPED}),
    }  # fmt: skip
