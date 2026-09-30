"""Performance metrics for an equity curve (backtests, agent reports)."""

from typing import Callable, Optional

import numpy as np
import pandas as pd


def bootstrap_ci(
    values: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """(point, lower, upper) bootstrap CI - same method as src/stats_utils.bootstrap_ci."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 2:
        return (float("nan"),) * 3
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    boots = np.array([statistic(values[row]) for row in idx])
    alpha = (1 - ci) / 2
    lower, upper = np.quantile(boots, [alpha, 1 - alpha])
    return float(statistic(values)), float(lower), float(upper)


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough fall, as a negative fraction (e.g. -0.23)."""
    if equity.empty:
        return 0.0
    return float((equity / equity.cummax() - 1).min())


def summarize(
    equity: pd.Series,
    fills: Optional[pd.DataFrame] = None,
    starting_cash: Optional[float] = None,
    cash: Optional[pd.Series] = None,
    with_ci: bool = True,
) -> dict:
    """
    Metrics for a daily equity series indexed by date. Annualisation uses the
    observed number of sessions per year (NEPSE trades ~230-240 days/yr).
    """
    equity = equity.dropna()
    if len(equity) < 2:
        return {"days": len(equity)}
    start_value = starting_cash or float(equity.iloc[0])
    returns = equity.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    periods_per_year = len(returns) / years
    std = returns.std()
    sharpe = float(returns.mean() / std * np.sqrt(periods_per_year)) if std > 0 else 0.0
    total_return = float(equity.iloc[-1] / start_value - 1)

    out = {
        "start": equity.index[0].date().isoformat(),
        "end": equity.index[-1].date().isoformat(),
        "days": int(len(equity)),
        "final_equity": round(float(equity.iloc[-1]), 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(((1 + total_return) ** (1 / years) - 1) * 100, 2) if total_return > -1 else -100.0,
        "sharpe": round(sharpe, 3),
        "volatility_pct": round(float(std * np.sqrt(periods_per_year) * 100), 2),
        "max_drawdown_pct": round(max_drawdown(equity) * 100, 2),
    }
    if cash is not None:
        exposure = 1 - (cash.reindex(equity.index) / equity)
        out["avg_exposure_pct"] = round(float(exposure.mean() * 100), 1)

    if fills is not None and not fills.empty:
        sells = fills[fills["side"] == "sell"]
        wins = sells["realized_pnl"][sells["realized_pnl"] > 0].sum()
        losses = -sells["realized_pnl"][sells["realized_pnl"] < 0].sum()
        traded = float((fills["price"] * fills["qty"]).sum())
        out.update(
            {
                "trades": int(len(fills)),
                "round_trips": int(len(sells)),
                "win_rate_pct": round(float((sells["realized_pnl"] > 0).mean() * 100), 1) if len(sells) else None,
                "profit_factor": round(float(wins / losses), 2) if losses > 0 else None,
                "fees_paid": round(float(fills["fees"].sum()), 2),
                "annual_turnover_x": round(traded / float(equity.mean()) / years, 2),
            }
        )
    else:
        out.update({"trades": 0, "round_trips": 0, "fees_paid": 0.0})

    if with_ci:
        point, lower, upper = bootstrap_ci(returns.to_numpy())
        out["mean_daily_return_ci_pct"] = [round(v * 100, 4) for v in (point, lower, upper)]
    return out
