"""
Step 9: evaluate trading agents on out-of-sample predictions.

Runs every agent as one continuous paper portfolio over the walk-forward test
years (the first fold is used only to tune TunedSignalBot), with full NEPSE
costs, and writes:

    outputs/agents/report_{family}.json   metrics + CIs, per-year returns,
                                          equity curves, recent trades,
                                          paired comparisons, tuning choices
    outputs/agents/trades_{family}.parquet
    outputs/agents/live_agents.json       configs the live paper bots use

The RL agent (src/10_train_rl_agent.py) adds itself to the same report.

Usage: MODEL_FAMILY=xgboost python src/09_agent_backtest.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
logging.getLogger("app.services.exit_rules").setLevel(logging.WARNING)

from app.agents.blend_agent import BlendAgent  # noqa: E402
from app.agents.data import adjust_for_corporate_actions, family_suffix, load_market_data  # noqa: E402
from app.agents.report import build_report, paired_difference  # noqa: E402
from app.agents.signal_agent import BuyAndHoldAgent, RandomAgent, SignalAgent  # noqa: E402
from app.agents.tuning import config_label, grid_configs, load_folds, score, walk_forward  # noqa: E402
from app.trading.backtest import run_backtest  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
OUT_DIR = PROJECT_ROOT / "outputs" / "agents"


def normalize_family(raw: str | None) -> str:
    value = (raw or "xgboost").strip().lower().replace("-", "_")
    return "random_forest" if value in {"rf", "random_forest", "randomforest"} else "xgboost"


def tune_live_config(market, train_years: int = 3) -> dict:
    """Pick today's live SignalBot settings on the most recent `train_years` of data."""
    end = market.dates[-1]
    start = end - pd.DateOffset(years=train_years)
    best = max(
        ((score(run_backtest(SignalAgent(**c), market, start, end, with_ci=False).metrics), c) for c in grid_configs()),
        key=lambda item: item[0],
    )
    return best[1]


def main() -> None:
    family = normalize_family(os.getenv("MODEL_FAMILY"))
    started = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    market = load_market_data(PROCESSED, family)
    folds = load_folds(PROCESSED / "fold_config.json")
    print(f"[{family}] {len(market.dates)} sessions {market.dates[0].date()} → {market.dates[-1].date()}")

    print("Walk-forward tuning TunedSignalBot...")
    tuned, choices = walk_forward(market, folds)
    start = pd.Timestamp(choices[0]["test_start"]) if choices else market.dates[0]
    last_config = choices[-1]["config"] if choices else {}

    agents = [
        SignalAgent(),
        tuned,
        BlendAgent(name="CoreSatellite", satellite=SignalAgent(name="CoreSatellite-satellite", **last_config)),
        RandomAgent(),
        BuyAndHoldAgent(),
    ]
    results = {}
    for agent in agents:
        result = run_backtest(agent, market, start=start)
        results[agent.name] = result
        m = result.metrics
        print(f"  {agent.name:15s} return {m['total_return_pct']:7.1f}%  Sharpe {m['sharpe']:5.2f}  max DD {m['max_drawdown_pct']:6.1f}%  fees Rs {m['fees_paid']:,.0f}")

    comparisons = [
        paired_difference(results["SignalBot"], results["RandomBot"]),
        paired_difference(results["TunedSignalBot"], results["SignalBot"]),
        paired_difference(results["TunedSignalBot"], results["BuyAndHold"]),
        paired_difference(results["CoreSatellite"], results["BuyAndHold"]),
    ]
    raw_prices = pd.read_parquet(PROCESSED / "all_stocks_features.parquet", columns=["Symbol", "Date", "Close"])
    _, gap_count = adjust_for_corporate_actions(raw_prices)

    report = build_report(
        family,
        list(results.values()),
        folds,
        {
            "period": {"start": start.date().isoformat(), "end": market.dates[-1].date().isoformat()},
            "tuning": choices,
            "comparisons": comparisons,
            "data_notes": {
                "corporate_action_gaps_adjusted": gap_count,
                "explanation": "Stored prices are not adjusted for bonus/right shares. Close-to-close moves beyond "
                "NEPSE's ±10% circuit were treated as corporate actions and earlier prices back-adjusted.",
            },
            "method": {
                "fills": "Orders decided after a session's close fill at the next session's close.",
                "costs": "Tiered broker commission, SEBON 0.015%, Rs 25 DP charge, 5%/7.5% CGT.",
                "limits": "10-share buy lot, max 10% of a day's volume, no short selling.",
                "predictions": "Walk-forward out-of-sample model probabilities only.",
            },
        },
    )
    rl_path = OUT_DIR / f"rl_{family}.json"
    if rl_path.exists():
        report["rl"] = json.loads(rl_path.read_text())  # latest RL evaluation, if one was trained

    (OUT_DIR / f"report_{family}.json").write_text(json.dumps(report, indent=1, default=str))
    trades = pd.concat([r.fills.assign(agent=name) for name, r in results.items()], ignore_index=True)
    trades.to_parquet(OUT_DIR / f"trades{family_suffix(family)}.parquet", index=False)

    if family == "xgboost":
        live = tune_live_config(market)
        live_path = OUT_DIR / "live_agents.json"
        existing = json.loads(live_path.read_text()) if live_path.exists() else {}
        existing.update(
            {
                "signal_config": live,
                "signal_label": config_label(live),
                "tuned_on": f"{(market.dates[-1] - pd.DateOffset(years=3)).date()}..{market.dates[-1].date()}",
            }
        )
        live_path.write_text(json.dumps(existing, indent=1))
        print(f"Live TunedSignalBot config: {config_label(live)}")

    print(f"Wrote {OUT_DIR / f'report_{family}.json'} in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
