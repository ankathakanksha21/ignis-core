# Flame in Freefall

NASA Space Apps 2026. A dashboard that summarizes, ranks and interprets NASA's microgravity combustion experiments for fire safety in space.

It is a research and teaching aid, not a certified safety tool. Numbers come from code reading NASA tables, each value links to its source row, and nothing is predicted outside the conditions NASA tested.

## Who owns what

| Path | What | Owner |
| --- | --- | --- |
| `backend/` | FastAPI app, one router per feature | @ankathakanksha21 |
| `frontend/` | React app, one folder per feature | @ankathakanksha21 |
| `ml/` | Models and physics engine (6.3) | @VDT37 |
| `data/raw/` | PSI snapshot, written only by `scripts/fetch_psi.py` | both |
| `data/processed/` | Output of ingest | @ankathakanksha21 |

## Run it

Needs Python 3.10+ and Node 20+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e "ml[dev]" -e "backend[dev]"
cd backend && uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.

## Test

```bash
cd ml && pytest
cd backend && pytest
cd frontend && npm run lint && npm run build
```

## Rebuild the data

After changing `backend/app/ingest/`, run `cd backend && python -m app.ingest` and commit the rebuilt files with the code.

The AI summaries are written once by `cd backend && python -m app.summaries`, which needs the key. A summary is hidden if the data it was written from changes, until you run that again.

## API key

Copy `.env.example` to `.env` and add the key. `.env` is git-ignored. Never commit the key.

## More

- [How we work](CONTRIBUTING.md)
- [Contract between the two halves](docs/CONTRACTS.md)
- [The data](data/README.md)
- [Problem statement](docs/PROBLEM_STATEMENT.md)

The data is from NASA's [PSI](https://psi.nasa.gov) repository. Each investigation is cited by its DOI.
