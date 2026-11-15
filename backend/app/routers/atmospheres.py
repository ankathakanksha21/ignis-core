"""6.2 Exploration atmospheres: habitat profiles, untested conditions, suggested experiments, data quality."""

from fastapi import APIRouter, HTTPException

from .. import gaps

router = APIRouter(prefix="/atmospheres", tags=["atmospheres"])


@router.get("/habitats")
def list_habitats() -> list[dict]:
    return [{"id": key, **habitat} for key, habitat in gaps.HABITATS.items()]


@router.get("/gaps")
def get_gap_map(habitat: str = "moon") -> dict:
    if habitat not in gaps.HABITATS:
        raise HTTPException(404, f"Unknown habitat {habitat!r}")
    return gaps.gap_map(habitat)
