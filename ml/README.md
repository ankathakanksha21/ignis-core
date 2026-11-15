# ignis_ml: the models and the physics engine

A standalone Python package. It needs no backend, no frontend and no API key.

## What is in it

| Piece | What it does |
| --- | --- |
| `flex_burning_rate` | Predicts how fast a fuel droplet burns, from NASA's FLEX tests. |
| `flex_extinction` | Predicts whether a droplet flame puts itself out. |
| `cfig_hot_ignition` | Predicts whether a gas flame ignites hot, from the CFI-G tests. |
| `solid_flame_spread` | Finds the nearest real solid-fuel tests. It predicts nothing. |
| Droplet physics | Simulates a burning droplet with the d² law, for the lab. |

Every model answers only inside the conditions NASA tested, and cites the real test rows nearest to the question.

## Run it

```bash
pip install -e "ml[dev]"
cd ml && pytest
```

```bash
python -m ignis_ml.train
```

The second command trains every model from `data/raw/` and prints its scores. Training takes seconds, so no trained model is stored in the repository.

## How the app uses it

Three functions in `src/ignis_ml/api.py`, with their types in `src/ignis_ml/contract.py`:

```python
model_cards() -> list[ModelCard]
predict(PredictRequest) -> PredictResponse
simulate(SimulateRequest) -> SimulateResponse
```

## Layout

```
src/ignis_ml/
  api.py          the three public functions
  contract.py     request and response types, with the units
  raw.py          reads NASA's tables
  features/       raw text to typed inputs
  models/         one module per model
  physics/        the droplet d² law
  train.py        python -m ignis_ml.train
```
