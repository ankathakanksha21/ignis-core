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


def model_cards() -> list[ModelCard]:
    """Every model the app knows about, built or not, with its tested ranges."""
    return [
        ModelCard(model_id=model_id, status="not_implemented", **_PLANNED[model_id])
        for model_id in get_args(ModelId)
    ]


def predict(request: PredictRequest) -> PredictResponse:
    """Predict from measured-data models. Withholds outside the tested range."""
    return PredictResponse(
        status="not_implemented",
        model_id=request.model_id,
        message="This model is not built yet.",
    )


def simulate(request: SimulateRequest) -> SimulateResponse:
    """Run the simplified physics engine. Output is always labelled simulated."""
    return SimulateResponse(
        status="not_implemented",
        message="The physics engine is not built yet.",
    )
