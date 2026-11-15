"""The contract's honesty rules are enforced by the types themselves."""

from typing import get_args

import pytest
from pydantic import ValidationError

from ignis_ml import api
from ignis_ml.contract import (
    ModelId,
    PredictRequest,
    PredictResponse,
    Prediction,
    RangeViolation,
    SimState,
    SimulateRequest,
    SimulateResponse,
)


def test_every_model_has_a_card():
    assert [card.model_id for card in api.model_cards()] == list(get_args(ModelId))


def test_placeholders_answer_not_implemented():
    request = PredictRequest(model_id="flex_extinction", inputs={"o2_mole_fraction": 0.21})
    assert api.predict(request).status == "not_implemented"
    sim = SimulateRequest(scenario="droplet", fuel="heptane", gravity_g=0, pressure_kpa=101.3, o2_mole_fraction=0.21)
    assert api.simulate(sim).status == "not_implemented"


def test_a_withheld_prediction_cannot_carry_a_value():
    with pytest.raises(ValidationError):
        PredictResponse(
            status="withheld",
            model_id="flex_burning_rate",
            prediction=Prediction(value=0.5, unit="mm^2/s"),
            out_of_range=[RangeViolation(feature="o2_mole_fraction", value=0.5, tested_min=0.12, tested_max=0.34)],
        )


def test_an_out_of_range_input_cannot_be_ok():
    with pytest.raises(ValidationError):
        PredictResponse(
            status="ok",
            model_id="flex_burning_rate",
            prediction=Prediction(value=0.5, unit="mm^2/s"),
            out_of_range=[RangeViolation(feature="o2_mole_fraction", value=0.5, tested_min=0.12, tested_max=0.34)],
        )


def test_withheld_must_say_why():
    with pytest.raises(ValidationError):
        PredictResponse(status="withheld", model_id="flex_burning_rate")


def test_partial_gravity_is_reported_as_bounds_not_a_single_answer():
    micro = SimState(gravity_g=0, sustains=True, regime="burning")
    normal = SimState(gravity_g=1, sustains=True, regime="burning")
    SimulateResponse(status="ok", bounds=[micro, normal])
    SimulateResponse(status="ok", state=micro)
    with pytest.raises(ValidationError):
        SimulateResponse(status="ok", state=micro, bounds=[micro, normal])
    with pytest.raises(ValidationError):
        SimulateResponse(status="ok")


def test_gas_fractions_cannot_exceed_one():
    with pytest.raises(ValidationError):
        SimulateRequest(
            scenario="droplet", fuel="heptane", gravity_g=0, pressure_kpa=101.3,
            o2_mole_fraction=0.6, co2_mole_fraction=0.5,
        )  # fmt: skip
