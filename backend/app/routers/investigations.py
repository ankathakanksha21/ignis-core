"""6.1 Mission-relevance dashboard: investigation cards, ranking, compare, similar tests, gap map."""

from collections import Counter

from fastapi import APIRouter, HTTPException

from .. import catalog, store

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
    }


@router.get("")
def list_investigations() -> dict:
    entries = store.investigations().values()
    return {
        "pillars": [{"id": key, "description": text} for key, text in catalog.PILLARS.items()],
        "investigations": [_card(entry) for entry in entries if entry["in_scope"]],
        "left_out": [
            {"psi_id": e["psi_id"], "title": e["title"], "reason": e["out_of_scope_reason"]}
            for e in entries if not e["in_scope"]
        ],  # fmt: skip
    }


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
    }
