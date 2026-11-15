"""The droplet scenario of simulate(): the d-squared law tied to FLEX."""

import statistics

import pytest

from ignis_ml import api
from ignis_ml.contract import PredictRequest, SimulateRequest
from ignis_ml.models import flex_burning_rate
from ignis_ml.physics import droplet
from ignis_ml.raw import read_raw_table

BASE = dict(
    scenario="droplet", fuel="methanol", gravity_g=0, pressure_kpa=101.3,
    o2_mole_fraction=0.21, droplet_diameter_mm=3.0,
)  # fmt: skip


def run(**changes):
    return api.simulate(SimulateRequest(**{**BASE, **changes}))


def test_an_in_range_run_is_ok_and_labelled_simulated():
    response = run()
    assert response.status == "ok" and response.kind == "simulated"
    assert response.bounds == []
    state = response.state
    assert (state.gravity_g, state.sustains, state.regime) == (0.0, True, "burning")
    assert state.burning_rate_mm2_s > 0 and state.burn_time_s > 0
    assert state.flame_standoff_ratio is None
    assert response.message.startswith("Simulated, not measured.")
    assert response.engine_version == droplet.ENGINE_VERSION


def test_the_engine_and_the_model_give_the_same_burning_rate():
    inputs = {
        "fuel": "methanol", "o2_mole_fraction": 0.21, "co2_mole_fraction": 0.0,
        "he_mole_fraction": 0.0, "pressure_kpa": 101.3, "droplet_diameter_mm": 3.0,
    }  # fmt: skip
    predicted = api.predict(PredictRequest(model_id="flex_burning_rate", inputs=inputs)).prediction.value
    assert run().state.burning_rate_mm2_s == predicted


def test_the_curve_is_a_straight_line_from_the_start_to_the_flame_out_point():
    response = run()
    state, curve = response.state, response.state.d2_curve
    assert (curve[0].t_s, curve[0].d2_mm2) == (0.0, 9.0)
    assert curve[-1].t_s == pytest.approx(state.burn_time_s, abs=1e-3)
    for before, after in zip(curve, curve[1:]):
        slope = (after.d2_mm2 - before.d2_mm2) / (after.t_s - before.t_s)
        assert slope == pytest.approx(-state.burning_rate_mm2_s, abs=2e-3)

    # The flame-out point is the median of the cited tests, read from their raw cells.
    ratios = [
        float(test.values["Visible flame extinction diameter; mm"]) / float(test.values["Droplet initial diameter; mm"])
        for test in response.nearest_tests
    ]
    assert len(ratios) == droplet.N_NEAREST
    assert curve[-1].d2_mm2 == pytest.approx((statistics.median(ratios) * 3.0) ** 2, abs=1e-3)
    assert 0 <= curve[-1].d2_mm2 < 9.0


def test_more_oxygen_burns_faster():
    assert run(o2_mole_fraction=0.30).state.burning_rate_mm2_s > run(o2_mole_fraction=0.18).state.burning_rate_mm2_s


def test_a_missing_droplet_size_uses_the_median_flex_droplet_and_says_so():
    response = run(droplet_diameter_mm=None)
    train = flex_burning_rate.fitted().train
    median = train.loc[train["fuel"] == "methanol", "droplet_diameter_mm"].median()
    assert response.state.d2_curve[0].d2_mm2 == pytest.approx(median**2, abs=1e-3)
    assert any("No droplet size was given" in line for line in response.assumptions)
    assert not any("No droplet size was given" in line for line in run().assumptions)


def test_every_simplification_is_listed_and_the_calibration_is_cited():
    response = run()
    text = " ".join(response.assumptions)
    for phrase in ["d-squared law", "flex_burning_rate", "flame goes out", "Microgravity", "Check against FLEX"]:
        assert phrase in text
    table = response.calibrated_on[0]
    assert (table.psi_id, table.doi) == ("PSI-69", "10.60555/mbq8-0451")
    assert table.n_rows == len(flex_burning_rate.fitted().train)


def test_the_law_reproduces_measured_flex_burn_times():
    tests, agreement = droplet.law_check()
    assert tests > 100
    assert 0.85 < agreement < 1.05


@pytest.mark.parametrize("gravity", [0.16, 0.38, 1.0])
def test_other_gravity_levels_are_not_simulated(gravity):
    response = run(gravity_g=gravity)
    assert response.status == "not_implemented"
    assert response.state is None and response.bounds == []
    assert "microgravity" in response.message


@pytest.mark.parametrize(
    ("changes", "named"),
    [
        ({"o2_mole_fraction": 0.5}, "o2_mole_fraction 0.5 (tested 0.12 to 0.34)"),
        ({"fuel": "ethanol"}, "fuel 'ethanol' (tested: heptane, methanol)"),
        ({"co2_mole_fraction": 0.1, "he_mole_fraction": 0.1}, "he_mole_fraction"),
        ({"flow_cm_s": 5.0}, "airflow"),
    ],
    ids=["oxygen out of range", "untested fuel", "CO2 with helium", "airflow"],
)
def test_conditions_flex_did_not_test_are_refused_with_the_reason(changes, named):
    response = run(**changes)
    assert response.status == "invalid_input" and response.state is None
    assert named in response.message


def test_the_solid_scenario_is_not_built():
    response = run(scenario="solid", fuel="pmma", droplet_diameter_mm=None)
    assert response.status == "not_implemented" and response.kind == "simulated"


def test_every_cited_row_exists_and_its_cells_are_verbatim():
    raw = read_raw_table("PSI-69").set_index("row")
    for response in [run(), run(fuel="heptane", o2_mole_fraction=0.3, pressure_kpa=71.0), run(o2_mole_fraction=0.5)]:
        assert response.nearest_tests
        for test in response.nearest_tests:
            assert (test.psi_id, test.file_name) == ("PSI-69", "PSI-69_Experimental table_FLEX.csv")
            for column, cell in test.values.items():
                assert raw.at[test.row, column] == cell


def test_no_positive_burning_rate_means_the_flame_does_not_sustain(monkeypatch):
    monkeypatch.setattr(flex_burning_rate, "estimate", lambda fit, values: 0.0)
    plain, diluted = run().state, run(co2_mole_fraction=0.3).state
    assert (plain.sustains, plain.regime, plain.d2_curve) == (False, "below_oxygen_limit", None)
    assert (diluted.sustains, diluted.regime) == (False, "diluent_extinction")
