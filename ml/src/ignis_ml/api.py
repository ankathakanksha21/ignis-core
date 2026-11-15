"""The three functions the rest of the app calls. Nothing else in ml/ is public.

On main these are placeholders that answer "not_implemented", which is a valid
contract response, so the backend and the UI can be built against them today.
The 6.3 work replaces the bodies; the signatures stay.
"""

from __future__ import annotations

from typing import get_args

from .contract import (
    ModelCard,
    ModelId,
    PredictRequest,
    PredictResponse,
    SimulateRequest,
    SimulateResponse,
)
from .models import flex_burning_rate
from .physics import droplet

_PLANNED: dict[ModelId, dict] = {
    "flex_burning_rate": dict(
        title="Droplet burning rate", fuel_class="droplet", task="regression",
        target="burning rate", target_unit="mm^2/s",
    ),
    "flex_extinction": dict(
        title="Droplet flame extinction", fuel_class="droplet", task="classification",
        target="test end", classes=["Extinction", "Disruption", "Completion"],
    ),
    "cfig_cool_flame": dict(
        title="Cool flame occurrence", fuel_class="gas", task="classification",
        target="cool flame", classes=["yes", "no"],
    ),
    "solid_flame_spread": dict(
        title="Flame spread on solids", fuel_class="solid", task="matcher",
        target="nearest real tests",
    ),
}  # fmt: skip


# Models that are built. Anything in ModelId but not here answers not_implemented.
_BUILT = {flex_burning_rate.MODEL_ID: flex_burning_rate}


def model_cards() -> list[ModelCard]:
    """Every model the app knows about, built or not, with its tested ranges."""
    return [
        _BUILT[model_id].card()
        if model_id in _BUILT
        else ModelCard(model_id=model_id, status="not_implemented", **_PLANNED[model_id])
        for model_id in get_args(ModelId)
    ]


def predict(request: PredictRequest) -> PredictResponse:
    """Predict from measured-data models. Withholds outside the tested range."""
    if request.model_id in _BUILT:
        return _BUILT[request.model_id].predict(request)
    return PredictResponse(
        status="not_implemented",
        model_id=request.model_id,
        message="This model is not built yet.",
    )


def simulate(request: SimulateRequest) -> SimulateResponse:
    """Run the simplified physics engine. Output is always labelled simulated."""
    if request.scenario == "droplet":
        return droplet.simulate(request)
    return SimulateResponse(
        status="not_implemented",
        message="The solid scenario is not built: PSI has too few solid tests with an outcome to calibrate it on.",
    )
