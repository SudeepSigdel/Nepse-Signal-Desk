# Research Gaps

How NEPSE Signal Desk differs from typical past NEPSE / stock-prediction academic projects.

Most prior work in this space follows a common pattern: a single Jupyter notebook, one
random (non-time-ordered) train/test split, technical indicators or raw price only, a
next-day direction or price-value target, no transaction costs, and a headline accuracy of
80–95% — a strong tell of leakage on a time-series problem. No deployment, no persistence,
no automation, no retraining after submission.

This project takes a narrower predictive edge in exchange for methodological rigor and a
deployed system. The sections below state each gap it fills, and — for credibility — the
gaps it deliberately does not.

---

## 1. Leakage-conscious evaluation

Walk-forward validation with **9 expanding-window annual folds**
(`data/processed/fold_config.json`, built in `src/05_walk_forward_setup.py`), each with a
**20-day embargo gap** between train and test, plus an explicit per-fold leakage check
printed during training. `StandardScaler` is fit on train only, per fold.

**Gap filled:** past NEPSE projects' reported accuracy is frequently inflated by leakage from
random splits on time-ordered data. This project reports honest, modest OOS AUC (low-to-mid
0.50s, see `docs/architecture.md`) instead of an inflated one.

## 2. Transaction-cost-aware problem framing

The label threshold (`Label_10d`, `Label_10d_sell` in `src/04_label_construction.py`) is
`>1%` / `<-1%` over 10 days — set to NEPSE's round-trip transaction cost, not an arbitrary
0% direction split. The backtest (`src/07_backtest.py`) deducts a 1% cost per simulated trade.

**Gap filled:** most past work predicts raw price direction and reports accuracy divorced
from whether the edge survives real trading frictions.

## 3. Separate BUY/SELL model architecture

Two independent classifier families (`src/06_train_model.py` for BUY,
`src/06b_train_sell_model.py` for SELL), combined into a 5-level verdict
(BUY/MODERATE/HOLD/WEAK_SELL/SELL) via thresholds in `app/constants.py`.

**Gap filled:** past work typically models a single up/down direction. This treats entry and
exit as distinct prediction problems, closer to how a real trading rule would be built.

## 4. Full system vs. static analysis

A deployed FastAPI backend (`app/`) with JWT + Google OAuth, Postgres-backed
watchlist/holdings, rate limiting, and a documented three-layer signal architecture
(`docs/architecture.md`); a React dashboard (`frontend/src/pages/`) with live stock
research, watchlist, portfolio, and a dedicated Model Trust page.

**Gap filled:** past academic NEPSE ML projects almost universally stop at a backtest chart —
no serving layer, no persistence, no user-facing product.

## 5. Live, self-updating pipeline

A daily CI-driven pipeline (`.github/workflows/daily-pipeline.yml`,
`automation/daily_pipeline.py`) runs scrape → clean → feature engineering → labeling →
walk-forward retrain (BUY+SELL) → backtest → report, then commits refreshed data/models
automatically. A custom scraper (`scrapper/nepse_scraper.py`) targets Sharesansar with a
Merolagani fallback, since NEPSE has no public market-data API.

**Gap filled:** past projects use a static dataset frozen at submission time. This system
keeps retraining and stays current afterward, and addresses the "no public NEPSE API"
data-access barrier that limits most local research.

## 6. Transparent, continuously-computed model monitoring

`/api/model-performance` and the Model Trust page render live-computed fold AUC,
calibration (stated confidence vs. realized outcome rate), and ML-vs-baseline comparison —
sourced from real backtest artifacts (`app/repositories/evaluation_repository.py`), not
numbers hardcoded at report-writing time.

**Gap filled:** past work reports a single static accuracy number with no way to verify it
holds as new data arrives. This project exposes its own ongoing, honest scorecard.

---

## What this project does *not* close

- **No fundamental or dedicated macroeconomic features.** Market-wide news
  sentiment is now included as an availability-aware feature; per-symbol
  sentiment remains experimental and is not part of the production feature set.
- **No explicit NEPSE market-microstructure modeling** — no circuit-breaker, illiquidity, or
  T+ settlement handling. The only NEPSE-specific adaptation is the 1% transaction-cost
  label threshold and a crude data-availability filter (drop symbols with <120 rows in
  `src/02_data_cleaning.py`).
- **Modest predictive edge** — OOS AUC in the low-to-mid 0.50s. The contribution here is
  methodological rigor and system engineering, not a breakthrough in predictive accuracy.

Both of the above are natural directions for future work.
