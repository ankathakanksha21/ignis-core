"""6.4 Interactive combustion lab: presets and the real tests shown beside a simulation."""

from functools import lru_cache

from fastapi import APIRouter

from ignis_ml import raw

from .. import store
from ..ingest.cells import read_numbers

router = APIRouter(prefix="/lab", tags=["lab"])

PSI_ID = "PSI-69"
# What the pattern explorer can plot: (key, label, unit, where it comes from)
FIELDS = [
    ("o2_percent", "Oxygen", "%", "o2_mole_fraction"),
    ("co2_percent", "Carbon dioxide", "%", "co2_mole_fraction"),
    ("he_percent", "Helium", "%", "he_mole_fraction"),
    ("pressure_kpa", "Pressure", "kPa", "pressure_kpa"),
    ("droplet_mm", "Droplet diameter", "mm", "Droplet initial diameter; mm"),
    ("burning_rate", "Burning rate", "mm²/s", "Burning rate; mm"),
    ("burn_time_s", "Burn time", "s", "Burn time; s"),
    ("flame_out_mm", "Droplet diameter at flame-out", "mm", "Visible flame extinction diameter; mm"),
]
_SCALE = {"o2_percent": 100, "co2_percent": 100, "he_percent": 100}


@lru_cache(maxsize=1)
def _flex() -> dict:
    """Every FLEX test as numbers, for plotting measured against measured."""
    entry = store.investigations()[PSI_ID]
    conditions: dict[int, dict[str, float]] = {}
    for line in store.conditions():
        if line["psi_id"] == PSI_ID and line["value"]:
            conditions.setdefault(int(line["row"]), {})[line["field"]] = float(line["value"])
    flagged = {int(flag["row"]) for flag in store.flags() if flag["psi_id"] == PSI_ID}

    rows = []
    for record in raw.read_raw_table(PSI_ID).to_dict("records"):
        row = {"row": record["row"], "fuel": record["Fuel"].strip(), "test_end": record["Test end"].strip(),
               "flagged": record["row"] in flagged}  # fmt: skip
        for key, _, _, source in FIELDS:
            if source in record:  # a column read here, as published
                reading = read_numbers(record[source])
                row[key] = reading.values[0][0] if reading.status == "ok" and reading.form == "single" else None
            else:  # a condition ingest already converted and checked
                value = conditions.get(record["row"], {}).get(source)
                row[key] = None if value is None else round(value * _SCALE.get(key, 1), 4)
        rows.append(row)
    return {
        "source": {"psi_id": PSI_ID, "name": entry["name"], "file_name": entry["tables"][0]["file_name"], "doi": entry["doi"]},
        "fields": [{"key": key, "label": label, "unit": unit} for key, label, unit, _ in FIELDS],
        "rows": rows,
        "note": "NASA's header for burning rate has lost part of its unit. The values fit mm²/s.",
    }


@router.get("/flex")
def flex_rows() -> dict:
    return _flex()
