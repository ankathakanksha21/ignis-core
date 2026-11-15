"""A burning fuel droplet in microgravity: the d-squared law, tied to FLEX.

The law says a burning droplet's diameter squared falls in a straight line
with time:

    d(t)^2 = d0^2 - K * t

Two numbers set the curve, and both come from FLEX (PSI-69), not from theory:

    K           the burning-rate constant, taken from the flex_burning_rate
                model for the requested conditions, so the engine and the
                model cannot disagree;
    flame-out   the diameter at which the flame goes out, as a fraction of the
                starting diameter: the median over the nearest real tests of
                the same fuel that recorded an extinction diameter.

The burn lasts until the droplet reaches the flame-out diameter. Nothing is
simulated outside what FLEX tested: other gravity levels, airflow, untested
fuels or gas mixtures get a refusal that says why.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache

import numpy as np
import pandas as pd

from ..contract import CurvePoint, RangeViolation, SimState, SimulateRequest, SimulateResponse, TestRef
from ..features.flex import SOURCE_COLUMNS
from ..guards import check_inputs
from ..models import flex_burning_rate as burning_rate
from ..nearest import cite, rank_tests

ENGINE_VERSION = "0.1.0"
N_NEAREST = 5
CURVE_POINTS = 21

CITED_COLUMNS = [
    *burning_rate.CITED_COLUMNS,
    SOURCE_COLUMNS["extinction_diameter_mm"],
    SOURCE_COLUMNS["burn_time_s"],
]


def _flame_out_pool(train: pd.DataFrame) -> pd.DataFrame:
    """Training rows that recorded where the flame went out, with that point
    as a fraction of the starting diameter. A row whose extinction diameter
    is not below its starting diameter cannot be used."""
    ratio = train["extinction_diameter_mm"] / train["droplet_diameter_mm"]
    return train.assign(flame_out_ratio=ratio)[ratio.between(0, 1, inclusive="left")]


@lru_cache(maxsize=1)
def law_check() -> tuple[int, float]:
    """How well the law reproduces FLEX: (tests used, median of simulated burn
    time over measured burn time), using each test's own measured burning rate
    and extinction diameter. Only tests that ended in extinction have a burn
    time that ends where the law says it should."""
    pool = _flame_out_pool(burning_rate.fitted().train)
    pool = pool[(pool["test_end"] == "Extinction") & pool["burn_time_s"].notna()]
    simulated = (pool["droplet_diameter_mm"] ** 2 - pool["extinction_diameter_mm"] ** 2) / pool[burning_rate.TARGET]
    return len(pool), float((simulated / pool["burn_time_s"]).median())


def _describe(violation: RangeViolation) -> str:
    if violation.categories is not None:
        return f"{violation.feature} '{violation.value}' (tested: {', '.join(violation.categories)})"
    return f"{violation.feature} {violation.value:g} (tested {violation.tested_min:g} to {violation.tested_max:g})"


def _refuse(status: str, message: str, nearest: list[TestRef] | None = None) -> SimulateResponse:
    return SimulateResponse(
        status=status, message=message, nearest_tests=nearest or [], engine_version=ENGINE_VERSION
    )


def simulate(request: SimulateRequest) -> SimulateResponse:
    fit = burning_rate.fitted()
    train = fit.train

    if request.gravity_g > 0:
        return _refuse(
            "not_implemented",
            f"PSI holds no droplet tests above microgravity, so nothing is simulated at {request.gravity_g:g} g."
            " FLEX ran on the space station only.",
        )
    if request.flow_cm_s > 0:
        return _refuse(
            "invalid_input",
            "The FLEX table records no airflow, so the droplet scenario is simulated in still gas only."
            " Set flow_cm_s to 0.",
        )

    fuel = request.fuel.strip().lower()
    same_fuel = train[train["fuel"] == fuel]
    diameter = request.droplet_diameter_mm
    if diameter is None:
        diameter = float((same_fuel if len(same_fuel) else train)["droplet_diameter_mm"].median())

    checked = check_inputs(
        fit.specs,
        {
            "fuel": fuel,
            "o2_mole_fraction": request.o2_mole_fraction,
            "co2_mole_fraction": request.co2_mole_fraction,
            "he_mole_fraction": request.he_mole_fraction,
            "pressure_kpa": request.pressure_kpa,
            "droplet_diameter_mm": diameter,
        },
        train,
        presence_groups=[burning_rate.DILUENTS],
    )
    values = checked.values
    pool = _flame_out_pool(train)
    ranked = rank_tests(pool, values, fit.scales, match=burning_rate.CATEGORICAL).head(N_NEAREST)
    nearest = cite(ranked, fit.raw, CITED_COLUMNS, doi=fit.table.doi)

    if checked.violations:
        outside = "; ".join(_describe(violation) for violation in checked.violations)
        message = f"Outside the conditions NASA tested in FLEX, so nothing is simulated: {outside}."
        return _refuse("invalid_input", " ".join([message, *checked.notes]), nearest)
    if ranked.empty:
        return _refuse("not_implemented", f"No FLEX test with {fuel} recorded where the flame went out.")

    assumptions = [
        "The droplet follows the d-squared law: its diameter squared falls in a straight line with time.",
        f"The burning-rate constant is the flex_burning_rate model's value for these conditions"
        f" ({fit.served} on {len(train)} FLEX tests).",
        "Microgravity, still gas, one droplet. Soot, cool flames, droplet disruption and the flame's own"
        " radiation are not modelled.",
        "The FLEX table has no flame size, so no flame standoff ratio is given.",
    ]
    if request.droplet_diameter_mm is None:
        assumptions.append(
            f"No droplet size was given, so the median FLEX {fuel} droplet ({diameter:g} mm) is used."
        )

    rate = burning_rate.estimate(fit, values)
    if rate <= 0:
        diluted = values["co2_mole_fraction"] + values["he_mole_fraction"] > 0
        state = SimState(
            gravity_g=0.0,
            sustains=False,
            regime="diluent_extinction" if diluted else "below_oxygen_limit",
        )
        message = "Simulated, not measured. The burning-rate model gives no positive rate here, so no burn is drawn."
    else:
        ratio = float(ranked["flame_out_ratio"].median())
        flame_out = ratio * diameter
        burn_time = (diameter**2 - flame_out**2) / rate
        times = np.linspace(0.0, burn_time, CURVE_POINTS)
        state = SimState(
            gravity_g=0.0,
            sustains=True,
            regime="burning",
            burning_rate_mm2_s=round(rate, 4),
            burn_time_s=round(burn_time, 3),
            d2_curve=[CurvePoint(t_s=round(float(t), 4), d2_mm2=round(diameter**2 - rate * float(t), 4)) for t in times],
        )
        rows = ", ".join(str(row) for row in ranked["row"])
        where = (
            "The droplet burns away completely"
            if ratio == 0
            else f"The flame goes out when the droplet reaches {ratio:.2f} of its starting diameter ({flame_out:.2f} mm)"
        )
        assumptions.insert(
            2,
            f"{where}: that is the median extinction diameter of the {len(ranked)} nearest real tests"
            f" that recorded one (rows {rows}).",
        )
        tests, agreement = law_check()
        assumptions.append(
            f"Check against FLEX: with each test's own measured burning rate and extinction diameter, the law's"
            f" burn time is a median {agreement:.2f} of the measured one across {tests} tests that ended in extinction."
        )
        ends = Counter(ranked["test_end"])
        outcome = ", ".join(f"{count} in {end.lower()}" for end, count in ends.most_common())
        message = f"Simulated, not measured. Of the {len(ranked)} nearest real tests, the burn ended: {outcome}."

    return SimulateResponse(
        status="ok",
        state=state,
        calibrated_on=[fit.table],
        nearest_tests=nearest,
        assumptions=assumptions,
        message=message,
        engine_version=ENGINE_VERSION,
    )
