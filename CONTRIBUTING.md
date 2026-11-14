# How we work in parallel

Two people, one repository, no stepping on each other. Three things make that work, in this order of importance:

1. **Each person owns folders.** Branches do not prevent conflicts; not editing the same files does.
2. **The two halves meet at a written contract** ([docs/CONTRACTS.md](docs/CONTRACTS.md)), so each can be built and tested without the other being finished.
3. **Branches are short.** Start from fresh `main`, merge back within hours, repeat.

## 1. Who owns what

| Area | Paths | Owner |
| --- | --- | --- |
| Dashboard: 6.1, 6.2, 6.4, 6.5 and data ingest | `backend/` (except `routers/predict.py`), `frontend/`, `data/processed/` | @ankathakanksha21 |
| Models: 6.3 | `ml/`, `backend/app/routers/predict.py`, `data/labels/` | @VDT37 |
| Contract | `ml/src/ignis_ml/contract.py`, `ml/src/ignis_ml/raw.py`, `docs/CONTRACTS.md`, `data/raw/`, `scripts/fetch_psi.py`, `.github/` | both |

Rules:

- Edit only your own paths. If you need a change in the other person's area, ask them, or open a small pull request and have them review it.
- A change to a contract file is its own pull request with nothing else in it, and the other person approves it before it merges.
- Do not reformat, rename or "tidy" files you do not own. A formatter run across the whole repository is the fastest way to conflict with everything.

`backend/app/main.py` and `frontend/src/App.tsx` already register every feature. Feature work goes in the feature's own file or folder, and those two shared files should not need editing.

## 2. The loop

Every piece of work follows the same five steps.

**Start from up-to-date `main`:**

```bash
git switch main
```

```bash
git pull
```

```bash
git switch -c feat/6.1-cards
```

**Work and commit** as often as you like. Push early so the work is backed up:

```bash
git push -u origin feat/6.1-cards
```

**Before opening a pull request, bring in what has landed on `main` since you started:**

```bash
git fetch origin
```

```bash
git merge origin/main
```

Run the tests for your area, then push.

**Open a pull request into `main`.** Wait for CI to go green. If it touches only your own paths, merge it yourself. If it touches a contract file, wait for the other person's approval.

**Merge with "Squash and merge", then delete the branch.** Start the next piece of work from step one with a new branch. Do not keep committing to a branch after it has been squash-merged; its history no longer matches `main` and the next merge will conflict with itself.

## 3. Keep branches short

"One branch per feature" does not mean one branch for all of 6.1. A branch that lives for a day drifts far from `main` and merges painfully. Cut each feature into slices that each take a few hours and each leave `main` working:

```
feat/ingest                     feat/6.3-flex-burning-rate
feat/6.1-cards                  feat/6.3-flex-extinction
feat/6.1-ranking                feat/6.3-physics-d2
feat/6.1-compare                feat/6.3-cfig-cool-flame
feat/6.2-habitat-profiles       feat/6.3-solid-matcher
```

Aim to merge something every two to three hours. Half-finished is fine as long as `main` still runs and tests pass: a page that says "not built yet" is a valid state.

If your next slice depends on your previous one, merge the previous one first rather than branching from an unmerged branch.

## 4. Branch names

```
feat/<feature>-<slice>     feat/6.3-flex-burning-rate
fix/<what>                 fix/flex-encoding
contract/<what>            contract/add-spread-rate
data/<what>                data/refresh-snapshot
```

Branches made by an AI coding session (for example `claude/...`) follow the same rules: made from fresh `main`, short-lived, merged by pull request.

## 5. `main`

- `main` always runs and its tests pass.
- Nobody pushes to `main` directly. Everything arrives by pull request.
- Never force-push `main`, and never force-push a branch the other person has pulled.

To have GitHub enforce this: repository Settings, Branches, add a rule for `main`, and tick "Require a pull request before merging" and "Require status checks to pass". Leave required approvals at 0. With two people, required approvals mean neither can merge their own area's work while the other is asleep, and "Require review from Code Owners" blocks you outright on your own folders, because you cannot approve your own pull request. The contract files are the only ones where waiting for the other person matters, and that stays a rule between us.

## 6. When you need something from the other half

- **A new field or function across the boundary:** open a `contract/...` pull request with only the change to `contract.py` and `docs/CONTRACTS.md`. Get it approved and merged quickly, then both pull `main`. Adding an optional field never breaks the other side.
- **The other half is not built yet:** build against the contract. `ignis_ml.api` answers `not_implemented` until the models land, and the UI has to handle that status anyway.
- **Bad or surprising data in `data/raw/`:** do not edit the file. Flag the row in `data/processed/quality_flags.csv` (see the contract).

## 7. If a conflict happens anyway

It will most likely be in a dependency file or a contract file.

```bash
git fetch origin
```

```bash
git merge origin/main
```

Git lists the conflicted files. Open each, keep the right lines, remove the `<<<<<<<`, `=======`, `>>>>>>>` markers, then:

```bash
git add <file>
```

```bash
git commit
```

For `frontend/package-lock.json`, do not resolve by hand. Take the version from `main` and regenerate:

```bash
git checkout origin/main -- frontend/package-lock.json
```

```bash
cd frontend && npm install
```

If the conflict is in the other person's file, stop and ask them. It means one of you edited outside your area.

## 8. Before you merge

- Tests for your area pass (`pytest` in `ml/` or `backend/`, `npm run lint && npm run build` in `frontend/`).
- CI is green.
- No key, token or `.env` file is in the diff.
- The project's own rules still hold (section 7 of the problem statement): numbers come from code, sources are attached, simulated output is labelled, nothing is predicted outside the tested range.
