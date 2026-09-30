"""Turn backtest results into the JSON report served by /api/agents."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.trading.backtest import BacktestResult
from app.trading.metrics import bootstrap_ci

AGENT_DESCRIPTIONS = {
    "SignalBot": "Buys the model's top picks (buy confidence ≥ 0.65, up to 5 names) and exits with the app's rules: "
    "10-day time exit, 5% stop-loss, or confidence falling below 0.45.",
    "TunedSignalBot": "SignalBot, but each year it picks its threshold, holding period and stop-loss using only the "
    "previous 3 years, then trades the next (unseen) year with them.",
    "CoreSatellite": "80% in an equal-weight basket of the 20 most liquid stocks, 20% in the tuned model picks.",
    "RLBot": "A reinforcement-learning policy that chooses each day how to split money between cash, the market "
    "basket and model picks, based on market trend, breadth, volatility and signal strength.",
    "RandomBot": "Control group: SignalBot's exact sizing and exit rules, but random picks.",
    "BuyAndHold": "Benchmark: equal-weight every liquid stock on day one and never trade.",
}


def weekly_curve(equity: pd.Series) -> list[list]:
    weekly = equity.resample("W").last().dropna()
    return [[d.date().isoformat(), round(float(v), 2)] for d, v in weekly.items()]


def per_fold_returns(equity: pd.Series, folds) -> list[dict]:
    rows = []
    for fold in folds:
        window = equity[(equity.index >= fold.test_start) & (equity.index <= fold.test_end)]
        before = equity[equity.index < fold.test_start]
        if window.empty:
            continue
        base = before.iloc[-1] if not before.empty else window.iloc[0]
        rows.append({"fold": fold.fold, "year": fold.test_start.year, "return_pct": round(float(window.iloc[-1] / base - 1) * 100, 2)})
    return rows


def paired_difference(a: BacktestResult, b: BacktestResult) -> dict:
    """Bootstrap CI of the mean daily return difference a - b on shared dates (percent)."""
    joined = pd.concat([a.daily_returns(), b.daily_returns()], axis=1, join="inner").dropna()
    diff = (joined.iloc[:, 0] - joined.iloc[:, 1]).to_numpy()
    point, lower, upper = bootstrap_ci(diff) if len(diff) > 1 else (np.nan,) * 3
    return {
        "a": a.agent,
        "b": b.agent,
        "mean_daily_diff_pct": round(point * 100, 4),
        "ci_pct": [round(lower * 100, 4), round(upper * 100, 4)],
        "significant": bool(lower > 0 or upper < 0),
        "annualized_diff_pct": round(point * 100 * 240, 2),
    }


def agent_entry(result: BacktestResult, folds, recent_trades: int = 40) -> dict:
    fills = result.fills.tail(recent_trades).copy()
    fills["date"] = fills["date"].dt.date.astype(str)
    return {
        "name": result.agent,
        "description": AGENT_DESCRIPTIONS.get(result.agent, ""),
        "metrics": result.metrics,
        "per_fold": per_fold_returns(result.equity, folds),
        "equity": weekly_curve(result.equity),
        "recent_trades": fills.round(2).to_dict(orient="records"),
    }


def build_report(family: str, results: list[BacktestResult], folds, extras: dict) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "family": family,
        "starting_cash": results[0].starting_cash if results else None,
        "agents": [agent_entry(r, folds) for r in results],
        **extras,
    }
