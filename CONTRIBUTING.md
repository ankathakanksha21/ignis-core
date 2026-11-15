# How we work

Two people, one repository. Each person edits only their own folders, and work reaches `main` through short branches and pull requests.

## Who owns what

| Area | Paths | Owner |
| --- | --- | --- |
| Dashboard (6.1, 6.2, 6.4, 6.5, ingest) | `backend/` except `routers/predict.py`, `frontend/`, `data/processed/` | @ankathakanksha21 |
| Models (6.3) | `ml/`, `backend/app/routers/predict.py`, `data/labels/` | @VDT37 |
| Contract | `ml/src/ignis_ml/contract.py`, `ml/src/ignis_ml/raw.py`, `docs/CONTRACTS.md`, `data/raw/`, `scripts/fetch_psi.py`, `.github/` | both |

A contract file changes in a pull request of its own, and the other person approves it first.

## The loop

1. Start from fresh `main`:
   ```bash
   git switch main && git pull && git switch -c feat/6.1-cards
   ```
2. Work, commit, push.
3. Before the pull request, bring in `main` and run your tests:
   ```bash
   git fetch origin && git merge origin/main
   ```
4. Open a pull request into `main` and wait for CI.
5. Squash and merge, delete the branch, and start the next piece from step 1.

## Rules

- Keep branches short. Cut a feature into pieces of a few hours and merge each one.
- Never push to `main` directly, and never force-push it.
- Do not keep working on a branch after it is merged. Start a new one.
- Do not reformat files you do not own.
- Never edit `data/raw/` by hand. Flag bad rows in `data/processed/quality_flags.csv`.
- Never commit a key or a `.env` file.

Branch names look like `feat/6.3-flex-burning-rate`, `fix/flex-encoding`, `contract/add-spread-rate`.

To have GitHub enforce the pull request rule, go to Settings, Branches, and require a pull request and passing checks for `main`. Leave required approvals at 0.

## If you hit a conflict

Run step 3. Git lists the conflicted files. Fix each one, then `git add <file>` and `git commit`.

For `frontend/package-lock.json`, take the version on `main` and regenerate it:

```bash
git checkout origin/main -- frontend/package-lock.json && cd frontend && npm install
```

A conflict in the other person's file means one of you edited outside your area. Ask before resolving it.
