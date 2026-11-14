# Contracts

The project is built by two people in two halves:

- **Dashboard** (features 6.1, 6.2, 6.4, 6.5): `backend/`, `frontend/`.
- **Models** (feature 6.3): `ml/`.

The halves touch in exactly two places. Data goes in to the models, and predictions and simulations come out. This document fixes both, so each half can be built and tested without the other being finished.

Read this once together before splitting up. The open questions at the end are the ones worth ten minutes of discussion now.

## 1. Data in

### The test-row key

Every test in the project is identified by three values:

```
(psi_id, file_name, row)        e.g. ("PSI-69", "PSI-69_Experimental table_FLEX.csv", 2)
```

`row` is the spreadsheet row number of the raw table: the header is row 1 and the first test is row 2. Empty rows keep their number and are skipped.

Anything that refers to a test uses this key: a model's nearest tests, a quality flag, a mined label, a citation in an answer. Because both halves use the same key, the dashboard can link a model's "nearest real experiments" straight to its own test rows without any mapping.

`ignis_ml.raw.read_raw_table(psi_id, file_name=None)` returns a table with these three columns in front and every cell as published text. Use it rather than reading the CSV yourself, so the numbering cannot drift.

### Units

Inside the code and across the API, always:

| Quantity | Unit | Field name |
| --- | --- | --- |
| Oxygen, CO2, helium, nitrogen | mole fraction, 0 to 1 | `o2_mole_fraction`, `co2_mole_fraction`, `he_mole_fraction` |
| Pressure | kPa | `pressure_kpa` |
| Flow velocity | cm/s | `flow_cm_s` |
| Gravity | multiples of Earth gravity | `gravity_g` |
| Lengths | mm | `..._mm` |
| Time | s | `..._s` |
| Burning-rate constant | mm²/s | `burning_rate_mm2_s` |

The raw tables use percent, mmHg, bar and psi in different places. Convert once, when reading the table. The UI converts back for display (percent oxygen, psi).

```
1 psi  = 6.894757 kPa      1 mmHg = 0.1333224 kPa      1 bar = 100 kPa

14.7 psi = 101.4 kPa       10.2 psi = 70.3 kPa         4.3 psi = 29.6 kPa
```

### Who reads what

The models read `data/raw/` directly, starting today. They do not wait for ingest.

When ingest lands, it writes two things the models may then use:

**`data/processed/quality_flags.csv`**, one line per suspicious cell:

```
psi_id,file_name,row,column,check,detail
PSI-69,PSI-69_Experimental table_FLEX.csv,115,"Ambient pressure; mmHg",non_physical,"pressure is 0 mmHg"
```

The dashboard shows these in the data quality view. The models leave flagged rows out of training and say how many in the model card. One file, so the two halves cannot disagree about which rows are bad. (The example is real: FLEX test 114, on row 115, is the one row with a pressure of 0 mmHg.)

**`data/labels/<name>.csv`**, written by the modelling side when labels are mined from NASA reports (BASS-II has no outcome column):

```
psi_id,file_name,row,label,source_document,source_page,quote
```

Every label carries the document and page it came from. No source, no label.

## 2. Predictions and simulations out

The models are a Python package, `ignis_ml`. The rest of the app uses three functions from `ignis_ml.api` and the types in `ignis_ml.contract`. Nothing else in `ml/` is public, so everything else can be rewritten freely.

| Function | HTTP route | Used by |
| --- | --- | --- |
| `model_cards() -> list[ModelCard]` | `GET /api/models` | Model pages, and anywhere the UI needs a model's tested ranges. |
| `predict(PredictRequest) -> PredictResponse` | `POST /api/predict` | Prediction panel (6.2, 6.3). |
| `simulate(SimulateRequest) -> SimulateResponse` | `POST /api/simulate` | Combustion lab (6.4). |

The backend route is a thin adapter in `backend/app/routers/predict.py`. With the backend running, `http://localhost:8000/docs` shows every field and lets you try calls.

### The honesty rules are in the types

A response that breaks one of these is rejected when it is built, so it cannot reach the UI:

- `PredictResponse.status` is `ok`, `withheld`, `invalid_input` or `not_implemented`. A prediction is present only when the status is `ok`.
- An input outside the tested range forces `withheld`, and `out_of_range` lists each offending input with the range NASA tested.
- `PredictResponse.kind` is always `model_prediction` and `SimulateResponse.kind` is always `simulated`. The UI labels by this field.
- A simulation between 0 g and 1 g has no single answer. It returns `bounds`, the 0 g and 1 g results, and `state` stays empty.
- `nearest_tests` and `calibrated_on` point at real rows and tables by the key above.

### The UI must handle every status from the start

On `main` all three functions answer `not_implemented`. That is a normal response, so the dashboard can be built against it now and will start showing real results the moment a model merges, with no change on the dashboard side. Build the `withheld` and `not_implemented` views first; they are the ones the project's rules are about.

### The tested range comes from the model

`ModelCard.features` gives each input's `tested_min`, `tested_max` or `categories`, computed from the rows the model was trained on. The UI uses these for slider limits and warnings. It does not compute its own.

## 3. Changing a contract

The contract files are:

```
ml/src/ignis_ml/contract.py
ml/src/ignis_ml/raw.py
docs/CONTRACTS.md
data/raw/        (and scripts/fetch_psi.py, which writes it)
```

- A change to any of them is a pull request of its own, containing only that change, approved by the other person before it merges.
- Adding an optional field is safe. Renaming or removing a field, or changing a unit, breaks the other half, so agree on it first.
- Bump `CONTRACT_VERSION` in `contract.py` when a change is not backwards compatible.
- Merge contract changes quickly and both pull `main` straight after.

## 4. Open questions to settle before splitting up

1. **Is `SimState` enough to draw the lab?** It carries whether the flame sustains, the regime, the burning-rate constant, burn time, flame standoff ratio and the d² curve. If the 2D view needs more (flame length on a solid, spread rate), add the fields now.
2. **Who builds the Models page UI?** Default: the dashboard side builds it against `/api/models` and `/api/predict`, and the modelling side only delivers the package. Say so if you would rather swap.
3. **Trained models: rebuild or commit?** Default: do not commit them. Training on a few hundred rows takes seconds, so `ignis_ml` trains from `data/raw/` with a fixed seed on first use. That avoids a pickle saved on one machine failing to load on another with a different library version.
4. **Which FLEX rows are excluded** before ingest's flags exist? Until then the modelling side applies its own obvious exclusions (for example pressure of 0 mmHg) and lists them in the model card.
5. **When does the physics engine land?** The lab (6.4) cannot show a real simulation until `simulate()` works. The droplet d² law is the small first step and gives the lab something real to draw early.
