# Flame in Freefall

NASA Space Apps 2026. A dashboard that summarizes, ranks and interprets NASA's microgravity combustion experiments for fire safety in space.

It is a research and teaching aid, not a certified safety tool. Numbers come from code reading NASA tables, each value links to its source row, and nothing is predicted outside the conditions NASA tested.

## What is in it

| Page | What it does |
| --- | --- |
| Experiments | The 24 investigations: browse them, rank them for a mission, compare them, find similar tests, and see their uses on Earth. |
| Habitats | The oxygen and pressure conditions NASA never tested, and the table cells that look wrong. |
| Models | Predictions inside the tested range, shown with the nearest real tests. |
| Lab | A simulated burning droplet beside the real tests, and plots of the real data. |
| Ask | Questions answered from NASA's records, with a source on every sentence. |

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

- [The data](data/README.md)
- [The models](ml/README.md)
- [Problem statement](docs/PROBLEM_STATEMENT.md)

The data is from NASA's [PSI](https://psi.nasa.gov) repository. Each investigation is cited by its DOI.
