# Contributing to NEPSE Signal Desk

Thanks for considering a contribution. This is a solo academic project that's grown into something usable — outside contributions are welcome, but please read this first so review goes smoothly.

## Before you start

For anything beyond a small fix (typo, obvious bug), open an issue first describing what you want to change and why. This avoids duplicated or wasted effort on larger features.

## Development setup

See the [Quick Start](README.md#quick-start) section in the README for backend and frontend setup. In short:

```bash
# Backend
python -m venv venv && venv\Scripts\activate  # or source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL to test accounts/watchlist/portfolio
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Before opening a PR

Run the same checks CI runs:

```bash
# Backend
python -m compileall app src automation scrapper
python -m pytest tests -q

# Frontend
cd frontend
npm run type-check
npm run build
```

Both `daily-pipeline.yml` (on every push/PR) and `deploy.yml` (on push to `main`) run these — a PR that fails them won't be merged.

## Code conventions

- **Backend**: routes live in `app/api/routes/`, data access in `app/repositories/`, business logic in `app/services/`. Confidence thresholds are centralized in `app/constants.py` — don't hardcode `0.65`/`0.55`/`0.45` elsewhere.
- **Frontend**: pages in `src/pages/`, shared state in `src/context/` (not prop-drilled), one API call site per resource in `src/lib/api.ts`. New pages should be added to the `React.lazy()` list in `App.tsx`, not imported eagerly, to keep the initial bundle small.
- **ML pipeline** (`src/`): scripts are numbered and meant to run in order. If you change feature engineering (`03_feature_engineering.py`) or labels (`04_label_construction.py`), you need to retrain (`06`/`06b`) and rerun the backtest (`07`/`08`) for both XGBoost and Random Forest (`MODEL_FAMILY=xgboost` / `random_forest`) before the model-performance numbers on the Trust page are accurate again.
- Keep comments to *why*, not *what* — the code should read clearly enough that a comment explaining what a line does is redundant.

## Commit messages

Conventional-commit-ish prefixes (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`) are used throughout the history — please follow the same pattern.

## Data and models

Don't commit changes under `data/raw/`, `data/processed/`, or `outputs/` in a PR — these are regenerated daily by the `daily-pipeline.yml` workflow and any PR-time changes to them will just be overwritten by the next scheduled run. If your change requires new pipeline outputs to be visible (e.g. a new metric), the CI-generated commit will supersede whatever you push locally.

## Reporting bugs / requesting features

Use the issue templates. For security vulnerabilities, see [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
