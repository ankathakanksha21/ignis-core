"""The solid-fuel matcher, through the public api."""

import pytest

from ignis_ml import api
from ignis_ml.contract import PredictRequest
from ignis_ml.features.solids import OTHER, load_solids, material_families
from ignis_ml.raw import read_raw_table


def ask(n_nearest=5, **inputs):
    return api.predict(PredictRequest(model_id="solid_flame_spread", inputs=inputs, n_nearest=n_nearest))


@pytest.fixture(scope="module")
def card():
    return next(card for card in api.model_cards() if card.model_id == "solid_flame_spread")


def test_a_material_family_comes_only_from_a_word_in_the_cell():
    assert material_families("1 cm wide PMMA 2 mm thick") == ["pmma"]
    assert material_families("Cotton-Fiberglass (SIBAL)") == ["sibal"]
    assert material_families("PMMA & Nomex") == ["pmma", "nomex"]
    assert material_families("Japan Wax candle") == ["wax"]
    assert material_families('1/4" black rod') == ["rod"]  # the cell does not say what the rod is made of
    assert material_families("4 cm spherical section") == [OTHER]


def test_only_real_tests_with_a_material_and_an_oxygen_level_are_searched():
    solids = load_solids()
    assert {acronym: n for _, _, acronym, n in solids.tables} == {"BASS-II": 112, "SAFFIRE-I": 2, "SAFFIRE-II": 7}
    reasons = {(item.acronym, item.reason) for item in solids.left_out}
    assert reasons == {
        ("BASS-II", "flagged by ingest"),
        ("SAFFIRE-II", "material not stated"),
        ("SAFFIRE-III", "oxygen not stated"),
    }
    # Saffire's footnote and flow-visualisation rows are not tests and are never searched.
    saffire_rows = set(solids.frame.loc[solids.frame["psi_id"] == "PSI-99", "row"])
    assert saffire_rows <= set(range(2, 11))


def test_the_card_is_a_matcher_with_no_evaluation(card):
    assert (card.status, card.task, card.fuel_class) == ("available", "matcher", "solid")
    assert card.evaluation == [] and card.cv_scheme is None
    assert {table.psi_id for table in card.trained_on} == {"PSI-25", "PSI-98", "PSI-99"}
    assert all(table.doi for table in card.trained_on)
    assert sum(table.n_rows for table in card.trained_on) == 121
    assert "never says whether a sample would burn" in card.notes
    by_name = {feature.name: feature for feature in card.features}
    assert {"pmma", "sibal", "rod"} <= set(by_name["material"].categories)
    assert (by_name["o2_mole_fraction"].tested_min, by_name["o2_mole_fraction"].tested_max) == (0.136, 0.222)


def test_an_in_range_query_returns_real_tests_and_no_outcome():
    response = ask(material="PMMA", o2_mole_fraction=0.21)
    assert response.status == "ok"
    assert response.prediction.model_dump(exclude_none=True) == {}
    assert "No outcome is predicted" in response.message
    assert len(response.nearest_tests) == 5
    distances = [test.distance for test in response.nearest_tests]
    assert distances == sorted(distances)


def test_every_cited_row_exists_and_its_cells_are_verbatim():
    for response in [ask(n_nearest=25, material="sibal", o2_mole_fraction=0.21), ask(material="silicone", o2_mole_fraction=0.22)]:
        assert response.nearest_tests
        for test in response.nearest_tests:
            raw = read_raw_table(test.psi_id, test.file_name).set_index("row")
            assert test.doi
            for column, cell in test.values.items():
                assert raw.at[test.row, column] == cell


def test_one_material_is_matched_across_investigations():
    cited = ask(n_nearest=25, material="sibal", o2_mole_fraction=0.216).nearest_tests
    assert {"PSI-25", "PSI-98", "PSI-99"} <= {test.psi_id for test in cited}


def test_a_test_naming_two_materials_is_found_under_both():
    for material in ("pmma", "nomex"):
        cited = ask(n_nearest=25, material=material, o2_mole_fraction=0.221).nearest_tests
        assert any((test.psi_id, test.values.get("Material")) == ("PSI-99", "PMMA & Nomex") for test in cited)


def test_exploration_atmosphere_oxygen_is_withheld_and_the_gap_is_shown():
    # No solid in these tables was tested above 22.2 percent oxygen.
    response = ask(material="sibal", o2_mole_fraction=0.30)
    assert response.status == "withheld" and response.prediction is None
    violation = response.out_of_range[0]
    assert (violation.feature, violation.tested_max) == ("o2_mole_fraction", 0.222)
    assert response.nearest_tests and "gap" in response.message


def test_oxygen_is_checked_for_the_chosen_material():
    assert ask(material="pmma", o2_mole_fraction=0.18).status == "ok"
    response = ask(material="silicone", o2_mole_fraction=0.18)
    assert response.status == "withheld"
    assert (response.out_of_range[0].tested_min, response.out_of_range[0].tested_max) == (0.215, 0.221)


def test_an_untested_material_is_withheld():
    response = ask(material="wood", o2_mole_fraction=0.21)
    assert response.status == "withheld"
    assert response.out_of_range[0].feature == "material"
    assert response.nearest_tests == []


@pytest.mark.parametrize(
    "inputs",
    [{"material": "pmma"}, {"material": "pmma", "o2_mole_fraction": "0.21"}, {"material": "pmma", "o2_mole_fraction": 0.21, "flow_cm_s": 20.0}],
    ids=["missing input", "number sent as text", "unknown input"],
)
def test_a_malformed_request_is_invalid_input(inputs):
    response = api.predict(PredictRequest(model_id="solid_flame_spread", inputs=inputs))
    assert response.status == "invalid_input" and response.prediction is None
