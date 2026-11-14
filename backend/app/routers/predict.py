"""6.3 Predictive modelling and physics engine, exposed over HTTP.

A thin adapter: all logic lives in the ignis_ml package, and the request and
response shapes are the contract types, unchanged.
"""

from fastapi import APIRouter

from ignis_ml import api
from ignis_ml.contract import (
    ModelCard,
    PredictRequest,
    PredictResponse,
    SimulateRequest,
    SimulateResponse,
)

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models() -> list[ModelCard]:
    return api.model_cards()


@router.post("/predict")
def predict(request: PredictRequest) -> PredictResponse:
    return api.predict(request)


@router.post("/simulate")
def simulate(request: SimulateRequest) -> SimulateResponse:
    return api.simulate(request)
