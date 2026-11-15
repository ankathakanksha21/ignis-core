"""Rank the investigations for a mission.

The score is this project's heuristic, not a NASA rating. It is a weighted
average of five factors, each between 0 and 1. A factor the data cannot
answer scores 0 and is reported as unknown, so missing data never helps.
"""

from __future__ import annotations

from . import catalog, store

PSI_TO_KPA = 6.894757
_EARTH_AIR = {"o2_mole_fraction": 0.21, "pressure_kpa": round(14.7 * PSI_TO_KPA, 1), "open_ended": False}
# "or more" and "or less": the brief gives this atmosphere as bounds, not a point.
_EXPLORATION = {"o2_mole_fraction": 0.30, "pressure_kpa": round(10.2 * PSI_TO_KPA, 1), "open_ended": True}
_EXPLORATION_BASIS = "The brief expects habitats at 30% oxygen or more and 10.2 psi or less."

MISSIONS = {
    "spacecraft": {
        "label": "Spacecraft", **_EARTH_AIR, "gravity_g": 0.0,
        "basis": "Microgravity.",
        "assumed": "The brief gives no atmosphere for a spacecraft. Earth-like air is assumed.",
    },
    "station": {
        "label": "Space station", **_EARTH_AIR, "gravity_g": 0.0,
        "basis": "Microgravity with Earth-like air.", "assumed": None,
    },
    "moon": {
        "label": "Moon base", **_EXPLORATION, "gravity_g": 0.16,
        "basis": _EXPLORATION_BASIS, "assumed": None,
    },
    "mars": {
        "label": "Mars base", **_EXPLORATION, "gravity_g": 0.38,
        "basis": "Mars gravity.",
        "assumed": "The brief gives no atmosphere for a Mars base. The Moon-base atmosphere is assumed.",
    },
    "rover": {
        "label": "Pressurized rover", **_EXPLORATION, "gravity_g": 0.16,
        "basis": _EXPLORATION_BASIS, "assumed": None,
    },
}  # fmt: skip

FACTORS = {
    "oxygen": "Oxygen match",
    "pressure": "Pressure match",
    "fuel": "Fuel type",
    "gravity": "Gravity",
    "pillar": "Pillar",
    "flow": "Flow match",
}
# Flow is scored only when the request gives a flow, so it never dilutes a ranking that did not ask for it.
DEFAULT_WEIGHTS = {"oxygen": 3.0, "pressure": 2.0, "fuel": 3.0, "gravity": 1.0, "pillar": 1.0, "flow": 2.0}

# A match scores 1 at the target and falls in a straight line to 0 this far away.
TOLERANCE = {"o2_mole_fraction": 0.10, "pressure_kpa": 35.0, "flow_cm_s": 10.0}

FUEL_RELEVANCE = {
    "solid": (1.0, "Cabin materials are solids."),
    "smoke": (1.0, "Smoke from overheated cabin materials."),
    "droplet": (0.5, "A liquid fuel, not a cabin material."),
    "gas": (0.3, "A gas flame, not a cabin material."),
    "dust": (0.2, "Dust, not a fuel."),
}
FUEL_OVERRIDES = {"PSI-20": (0.8, "A gas burner used to study material flammability, per the brief.")}
PARTIAL_GRAVITY_OVERRIDES = {"PSI-22": (0.75, "Mimicked partial gravity with an electric field, per the brief.")}


def _percent(fraction: float) -> str:
    return f"{fraction * 100:.3g}%"


def _factor(name: str, score: float, detail: str, *, unknown: bool = False, source: dict | None = None) -> dict:
    return {"id": name, "label": FACTORS[name], "score": round(score, 3), "unknown": unknown,
            "detail": detail, "source": source}  # fmt: skip


def _nearest(psi_id: str, field: str, target: float) -> tuple[float, dict] | None:
    """Distance from the target to the closest value the investigation tested."""
    best = None
    for line in store.conditions():
        if line["psi_id"] != psi_id or line["field"] != field or not line["value"]:
            continue
        low = float(line["value"])
        high = float(line["value_hi"]) if line["value_hi"] else low
        distance = 0.0 if low <= target <= high else min(abs(target - low), abs(target - high))
        if best is None or distance < best[0]:
            best = (distance, line)
    return best


def _match(name: str, psi_id: str, field: str, target: float, show) -> dict:
    found = _nearest(psi_id, field, target)
    if found is None:
        return _factor(name, 0.0, "Not stated in the test table.", unknown=True)
    distance, line = found
    tested = show(float(line["value"]))
    if line["value_hi"]:
        tested += f" to {show(float(line['value_hi']))}"
    source = {"file_name": line["file_name"], "row": int(line["source_row"]),
              "column": line["source_column"].strip(), "raw": line["raw"].strip()}  # fmt: skip
    score = max(0.0, 1 - distance / TOLERANCE[field])
    return _factor(name, score, f"Nearest tested: {tested}. Target: {show(target)}.", source=source)


def _fuel(entry: dict) -> dict:
    relevance = FUEL_OVERRIDES.get(entry["psi_id"]) or FUEL_RELEVANCE.get(entry["fuel_class"])
    if relevance is None:
        return _factor("fuel", 0.0, "No test table, so no fuel.", unknown=True)
    return _factor("fuel", relevance[0], relevance[1])


def _gravity(entry: dict, mission_g: float) -> dict:
    if entry["gravity_g"] is None:
        return _factor("gravity", 0.0, "A ground study with no flight tests.", unknown=True)
    if mission_g == entry["gravity_g"]:
        return _factor("gravity", 1.0, "Tested in microgravity, as on this mission.")
    override = PARTIAL_GRAVITY_OVERRIDES.get(entry["psi_id"])
    if override and 0 < mission_g < 1:
        return _factor("gravity", *override)
    return _factor("gravity", 0.5, f"Untested at {mission_g:g} g. PSI has no such data; microgravity results only bound it.")


def _pillar(entry: dict) -> dict:
    pillar = catalog.PILLAR_OF[entry["psi_id"]][0]
    if pillar == "science":
        return _factor("pillar", 0.5, "Flame science: the brief ties it to no single pillar.")
    return _factor("pillar", 1.0, f"{pillar.capitalize()}: tied to a fire safety pillar.")


def rank(profile: dict, weights: dict[str, float]) -> list[dict]:
    flow = profile.get("flow_cm_s")
    results = []
    for entry in store.investigations().values():
        if not entry["in_scope"]:
            continue
        psi_id = entry["psi_id"]
        factors = [
            _match("oxygen", psi_id, "o2_mole_fraction", profile["o2_mole_fraction"], _percent),
            _match("pressure", psi_id, "pressure_kpa", profile["pressure_kpa"], lambda kpa: f"{kpa:.3g} kPa"),
            _fuel(entry),
            _gravity(entry, profile["gravity_g"]),
            _pillar(entry),
        ]
        if flow is not None:
            factors.append(_match("flow", psi_id, "flow_cm_s", flow, lambda cm_s: f"{cm_s:.3g} cm/s"))
        for factor in factors:
            factor["weight"] = weights[factor["id"]]
        total_weight = sum(factor["weight"] for factor in factors)
        score = sum(f["score"] * f["weight"] for f in factors) / total_weight if total_weight else 0.0
        results.append({"psi_id": psi_id, "name": entry["name"], "pillar": catalog.PILLAR_OF[psi_id][0],
                        "fuel_class": entry["fuel_class"], "score": round(score, 3), "factors": factors})  # fmt: skip
    return sorted(results, key=lambda result: (-result["score"], result["name"]))
