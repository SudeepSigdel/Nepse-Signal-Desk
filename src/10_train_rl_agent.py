"""
Step 10 (manual / weekly): train and evaluate the RL allocator walk-forward.

For each test year (default: the last 4 folds) a PPO policy is trained only
on the preceding `--train-years` of out-of-sample data, then trades that
unseen year. The yearly policies run as one continuous portfolio and are
compared with BuyAndHold and the static 80/20 CoreSatellite over the same
window.

The RL bot is promoted to live paper trading only if it beats both
benchmarks on Sharpe AND the bootstrap CI of its daily-return edge over the
better benchmark lies entirely above zero. Otherwise it stays a research
result and the report says why.

Usage:
    python src/10_train_rl_agent.py [--timesteps 30000] [--folds 6,7,8,9]
Requires: pip install -r requirements.txt -r requirements-pipeline.txt
"""

import argparse
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
from app.agents.data import load_market_data  # noqa: E402
from app.agents.report import agent_entry, paired_difference  # noqa: E402
from app.agents.rl import ALLOCATION_LABELS, RLAgent, make_env  # noqa: E402
from app.agents.signal_agent import BuyAndHoldAgent, SignalAgent  # noqa: E402
from app.agents.tuning import ScheduledAgent, load_folds  # noqa: E402
from app.trading.backtest import run_backtest  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROCESSED / "models"
OUT_DIR = PROJECT_ROOT / "outputs" / "agents"


def train_policy(market, start, end, timesteps: int, seed: int):
    from stable_baselines3 import PPO

    env = make_env(market, start, end, episode_days=250, seed=seed)
    model = PPO(
        "MlpPolicy", env, n_steps=500, batch_size=100, learning_rate=3e-4, gamma=0.99,
        ent_coef=0.01, seed=seed, verbose=0, device="cpu",
    )
    model.learn(total_timesteps=timesteps)
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--timesteps", type=int, default=30_000)
    parser.add_argument("--folds", default="", help="Test folds, e.g. 6,7,8,9 (default: last 4).")
    parser.add_argument("--train-years", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    family = "xgboost" if os.getenv("MODEL_FAMILY", "xgboost").lower() in {"", "xgboost", "xgb"} else "random_forest"
    started = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    market = load_market_data(PROCESSED, family)
    all_folds = load_folds(PROCESSED / "fold_config.json")
    wanted = {int(f) for f in args.folds.split(",") if f.strip()} or {f.fold for f in all_folds[-4:]}
    folds = [f for f in all_folds if f.fold in wanted]

    schedule, trained = [], []
    for fold in folds:
        train_start = fold.test_start - pd.DateOffset(years=args.train_years)
        train_end = fold.test_start - pd.Timedelta(days=1)
        t0 = time.time()
        policy = train_policy(market, train_start, train_end, args.timesteps, args.seed)
        policy.save(MODEL_DIR / f"rl_agent_fold{fold.fold}.zip")
        # Satellite uses the a-priori default SignalAgent settings (0.65 / 10d / 5%),
        # not tuned ones, so nothing from the test year leaks into the RL bot.
        schedule.append((fold.test_start, RLAgent(policy, name="RLBot")))
        trained.append({"fold": fold.fold, "train": f"{train_start.date()}..{train_end.date()}", "seconds": round(time.time() - t0)})
        print(f"  fold {fold.fold}: trained on {train_start.date()}..{train_end.date()} in {time.time() - t0:.0f}s")

    start, end = folds[0].test_start, folds[-1].test_end
    rl = run_backtest(ScheduledAgent(schedule, name="RLBot"), market, start, end)
    core = run_backtest(BlendAgent(name="CoreSatellite"), market, start, end)
    bh = run_backtest(BuyAndHoldAgent(), market, start, end)

    best = max((core, bh), key=lambda r: r.metrics["sharpe"])
    edge = paired_difference(rl, best)
    beats_sharpe = rl.metrics["sharpe"] > max(core.metrics["sharpe"], bh.metrics["sharpe"])
    promoted = bool(beats_sharpe and edge["ci_pct"][0] > 0)
    if promoted:
        why = f"Beat {best.agent} with a daily edge whose 95% CI is above zero ({edge['ci_pct']})."
    elif beats_sharpe:
        why = f"Higher Sharpe than both benchmarks, but the edge over {best.agent} isn't statistically clear (CI {edge['ci_pct']})."
    else:
        why = f"Did not beat the benchmarks' Sharpe ({rl.metrics['sharpe']} vs {best.agent} {best.metrics['sharpe']})."

    for result in (rl, core, bh):
        m = result.metrics
        print(f"  {result.agent:14s} return {m['total_return_pct']:7.1f}%  Sharpe {m['sharpe']:5.2f}  max DD {m['max_drawdown_pct']:6.1f}%")
    print(f"Promoted: {promoted} - {why}")

    allocations = (
        rl.fills["reason"].str.extract(r"\[RL allocation: (.*)\]")[0].value_counts().to_dict()
        if not rl.fills.empty else {}
    )
    evaluation = {
        "family": family,
        "window": {"start": start.date().isoformat(), "end": end.date().isoformat()},
        "timesteps_per_fold": args.timesteps,
        "train_years": args.train_years,
        "folds": trained,
        "allocations": ALLOCATION_LABELS,
        "allocation_usage_in_trades": allocations,
        "agents": [agent_entry(r, folds) for r in (rl, core, bh)],
        "edge_vs_best_benchmark": edge,
        "promoted": promoted,
        "promotion_reason": why,
    }
    (OUT_DIR / f"rl_{family}.json").write_text(json.dumps(evaluation, indent=1, default=str))

    live_path = OUT_DIR / "live_agents.json"
    live = json.loads(live_path.read_text()) if live_path.exists() else {}
    live["rl_promoted"] = promoted
    live["rl_reason"] = why
    if promoted:
        latest_end = market.dates[-1]
        policy = train_policy(market, latest_end - pd.DateOffset(years=args.train_years), latest_end, args.timesteps, args.seed)
        policy.save(MODEL_DIR / "rl_agent_latest.zip")
        live["rl_model"] = "data/processed/models/rl_agent_latest.zip"
    live_path.write_text(json.dumps(live, indent=1))
    print(f"Done in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
