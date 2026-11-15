"""The contract between the 6.3 models and the rest of the app.

This file is jointly owned. Everything else in ml/ can change freely, but a
change here changes what the dashboard receives, so it goes through a pull
request that both people approve. docs/CONTRACTS.md explains it in prose.

Units are fixed so nobody converts twice:

    oxygen and diluents   mole fraction, 0 to 1   (o2_mole_fraction)
    pressure              kPa                     (pressure_kpa)
    flow velocity         cm/s                    (flow_cm_s)
    gravity               multiples of Earth g    (gravity_g)
    lengths               mm
    time                  s
    burning-rate constant mm^2/s
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "0.1"

ModelId = Literal[
    "flex_burning_rate",
    "flex_extinction",
    "cfig_cool_flame",
    "cfig_hot_ignition",
    "solid_flame_spread",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# Pointing at real NASA data
# --------------------------------------------------------------------------


class TableRef(_Strict):
    """One PSI experimental table."""

    psi_id: str = Field(examples=["PSI-69"])
    file_name: str = Field(examples=["PSI-69_Experimental table_FLEX.csv"])
    doi: str | None = None
    n_rows: int | None = Field(default=None, description="Rows actually used, after exclusions.")


class TestRef(_Strict):
    """One real test: a single row of a PSI experimental table.

    (psi_id, file_name, row) is the key the whole project uses for a test row.
    `row` is the spreadsheet row number: the header is row 1, the first test
    is row 2. ignis_ml.raw.read_raw_table produces exactly this numbering.
    """

    psi_id: str
    file_name: str
    row: int = Field(ge=2)
    doi: str | None = None
    distance: float | None = Field(
        default=None, ge=0, description="Scaled distance from the query; smaller is closer."
    )
    values: dict[str, str] = Field(
        default_factory=dict,
        description="Cell text copied verbatim from the table, keyed by its column header.",
    )


# --------------------------------------------------------------------------
# What each model is and where it is valid
# --------------------------------------------------------------------------


class FeatureSpec(_Strict):
    name: str = Field(description="Canonical input name, e.g. o2_mole_fraction.")
    kind: Literal["numeric", "categorical"]
    unit: str | None = None
    tested_min: float | None = Field(default=None, description="Smallest value in the training rows.")
    tested_max: float | None = Field(default=None, description="Largest value in the training rows.")
    categories: list[str] | None = Field(default=None, description="Values seen, for categorical inputs.")
    source_column: str | None = Field(default=None, description="Column header in the PSI table.")


class Metric(_Strict):
    name: str = Field(examples=["macro_f1", "mae"])
    value: float
    baseline_name: str | None = Field(default=None, examples=["majority class", "mean"])
    baseline_value: float | None = None


class ModelCard(_Strict):
    model_id: ModelId
    title: str
    status: Literal["available", "not_implemented"]
    fuel_class: Literal["droplet", "gas", "solid"]
    task: Literal["regression", "classification", "matcher"]
    target: str
    target_unit: str | None = None
    classes: list[str] | None = None
    features: list[FeatureSpec] = []
    trained_on: list[TableRef] = []
    evaluation: list[Metric] = []
    cv_scheme: str | None = Field(default=None, examples=["GroupKFold by test date"])
    version: str | None = None
    notes: str | None = None


# --------------------------------------------------------------------------
# Predictions (measured-data models)
# --------------------------------------------------------------------------


class PredictRequest(_Strict):
    model_id: ModelId
    inputs: dict[str, float | str] = Field(description="Keyed by FeatureSpec.name, in the units above.")
    n_nearest: int = Field(default=5, ge=0, le=25)


class RangeViolation(_Strict):
    """An input outside what NASA tested, or a category never tested."""

    feature: str
    value: float | str
    tested_min: float | None = None
    tested_max: float | None = None
    categories: list[str] | None = None


class Prediction(_Strict):
    # regression
    value: float | None = None
    unit: str | None = None
    low: float | None = None
    high: float | None = None
    # classification
    label: str | None = None
    class_probabilities: dict[str, float] | None = None


class PredictResponse(_Strict):
    """Result of one prediction.

    status
        ok               a prediction is given
        withheld         an input is outside the tested range; no prediction,
                         out_of_range says why
        invalid_input    a required input is missing or malformed
        not_implemented  the model is not built yet
    """

    status: Literal["ok", "withheld", "invalid_input", "not_implemented"]
    model_id: ModelId
    kind: Literal["model_prediction"] = "model_prediction"
    prediction: Prediction | None = None
    out_of_range: list[RangeViolation] = []
    nearest_tests: list[TestRef] = []
    message: str | None = None
    model_version: str | None = None

    @model_validator(mode="after")
    def _prediction_only_when_ok(self) -> "PredictResponse":
        if self.status == "ok" and self.prediction is None:
            raise ValueError("status 'ok' needs a prediction")
        if self.status != "ok" and self.prediction is not None:
            raise ValueError(f"status '{self.status}' must not carry a prediction")
        if self.status == "ok" and self.out_of_range:
            raise ValueError("an out-of-range input means the prediction is withheld")
        if self.status == "withheld" and not self.out_of_range:
            raise ValueError("status 'withheld' needs at least one out_of_range entry")
        return self


# --------------------------------------------------------------------------
# Simulation (physics engine, drives the 6.4 combustion lab)
# --------------------------------------------------------------------------


class SimulateRequest(_Strict):
    scenario: Literal["droplet", "solid"]
    fuel: str = Field(examples=["heptane", "methanol", "pmma"])
    gravity_g: float = Field(ge=0, le=1)
    pressure_kpa: float = Field(gt=0)
    o2_mole_fraction: float = Field(ge=0, le=1)
    co2_mole_fraction: float = Field(default=0, ge=0, le=1)
    he_mole_fraction: float = Field(default=0, ge=0, le=1)
    flow_cm_s: float = Field(default=0, ge=0)
    droplet_diameter_mm: float | None = Field(default=None, gt=0, description="Droplet scenario only.")
    sample_thickness_mm: float | None = Field(default=None, gt=0, description="Solid scenario only.")

    @model_validator(mode="after")
    def _fractions_fit(self) -> "SimulateRequest":
        # Nitrogen is the balance, so the named gases cannot exceed the whole.
        if self.o2_mole_fraction + self.co2_mole_fraction + self.he_mole_fraction > 1 + 1e-9:
            raise ValueError("oxygen, CO2 and helium mole fractions add up to more than 1")
        return self


class CurvePoint(_Strict):
    t_s: float
    d2_mm2: float = Field(description="Droplet diameter squared.")


class SimState(_Strict):
    """What the simplified physics says at one gravity level."""

    gravity_g: float
    sustains: bool
    regime: Literal["burning", "quench_low_flow", "blowoff", "below_oxygen_limit", "diluent_extinction"]
    burning_rate_mm2_s: float | None = None
    burn_time_s: float | None = None
    flame_standoff_ratio: float | None = Field(default=None, description="Flame diameter / droplet diameter.")
    d2_curve: list[CurvePoint] | None = None


class SimulateResponse(_Strict):
    """Result of one physics-engine run. Always simulated, never a measurement.

    At 0 g or 1 g, `state` holds the result. Between them PSI has no data, so
    `state` is empty and `bounds` holds the 0 g and 1 g results that bracket
    it; `message` says so.
    """

    status: Literal["ok", "invalid_input", "not_implemented"]
    kind: Literal["simulated"] = "simulated"
    state: SimState | None = None
    bounds: list[SimState] = []
    calibrated_on: list[TableRef] = []
    nearest_tests: list[TestRef] = []
    assumptions: list[str] = []
    message: str | None = None
    engine_version: str | None = None

    @model_validator(mode="after")
    def _state_or_bounds(self) -> "SimulateResponse":
        if self.status != "ok":
            if self.state is not None or self.bounds:
                raise ValueError(f"status '{self.status}' must not carry results")
            return self
        if (self.state is None) == (not self.bounds):
            raise ValueError("an ok result has either a state or a pair of bounds, not both or neither")
        if self.bounds and sorted(s.gravity_g for s in self.bounds) != [0.0, 1.0]:
            raise ValueError("bounds are the 0 g and 1 g results")
        return self
