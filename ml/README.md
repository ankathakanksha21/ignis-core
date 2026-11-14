# ignis_ml: predictive models and physics engine (feature 6.3)

A standalone Python package. It needs no backend, no frontend, no Node and no API key, so it can be developed on a different machine from the rest of the project and pushed from there.

## Set up on any machine

```bash
git clone https://github.com/ankathakanksha21/ignis-core.git
```

```bash
cd ignis-core
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e "ml[dev]"
```

```bash
cd ml && pytest
```

The data is already in the repository (`data/raw/`), so there is nothing to download.

On Colab or Kaggle, clone the repository and run `pip install -e ignis-core/ml` in a cell. If the package cannot find the data, set the environment variable `IGNIS_REPO_ROOT` to the path of the clone.

## Reading the data

```python
from ignis_ml.raw import read_raw_table

flex = read_raw_table("PSI-69")
cfig = read_raw_table("PSI-159", "PSI-159_Experimental table_CFI-G_Normal Flames.csv")
```

Each table comes back with `psi_id`, `file_name`, `row` in front and every cell as the text PSI published. Converting to numbers is your step, and it is where values such as `~ 21.5`, `n/a` and a pressure of `0` get handled deliberately. Read [data/README.md](../data/README.md) first: FLEX is not UTF-8 and its headers have lost their subscripts.

Keep the three key columns attached to every row all the way through. They are how a prediction cites its nearest real tests.

## What the rest of the app expects

Three functions in `src/ignis_ml/api.py`, with the types in `src/ignis_ml/contract.py`:

```python
model_cards() -> list[ModelCard]
predict(PredictRequest) -> PredictResponse
simulate(SimulateRequest) -> SimulateResponse
```

On `main` they answer `not_implemented`. The 6.3 work replaces their bodies and keeps their signatures. Everything else in this package is private and can be organised however suits the work, for example:

```
src/ignis_ml/
  api.py          public functions
  contract.py     shared types (jointly owned)
  raw.py          snapshot reader (jointly owned)
  features/       raw text -> typed, unit-converted model inputs
  models/         one module per model
  physics/        d² law, solid flammability boundary
  train.py        python -m ignis_ml.train
```

[docs/CONTRACTS.md](../docs/CONTRACTS.md) has the units, the status values and the rules a response must obey. The contract types enforce the main ones: a response with an out-of-range input cannot carry a prediction.

## Conventions worth keeping

- **Pin exact library versions** in `pyproject.toml` when adding scikit-learn or XGBoost, so two machines train the same model.
- **Do not commit trained models.** `ml/artifacts/` is git-ignored. Train from `data/raw/` with a fixed seed; at this data size it takes seconds, and it avoids a pickle from one machine failing to load on another.
- **Logic goes in `src/`, exploration goes in `notebooks/`.** Clear notebook outputs before committing so diffs stay readable.
- **Report evaluation even when weak**, against the majority-class or mean baseline, with cross-validation grouped by test day or fuel. Put the numbers in the `ModelCard`.
- **The tested range is computed from the training rows** and returned in `ModelCard.features`. The UI takes its limits from there.

## Checking it inside the app

Not needed for day-to-day modelling, but to see the models through the API:

```bash
pip install -e "ml[dev]" -e "backend[dev]"
```

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000/docs and try `POST /api/predict`.
