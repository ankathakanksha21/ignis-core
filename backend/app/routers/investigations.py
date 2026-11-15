"""6.1 Mission-relevance dashboard: investigation cards, ranking, compare, similar tests, gap map."""

from collections import Counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import catalog, ranking, store, summaries

router = APIRouter(prefix="/investigations", tags=["investigations"])


def _shorten(text: str | None, limit: int = 150) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _card(entry: dict) -> dict:
    psi_id = entry["psi_id"]
    pillar, why = catalog.PILLAR_OF[psi_id]
    kinds = Counter()
    for table in entry["tables"]:
        kinds.update(table["rows"])
    fuels = Counter(
        r["fuel"] for r in store.rows() if r["psi_id"] == psi_id and r["row_kind"] != "other" and r["fuel"]
    )
    return {
        "psi_id": psi_id,
        "name": entry["name"],
        "title": entry["title"],
        "pillar": pillar,
        "pillar_why": why,
        "fuel_class": entry["fuel_class"],
        "project_type": entry["project_type"],
        "platform": entry["platform"],
        "gravity_g": entry["gravity_g"],
        "hardware": entry["hardware"],
        "doi": entry["doi"],
        "objective_short": _shorten(entry["objective"]),
        "test_rows": kinds["test"],
        "summary_rows": kinds["summary"],
        "tests_counted": sum(table["tests_counted"] for table in entry["tables"]),
        "fuels": [name for name, _ in fuels.most_common(4)],
        "fuel_count": len(fuels),
        "conditions": entry["condition_ranges"],
        "flag_count": sum(1 for flag in store.flags() if flag["psi_id"] == psi_id),
        "brief_note": catalog.BRIEF_NOTES.get(psi_id),
        "ai_summary": summaries.get(psi_id),
    }


@router.get("")
def list_investigations() -> dict:
    entries = store.investigations().values()
    return {
        "pillars": [{"id": key, "description": text} for key, text in catalog.PILLARS.items()],
        "ai_model": summaries.model_name(),
        "investigations": [_card(entry) for entry in entries if entry["in_scope"]],
        "left_out": [
            {"psi_id": e["psi_id"], "title": e["title"], "reason": e["out_of_scope_reason"]}
            for e in entries if not e["in_scope"]
        ],  # fmt: skip
    }


class RankRequest(BaseModel):
    mission: str
    # Leave these out to use the mission's own profile.
    o2_mole_fraction: float | None = Field(default=None, ge=0, le=1)
    pressure_kpa: float | None = Field(default=None, gt=0)
    gravity_g: float | None = Field(default=None, ge=0, le=1)
    weights: dict[str, float] = {}


@router.get("/missions")
def list_missions() -> dict:
    return {
        "missions": [{"id": key, **mission} for key, mission in ranking.MISSIONS.items()],
        "factors": [{"id": key, "label": label, "weight": ranking.DEFAULT_WEIGHTS[key]}
                    for key, label in ranking.FACTORS.items()],
        "tolerance": ranking.TOLERANCE,
        "fuel_relevance": [{"fuel_class": key, "score": score, "why": why}
                           for key, (score, why) in ranking.FUEL_RELEVANCE.items()],
    }  # fmt: skip


@router.post("/rank")
def rank_investigations(request: RankRequest) -> dict:
    mission = ranking.MISSIONS.get(request.mission)
    if mission is None:
        raise HTTPException(404, f"Unknown mission {request.mission!r}")
    unknown = set(request.weights) - set(ranking.FACTORS)
    if unknown or any(not 0 <= weight <= 5 for weight in request.weights.values()):
        raise HTTPException(422, "Weights are 0 to 5, one per factor: " + ", ".join(ranking.FACTORS))

    profile = {key: mission[key] for key in ("o2_mole_fraction", "pressure_kpa", "gravity_g")}
    edits = {key: value for key in profile if (value := getattr(request, key)) is not None and value != profile[key]}
    profile.update(edits)
    weights = {**ranking.DEFAULT_WEIGHTS, **request.weights}
    return {
        "mission": request.mission,
        "profile": profile,
        "edited": sorted(edits),
        "weights": weights,
        "results": [
            {**result, "one_line": (summaries.get(result["psi_id"]) or {}).get("one_line")}
            for result in ranking.rank(profile, weights)
        ],
    }


def _points(psi_id: str) -> dict:
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
    for (_, row), cells in sorted(by_row.items()):
        oxygen, pressure = cells.get("o2_mole_fraction", []), cells.get("pressure_kpa", [])
        if not oxygen:
            burner_fed += "burner_o2_mole_fraction" in cells
            continue
        if not pressure:
            targets = [(oxygen_only, o2, {"o2": o2}) for o2 in oxygen]
        elif len(oxygen) == 1 or len(pressure) == 1:
            targets = [(placed, (o2, round(kpa, 1)), {"o2": o2, "pressure_kpa": round(kpa, 1)})
                       for o2 in oxygen for kpa in pressure]  # fmt: skip
        else:
            not_placed += 1
            continue
        for group, key, values in targets:
            point = group.setdefault(key, {**values, "rows": [], "approximate": False})
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


@router.get("/points")
def get_points(ids: str) -> dict:
    wanted = [psi_id for psi_id in ids.split(",") if psi_id]
    known = store.investigations()
    if not 1 <= len(wanted) <= 3 or any(psi_id not in known or not known[psi_id]["in_scope"] for psi_id in wanted):
        raise HTTPException(404, "Give one to three combustion investigation ids, separated by commas")
    return {"series": [_points(psi_id) for psi_id in wanted]}


@router.get("/{psi_id}")
def get_investigation(psi_id: str) -> dict:
    entry = store.investigations().get(psi_id)
    if entry is None or not entry["in_scope"]:
        raise HTTPException(404, f"{psi_id} is not one of the combustion investigations")

    names = {key: value["name"] for key, value in store.investigations().items()}
    shared = next(
        ({"hardware": label, "with": [{"psi_id": other, "name": names[other]} for other in members if other != psi_id]}
         for label, members in catalog.HARDWARE_GROUPS.items() if psi_id in members),
        None,
    )  # fmt: skip
    tables = [
        {**table, "columns": store.columns(psi_id, table["file_name"])}
        for table in entry["tables"]
    ]  # fmt: skip
    return {
        **_card(entry),
        "objective": entry["objective"],
        "approach": entry["approach"],
        "hypothesis": entry["hypothesis"],
        "research_impacts": entry["research_impacts"],
        "license": entry["license"],
        "start_date": entry["start_date"],
        "end_date": entry["end_date"],
        "related": [{"psi_id": other, "name": names.get(other, other)} for other in entry["related"]],
        "shares_hardware": shared,
        "publications": entry["publications"],
        "tables": tables,
        "flags": [flag for flag in store.flags() if flag["psi_id"] == psi_id],
        "ai_model": summaries.model_name(),
    }
