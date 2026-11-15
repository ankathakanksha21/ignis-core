# Flame in Freefall

NASA Space Apps 2026. A web dashboard that summarizes, ranks and interprets NASA's microgravity combustion investigations (from the PSI repository) for fire safety in human space exploration.

It is a research and teaching aid, not a certified safety tool. Every number comes from code reading NASA tables, every value links to its source row, and predictions are withheld outside the conditions NASA tested.

- Problem statement and feature list: [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
- How the two of us work in parallel: [CONTRIBUTING.md](CONTRIBUTING.md)
- The contract between the two halves: [docs/CONTRACTS.md](docs/CONTRACTS.md)
- The data snapshot and what it found: [data/README.md](data/README.md)

## Layout

| Path | What | Owner |
| --- | --- | --- |
| `backend/` | FastAPI app. One router file per feature in `app/routers/`. | @ankathakanksha21 |
| `frontend/` | React app (Vite, TypeScript). One folder per feature in `src/features/`. | @ankathakanksha21 |
| `ml/` | `ignis_ml`: predictive models and the physics engine (feature 6.3). Standalone Python package. | @VDT37 |
| `backend/app/routers/predict.py` | The thin HTTP adapter over `ignis_ml`. | @VDT37 |
| `ml/src/ignis_ml/contract.py`, `raw.py`, `docs/CONTRACTS.md` | The contract. | both |
| `data/raw/` | PSI snapshot. Written only by `scripts/fetch_psi.py`. | both |
| `data/processed/` | Output of ingest. | @ankathakanksha21 |
| `data/labels/` | Labels mined from reports. | @VDT37 |

## Run it

Python 3.10 or newer and Node 20 or newer.

Backend and models:

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e "ml[dev]" -e "backend[dev]"
cd backend
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Models page lists the planned models, fetched from the backend, which shows the three parts are connected. API docs are at http://localhost:8000/docs.

Working only on the models? You need none of the above except the `ml` package. See [ml/README.md](ml/README.md).

## Tests

```bash
cd ml && pytest
```

```bash
cd backend && pytest
```

```bash
cd frontend && npm run lint && npm run build
```

CI runs all three on every pull request.

## Rebuild the processed data

`data/processed/` is built from `data/raw/`. After changing anything in `backend/app/ingest/`:

```bash
cd backend && python -m app.ingest
```

Commit the code and the rebuilt files together. A backend test fails if they disagree.

## The language-model key

Copy `.env.example` to `.env` and put the key there. `.env` is git-ignored. Never commit the key or paste it into an issue, pull request or notebook; CI fails if one appears in the tree.

## Data and citation

The experiment data is from NASA's [Physical Sciences Informatics](https://psi.nasa.gov) repository. Each investigation is cited by its DOI, listed in `data/raw/manifest.json`.
