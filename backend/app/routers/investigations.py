"""6.1 Mission-relevance dashboard: investigation cards, ranking, compare, similar tests, gap map."""

from collections import Counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import catalog, conditions, ranking, store, summaries

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


class SimilarRequest(BaseModel):
    # Leave a condition out to ignore it.
    o2_mole_fraction: float | None = Field(default=None, ge=0, le=1)
    pressure_kpa: float | None = Field(default=None, gt=0)
    flow_cm_s: float | None = Field(default=None, ge=0)
    fuel_class: str | None = None


@router.post("/similar")
def find_similar(request: SimilarRequest) -> dict:
    query = {field: value for field in ranking.TOLERANCE if (value := getattr(request, field)) is not None}
    if not query:
        raise HTTPException(422, "Give at least one of oxygen, pressure or flow")
    results = conditions.similar(query, request.fuel_class)
    return {
        "query": query,
        "tolerance": {field: ranking.TOLERANCE[field] for field in query},
        "results": results,
        # True when even the closest row is more than one tolerance away, or states less than was asked.
        "nothing_close": not results or results[0]["distance"] > 1 or bool(results[0]["not_stated"]),
    }


@router.get("/points")
def get_points(ids: str) -> dict:
    wanted = [psi_id for psi_id in ids.split(",") if psi_id]
    known = store.investigations()
    if not 1 <= len(wanted) <= 3 or any(psi_id not in known or not known[psi_id]["in_scope"] for psi_id in wanted):
        raise HTTPException(404, "Give one to three combustion investigation ids, separated by commas")
    return {"series": [conditions.points(psi_id) for psi_id in wanted]}


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
