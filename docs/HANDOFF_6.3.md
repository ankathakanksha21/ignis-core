# Handoff: feature 6.3, predictive models and physics engine

For @VDT37 and the coding session that will build 6.3. Written 15 Nov 2026 and revised the same day, after step 1 was built and data ingest was merged into `main`. If this file and the repository disagree, the repository is right.

To start a session: open it on `ankathakanksha21/ignis-core` and say "Read docs/HANDOFF_6.3.md and start on the first task."

## 1. The situation

- The project is "Flame in Freefall", a NASA Space Apps 2026 dashboard over NASA's microgravity combustion experiments (the PSI repository).
- Two people build it. @ankathakanksha21 builds the dashboard (features 6.1, 6.2, 6.4, 6.5 and data ingest). You build 6.3: the predictive models and a simplified physics engine.
- Your work is a standalone Python package, `ml/` (`ignis_ml`). It needs no backend, frontend, Node or API key.
- The rest of the app calls three functions in `ml/src/ignis_ml/api.py`. `flex_burning_rate` and the droplet scenario of `simulate()` are real on `main`. `cfig_hot_ignition` is built on branch `feat/6.3-cfig-ignition`. The other models and the solid scenario still answer `not_implemented`, which is a valid response the dashboard already handles.
- The plan is one model per fuel class (droplet, gas, solid), as the problem statement says.
- The data is already in the repository at `data/raw/`. Nothing to download.
- Ingest has landed. `data/processed/quality_flags.csv` lists the suspicious cells, and the models leave flagged rows out of training. `data/processed/rows.csv` marks each raw row as `test`, `summary` or `other`.

## 2. Read these, in this order

| File | What it gives you |
| --- | --- |
| `CLAUDE.md` | Ownership, commands and product rules. Loaded automatically. |
| `ml/README.md` | Setup, how to read the data, conventions for this package. |
| `docs/CONTRACTS.md` | Units, the test-row key, the response statuses, how to change the contract. |
| `ml/src/ignis_ml/contract.py` | The exact request and response types. |
| `data/README.md` | Quirks of the PSI tables. |
| `docs/PROBLEM_STATEMENT.md` section 6.3 | The model plan. Section 7 has the rules every output must obey. |
| `CONTRIBUTING.md` | Branches, pull requests, what to do on a conflict. |

## 3. Your area

Yours to edit freely:

```
ml/                                  everything except the two files below
backend/app/routers/predict.py       the thin HTTP adapter over ignis_ml
data/labels/                         labels mined from NASA reports
```

Shared, change only in a pull request of their own that the other person approves:

```
ml/src/ignis_ml/contract.py    ml/src/ignis_ml/raw.py    docs/CONTRACTS.md
data/raw/                      scripts/fetch_psi.py      .github/
```

Not yours: the rest of `backend/`, all of `frontend/`, `data/processed/`.

## 4. What to build, in order

One short branch per line, each merged by pull request before the next starts.

| # | Branch | Fuel | What | Status |
| --- | --- | --- | --- | --- |
| 1 | `feat/6.3-flex-burning-rate` | droplet | Regression of droplet burning rate on FLEX (PSI-69), plus the shared pieces. | Merged. |
| 2 | `feat/6.3-physics-d2` | droplet | `simulate()` for the droplet scenario using the d² law, calibrated on FLEX. | Merged. The combustion lab (6.4) can call it. |
| 3 | `feat/6.3-cfig-ignition` | gas | Classification of hot ignition (yes or no) on the CFI-G Normal Flames table only (PSI-159, 179 tests, label filled in every row). | Built on `feat/6.3-cfig-ignition`, on top of the contract branch `contract/add-cfig-hot-ignition`. Merge the contract pull request first. |
| 4 | `feat/6.3-solid-matcher` | solid | Nearest real tests for a solid-fuel query over BASS-II (PSI-25, 129 tests) and Saffire (PSI-98, -99, -100, 13 tests). A matcher, not a trained model. It reuses `nearest.py`. | Not started. |

### Left out on purpose

These cards stay `not_implemented`. They are picked up only if time remains.

- `flex_extinction` (test end classifier): a second droplet model, and the plan is one per fuel class. It is the cheapest to add later because features, range check and nearest tests already exist.
- Solid physics (flammability boundary with quenching and blowoff): BASS-II has no outcome column and Saffire has 13 tests, so there is nothing to calibrate it on. `simulate()` answers `not_implemented` for the solid scenario.
- The CFI-G Inverse Flames table: its labels need normalising and its oxygen and fuel columns are swapped relative to the Normal table.
- A cool-flame classifier: only 8 of 179 rows carry a label, so it cannot be trained. `cfig_cool_flame` stays `not_implemented` with the label count in its card.
- Self-extinguished against flow-terminated as a second gas target.
- Mining BASS-II outcome labels from NASA reports.

### What step 1 left for the others to reuse

- `ml/src/ignis_ml/features/flex.py`: typed, unit-converted FLEX rows with the row key. Rows flagged by ingest are left out with the reason recorded: row 115 (pressure 0 mmHg) and rows 71 and 74 (two rows sharing one test identifier).
- `ml/src/ignis_ml/flags.py`: reads `data/processed/quality_flags.csv` for one table. Use it in every new features module.
- `ml/src/ignis_ml/guards.py`: the range check. Malformed input is `invalid_input`; outside the tested range is `withheld`. Ranges are also checked per fuel, CO2 with helium is withheld because FLEX never tested both together, and a value within 1 percent of the tested width past either end is accepted (`RANGE_MARGIN`).
- `ml/src/ignis_ml/nearest.py`: nearest real tests with cells copied verbatim from the raw table.
- `ml/src/ignis_ml/models/flex_burning_rate.py`: the pattern for a model module (`MODEL_ID`, `card()`, `predict()`), registered in `_BUILT` in `api.py`.
- `python -m ignis_ml.train` prints every built model's evaluation.
- Result: 255 of 274 tests used, 78 distinct conditions, cross-validation grouped by condition. Mean absolute error is 0.048 mm²/s for ridge regression, 0.056 for gradient-boosted trees and 0.107 for predicting the mean. Ridge serves the answers because it had the lower error.
- scikit-learn is pinned to 1.9.1. XGBoost was not added.

### Done means, for every model

- `model_cards()` reports it as `available`, with each input's tested range or categories, `trained_on` (PSI id, file name, DOI, rows used), an evaluation against a baseline with the cross-validation scheme, and `notes` listing rows left out.
- Rows flagged in `data/processed/quality_flags.csv` are left out of training and listed in the card.
- `predict()` goes through `guards.py` before the model runs.
- `nearest_tests` cite real rows by `(psi_id, file_name, row)`.
- Inputs and outputs use the contract's units: mole fraction, kPa, cm/s, mm, s, mm²/s.
- Training is deterministic from `data/raw/` with a fixed seed. No trained model files are committed. Versions are pinned exactly in `ml/pyproject.toml`.
- Four tests in `ml/tests/`: an in-range query is `ok`; an out-of-range query is `withheld` and names the input; an untested category is `withheld`; every cited row exists.
- Weak results are reported as they are.

## 5. What the data looks like

Every cell arrives as text through `ignis_ml.raw.read_raw_table`.

### FLEX, `read_raw_table("PSI-69")`, 274 tests

- Headers lost their subscripts. `O initial ambient composition` is O2, `N` is N2, and `CO` is CO2 (it reaches 0.7 mole fraction, which only makes sense for the suppressant). `Burning rate; mm` has lost the rest of its unit; the values (0.05 to 1.06) fit mm²/s, but confirm against the PSI-69 documents.
- Fuel: Methanol 157, Heptane 117.
- Burning rate is filled in 258 rows.
- Pressure has one row at 0 (row 115, test 114), which is not a real pressure.
- Droplet diameter is a number in 262 rows; extinction diameter is a number in 197. Burn time has two entries written `~6` and `~9`.
- About 80 conditions repeat across the tests, so cross-validation must group by condition.

For the d² step, among tests that ended in extinction the flame went out at a median 0.57 of the initial diameter for methanol and 0.84 for heptane. The d² law's burn time, (d0² minus extinction diameter²) divided by the burning rate, is a median 0.95 of the measured burn time (101 methanol and 55 heptane tests). These were computed during planning and should be recomputed in code.

### CFI-G, PSI-159

`read_raw_table("PSI-159")` raises because there are two files. Pass the file name.

`PSI-159_Experimental table_CFI-G_Normal Flames.csv`, 179 tests:

- `Hot ignition`: Yes 132, No 47. Filled in every row.
- `Fuel` has six values, some diluted.
- `' XO2 before test'` (note the leading space) runs 0.18 to 0.40. `approx p (bar)` runs 0.51 to 3.04. `Day` runs 1 to 11 and works as a grouping key.

The Inverse Flames table is out of scope: its labels need normalising and its columns do not line up with the Normal table.

### Solids

- BASS-II, PSI-25, 129 tests: 51 distinct free-text material descriptions with the size inside the text (`100 micron PMMA film   2 cm wide`), six investigators, initial O2 13.6 to 22.2 percent. There is no outcome column.
- Saffire has 13 tests in all: Saffire-I 2, Saffire-II 9, Saffire-III 2. The other 8 rows of those tables are flow-visualisation files and footnotes, so filter on `row_kind` in `data/processed/rows.csv` before counting or matching.
- Saffire-II, PSI-99: burn lengths are text (`~ 0`, `29 cm`, `Complete`), units sit inside the cells (`20 cm/s`, `~ 21.5`), the `µ` in two headers arrived as `?`, and two tests have an empty material cell.

## 6. Open questions for the two of you

1. The gas model's id. Hot ignition is not cool flame, so it has its own id, `cfig_hot_ignition`, added to `ModelId` in `contract.py` on branch `contract/add-cfig-hot-ignition`. That is a contract change: its own pull request, approved by @ankathakanksha21, merged before the step 3 pull request.
2. What `simulate()` returns where FLEX has no data. As built in step 2: `ok` at 0 g only. Above 0 g it answers `not_implemented` with a message, because FLEX is microgravity only and there is no 1 g result to use as a bound. Outside the FLEX range, for an untested fuel, or with airflow above zero, it answers `invalid_input` with the tested range in the message, since `SimulateResponse` has no `withheld` status. `flame_standoff_ratio` is empty because the table has no flame size. Check with the dashboard side that the lab handles these, and whether `SimState` needs a flame-out diameter field (today it is the last point of the d² curve).
3. Untested combinations. Settled in step 1 without a contract change (per-fuel ranges, CO2 with helium withheld, and a caution in `message` when the closest real test is further than a scaled distance of 0.15). Revisit only if the dashboard wants a refusal there instead of a caution.

The dashboard side builds the Models page against `/api/models` and `/api/predict` (unchanged default).

## 7. How the work flows

```
git switch main && git pull && git switch -c feat/6.3-physics-d2
... work, commit, push ...
git fetch origin && git merge origin/main
cd ml && pytest
open a pull request into main, wait for CI, squash and merge, delete the branch
```

- Merge every few hours. A model that is honest about weak results is mergeable.
- Never push to `main` directly. Never edit `data/raw/` by hand.
- After a squash merge, start a new branch from `main`. Do not keep working on the merged one.

## 8. Next task

Steps 1 and 2 are merged. Step 3 is built and waits for two pull requests, in this order: `contract/add-cfig-hot-ignition`, then `feat/6.3-cfig-ignition`.

How step 2 works, in `ml/src/ignis_ml/physics/droplet.py`: the burning-rate constant is the `flex_burning_rate` model's value for the requested conditions, so the engine and the model cannot disagree. The flame-out diameter is the median over the 5 nearest real tests of the same fuel that recorded an extinction diameter, and those tests are the ones cited. Checked against FLEX, the law's burn time is a median 0.95 of the measured one across 154 tests that ended in extinction.

How step 3 turned out, in `ml/src/ignis_ml/models/cfig_hot_ignition.py`: 177 of 179 tests are used (rows 69 and 77 had no fuel flowing). Inputs are the fuel species (butane, ethane, propane), oxygen, pressure, the fuel fraction fed (`Xf`) and the fuel flow (`mHC (mg/s)`). Gradient-boosted trees serve the answers. Scored with repeats of one setup kept together, accuracy is 0.85 against 0.75 for the majority class and macro F1 is 0.78 against 0.43. Scored with a whole test day held out, it does no better than the majority class (accuracy 0.73 against 0.75). The card states this: the model fills in between settings that were run and does not carry over to a day with different settings.

Then step 4, the solid matcher, on a new branch from `main`:

1. Add a features module for BASS-II and Saffire: typed rows with the row key, only rows ingest marks as `test`, flagged rows left out through `flags.py`.
2. Add `ml/src/ignis_ml/models/solid_flame_spread.py`: no training, only `nearest.py` over the inputs both tables share (material, oxygen, flow where stated). Its card has task `matcher` and no evaluation.
3. `predict()` returns `withheld` for an untested material or an out-of-range input, and otherwise the nearest real tests. It never returns a burned or did-not-burn label, because BASS-II has no outcome column.
