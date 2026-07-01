## What does this PR do?

<!-- Brief description of the change and why -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] ML pipeline / model change
- [ ] Refactor / chore

## Checklist

- [ ] `python -m pytest tests -q` passes
- [ ] `cd frontend && npm run type-check && npm run build` passes
- [ ] No changes to `data/raw/`, `data/processed/`, or `outputs/` (these are owned by the scheduled pipeline — see [CONTRIBUTING.md](../CONTRIBUTING.md))
- [ ] If this changes feature engineering, labels, or model training, I retrained and reran the backtest for both model families
- [ ] If this changes API request/response shapes, I updated both the Pydantic schema (`app/schemas.py`) and the frontend TypeScript types (`frontend/src/types.ts`)

## Screenshots (if UI change)

<!-- Before/after screenshots help a lot for frontend PRs -->
