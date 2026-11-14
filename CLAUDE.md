# Flame in Freefall

NASA Space Apps 2026 project. FastAPI backend, React frontend, and a standalone Python package for models. Two people work in parallel, each in their own folders.

Read before starting: `CONTRIBUTING.md` (workflow and ownership), `docs/CONTRACTS.md` (the boundary between the two halves), `docs/PROBLEM_STATEMENT.md` (features and rules), `data/README.md` (data quirks).

## Stay in the right area

Ask which half the session is for if it is not clear from the task.

- Dashboard work (6.1, 6.2, 6.4, 6.5, ingest): `backend/` except `app/routers/predict.py`, `frontend/`, `data/processed/`.
- Models work (6.3): `ml/`, `backend/app/routers/predict.py`, `data/labels/`.
- Contract files need both people's approval. Do not change them as part of a feature: `ml/src/ignis_ml/contract.py`, `ml/src/ignis_ml/raw.py`, `docs/CONTRACTS.md`, `data/raw/`, `scripts/fetch_psi.py`, `.github/`.

Do not reformat or restructure files outside the area being worked on. `backend/app/main.py` and `frontend/src/App.tsx` already register every feature and should not need editing.

## Commands

```bash
pip install -e "ml[dev]" -e "backend[dev]"
cd ml && pytest
cd backend && pytest
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
cd frontend && npm run lint && npm run build
```

## Rules the product follows

- Every number comes from code reading NASA tables. The language model never produces a number.
- Every displayed value links to its source: PSI id, file name, row. Read tables with `ignis_ml.raw.read_raw_table` so row numbers agree everywhere.
- Outside tested conditions, refuse and show the gap. Partial gravity is always untested.
- Missing values show as "not stated". Unknown is never shown as safe.
- Simulated output is labelled and never mixed into measured data or rankings.
- Never edit `data/raw/` by hand. Flag bad rows in `data/processed/quality_flags.csv`.
- Units across the code and API: mole fraction, kPa, cm/s, g, mm, s.

## Secrets

The language-model key lives in `.env`, which is git-ignored. Never write a key into a tracked file, a test, a notebook or a commit message.
