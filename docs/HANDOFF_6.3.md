# Handoff: feature 6.3, predictive models and physics engine

For @VDT37 and the coding session that will build 6.3. Written 15 Nov 2026 by the session that set the repository up, with `main` at commit `a6a362f`. If this file and the repository disagree, the repository is right.

To start a session: open it on `ankathakanksha21/ignis-core` and say "Read docs/HANDOFF_6.3.md and start on the first task."

## 1. The situation in five lines

- The project is "Flame in Freefall", a NASA Space Apps 2026 dashboard over NASA's microgravity combustion experiments (the PSI repository).
- Two people build it. @ankathakanksha21 builds the dashboard (features 6.1, 6.2, 6.4, 6.5 and data ingest). You build 6.3: the predictive models and a simplified physics engine.
- Your work is a standalone Python package, `ml/` (`ignis_ml`). It needs no backend, frontend, Node or API key.
- The rest of the app calls three functions in `ml/src/ignis_ml/api.py`. On `main` they answer `not_implemented`. Your job is to make them real without changing their signatures.
- The data is already in the repository at `data/raw/`. Nothing to download, nothing to wait for.

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

| # | Branch | What | Data |
| --- | --- | --- | --- |
| 1 | `feat/6.3-flex-burning-rate` | Regression: droplet burning rate. Also sets up the shared pieces: typed FLEX features, range check, nearest-test lookup, training entry point. | FLEX, PSI-69 |
| 2 | `feat/6.3-flex-extinction` | Classification: test end (Extinction, Disruption, Completion). | FLEX, PSI-69 |
| 3 | `feat/6.3-physics-d2` | `simulate()` for the droplet scenario: the d² law, calibrated on FLEX burning rates. | FLEX, PSI-69 |
| 4 | `feat/6.3-cfig-ignition` | A CFI-G model. Read section 6 first: the planned cool-flame target has almost no labels. | CFI-G, PSI-159 |
| 5 | `feat/6.3-solid-matcher` | Nearest real tests for a solid-fuel query. A matcher, not a trained model. | BASS-II PSI-25, Saffire PSI-98, -99, -100 |
| 6 | `feat/6.3-physics-solid` | `simulate()` for the solid scenario: flammability boundary with quenching at low flow and blowoff at high flow. | Saffire, BASS-II |

Step 3 is early on purpose. The combustion lab (6.4) is the one dashboard feature that cannot work without 6.3, and the droplet d² law is the smallest thing that gives it something real to draw.

### Done means, for every model

- `model_cards()` reports it as `available`, with:
  - each input's tested range or categories, computed from the training rows;
  - `trained_on` with PSI id, file name, DOI and the number of rows used;
  - evaluation against a baseline (mean, or majority class) and the cross-validation scheme;
  - `notes` listing every row left out and why.
- `predict()` checks the inputs in code before the model runs. Out of range returns `withheld` with `out_of_range` filled in. A missing or malformed input returns `invalid_input`.
- `nearest_tests` point at real rows by `(psi_id, file_name, row)`, with cell values copied verbatim.
- Inputs and outputs use the contract's units: mole fraction, kPa, cm/s, mm, s, mm²/s.
- Training is deterministic from `data/raw/` with a fixed seed. No trained model files are committed. Library versions are pinned exactly in `ml/pyproject.toml`.
- Tests in `ml/tests/` cover: an in-range query is `ok`; an out-of-range query is `withheld` and names the input; an untested fuel is `withheld`; every cited row exists.
- Weak results are reported as they are, not hidden.

## 5. What the data looks like

All of this was computed from `data/raw/` on 15 Nov 2026 through `ignis_ml.raw.read_raw_table`. Every cell arrives as text.

### FLEX, `read_raw_table("PSI-69")`, 274 tests

- The file is Windows-1252, not UTF-8. The reader handles it.
- Headers lost their subscripts. `O initial ambient composition` is O2, `N` is N2, and `CO` is CO2: it reaches 0.7 mole fraction, which only makes sense for the suppressant. `Burning rate; mm` has lost the rest of its unit; the values (0.05 to 1.06) fit mm²/s, but confirm against the PSI-69 documents.
- Fuel: Methanol 157, Heptane 117. The two fuels cover nearly the same ranges.
- Test end: Extinction 186, Disruption 61, Completion 27. Heptane is 60 / 38 / 19, methanol 126 / 23 / 8.
- Burning rate is filled in 258 rows. The 16 empty ones are 8 Disruption and 8 Extinction.
- Pressure is 526.3 to 2319.9 mmHg, plus one row at 0 (row 115, test 114), which is not a real pressure. Leave it out and say so in the card.
- Pressure is very uneven: 103 tests near 0.7 atm, 161 near 1.0 atm, and only 9 above that (2.0, 2.7 and 3.1 atm).
- O2 takes 15 distinct values from 0.12 to 0.34. CO2 is above zero in 123 rows (up to 0.7), helium in 50 rows (up to 0.45). No test has both CO2 and helium.
- The four gas fractions add to 1.00 in 245 rows and to between 0.98 and 1.01 in the rest.
- Droplet diameter is a number in 262 rows; 6 hold a dash character and 6 are empty. Extinction diameter is a number in 197 rows. Burn time has two entries written `~6` and `~9`.
- There are 80 distinct test dates, and only about 80 distinct combinations of fuel, pressure and gas mixture across the 273 usable rows. Most tests are repeats of a condition.

Two consequences:

- **Cross-validation.** Repeats of one condition can fall on different days, so grouping by test date alone still leaks. Group by condition (fuel, pressure level, gas mixture) or compare both groupings.
- **The range check.** A check of each input against its own minimum and maximum would accept 2.5 atm, or CO2 together with helium, where NASA has almost no tests or none. See open question 1.

### CFI-G, PSI-159, two tables

`read_raw_table("PSI-159")` raises because there are two files. Pass the file name.

`PSI-159_Experimental table_CFI-G_Normal Flames.csv`, 179 tests:

- `Hot ignition`: Yes 132, No 47. Filled in every row.
- `Self-ext or flow term`: SE 102, FT 31, `-` 46. The `-` rows are the tests with no hot ignition.
- `Fuel` has six values, some diluted: 30% butane 52, 30% propane 36, 50% butane 30, 30% ethane 27, propane 20, ethane 14.
- `' XO2 before test'` (note the leading space) runs 0.18 to 0.40. `approx p (bar)` runs 0.51 to 3.04. `Day` runs 1 to 11 and works as a grouping key.
- `Tad (K)` and `Zst` each have 2 cells that are not numbers; `Peak burner T (C )` has 46.

`PSI-159_Experimental table_CFI-G_Inverse Flames.csv`, 154 tests:

- The file has 861 empty rows. The reader drops them and keeps the row numbers of the rest.
- `XO2` runs 0.12 to 0.85. This is the highest-oxygen data in PSI.
- `Hot ignition` needs normalising: Yes 114, yes 17, No 13, no 2, flash 8. `Flame Type` is spelled both `inverse` and `Inverse`.
- The oxygen and fuel columns are swapped relative to the Normal table (`Xf before test` here, `XO2 before test` there), so the two tables do not stack without care.

### Solids

- BASS-II, PSI-25, 129 tests: 51 distinct free-text material descriptions with the size inside the text (`100 micron PMMA film   2 cm wide`), six investigators, initial O2 13.6 to 22.2 percent. There is no outcome column.
- Saffire-II, PSI-99, 15 tests: burn lengths are text (`~ 0`, `29 cm`, `Complete`), units sit inside the cells (`20 cm/s`, `~ 21.5`), the `µ` in two headers arrived as `?`, and one row has an empty material.
- Saffire-I has 4 tests and Saffire-III has 2.

## 6. A problem with the plan: the cool-flame labels

The problem statement plans a "cool flame occurrence" classifier on CFI-G with "labels in the table". They are not there.

- In the Normal table, `Cool flame?` is filled in 8 of 179 rows (7 yes, 1 no), all 30% butane, rows 159 to 170.
- Nine more rows mention cool flames in `Comments` (`Cool flame!`, `direct cool - no hot ignition`, `No cool flame detected.`).
- The Inverse table has no cool-flame column at all.
- An empty cell is not a "no". Treating it as one would break the rule that unknown is never shown as safe.

So a cool-flame classifier cannot be trained from this table. Recommended instead, for step 4: predict **hot ignition** (yes or no), which is labelled in every row of both tables, and optionally self-extinguished against flow-terminated among the flames that ignited. Leave `cfig_cool_flame` as `not_implemented`, with a note in its card giving the label count.

This changes the feature list, so agree it with @ankathakanksha21 before building. A new model id is a change to `contract.py`, which goes in its own pull request.

## 7. Open questions for the two of you

1. **Untested combinations.** The contract's `withheld` status is driven by per-input ranges. FLEX shows why that is too weak (section 5). A second guard is to withhold when the nearest real test is further than a threshold. The contract currently has no way to say "this combination was never tested", so that needs a small addition. Worth settling before model 1 merges.
2. **Two "nearest tests".** The dashboard's similar-conditions search (6.1) and your `nearest_tests` both rank real tests by closeness. Built separately they can disagree for the same query. Decide whether one distance function serves both.
3. **Is `SimState` enough for the lab?** It carries sustains, regime, burning-rate constant, burn time, flame standoff ratio and the d² curve. Add fields before step 3 if the lab needs more.
4. **The cool-flame model** (section 6).
5. **Who builds the Models page.** Default: the dashboard side builds the UI against `/api/models` and `/api/predict`; you deliver the package.

## 8. How the work flows

```
git switch main && git pull && git switch -c feat/6.3-flex-burning-rate
... work, commit, push ...
git fetch origin && git merge origin/main
cd ml && pytest
open a pull request into main, wait for CI, squash and merge, delete the branch
```

- Merge every few hours. A model that is honest about weak results is mergeable.
- Never push to `main` directly. Never edit `data/raw/` by hand.
- After a squash merge, start a new branch from `main`. Do not keep working on the merged one.
- The branch `claude/determined-rubin-boyrgi` holds one commit that touches only `.env.example`. It does not affect 6.3.

## 9. First task

```bash
pip install -e "ml[dev]" && cd ml && pytest
```

All 36 tests should pass. Then start branch 1:

1. Add a module that turns the FLEX table into typed, unit-converted features, keeping `psi_id`, `file_name`, `row` on every row and recording each row it leaves out and why.
2. Build the range check and the nearest-test lookup on those features. Models 2 and 3 reuse both.
3. Fit ridge regression as the baseline and gradient-boosted trees as the main model for burning rate, with grouped cross-validation, and compare both against predicting the mean.
4. Fill in `model_cards()` and `predict()` for `flex_burning_rate`, with the tests listed in section 4.
