import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from pathlib import Path

from stats_utils import bootstrap_ci, compare_strategies, calibration_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TRANS_COST     = 0.01    # 1% round-trip NEPSE transaction cost
PROB_THRESHOLD = 0.55    # Only trade when model is at least 55% confident
                         # This filters out low-confidence predictions
HOLD_DAYS      = 10      # Days we hold each position


def normalize_model_family(raw_family: str | None) -> str:
    family = (raw_family or "xgboost").strip().lower().replace("-", "_")
    if family in {"rf", "randomforest", "random_forest", "random forest"}:
        return "random_forest"
    return "xgboost"


def family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


MODEL_FAMILY = normalize_model_family(os.getenv("MODEL_FAMILY"))
MODEL_SUFFIX = family_suffix(MODEL_FAMILY)

os.makedirs(OUTPUTS_DIR, exist_ok=True)

preds = pd.read_parquet(os.path.join(PROCESSED_DIR, f"oos_predictions{MODEL_SUFFIX}.parquet"))
preds["Date"] = pd.to_datetime(preds["Date"])
preds = preds.sort_values(["Symbol", "Date"]).reset_index(drop=True)

print(f"Loaded {len(preds):,} out-of-sample predictions")
print(f"Date range: {preds['Date'].min().date()} → {preds['Date'].max().date()}")
print(f"Probability threshold: {PROB_THRESHOLD}")


def simulate_strategy(df, entry_mask, label="strategy"):
    """
    Simulate a strategy given a boolean mask of entry points.
    Returns a DataFrame of individual trades with their outcomes.

    Parameters:
        df         : the predictions DataFrame
        entry_mask : boolean Series — True on rows where we enter a trade
        label      : name for this strategy
    """
    trades = df[entry_mask].copy()

    trades["Gross_return"] = trades["Fwd_ret_10d"]

    trades["Net_return"] = trades["Gross_return"] - TRANS_COST

    trades["Win"] = (trades["Net_return"] > 0).astype(int)

    trades["Strategy"] = label
    return trades


ml_mask     = preds["Pred_proba"] >= PROB_THRESHOLD
ml_trades   = simulate_strategy(preds, ml_mask, "ML-validated")

signal_mask  = (
    (preds["Signal_RSI_oversold"] == 1) |
    (preds["Signal_MACD_cross"]   == 1) |
    (preds["Signal_BB_lower"]     == 1)
)
sig_trades   = simulate_strategy(preds, signal_mask, "Signal-only")

always_mask  = pd.Series(True, index=preds.index)
always_trades = simulate_strategy(preds, always_mask, "Always-in")


def _sharpe_stat(net_rets_array):
    std = net_rets_array.std()
    if std > 0:
        return (net_rets_array.mean() / std) * np.sqrt(252 / HOLD_DAYS)
    return 0.0


def _profit_factor_stat(net_rets_array):
    gross_profit = net_rets_array[net_rets_array > 0].sum()
    gross_loss = abs(net_rets_array[net_rets_array < 0].sum())
    return gross_profit / gross_loss if gross_loss > 0 else np.inf


def calc_metrics(trades, strategy_name, with_ci=True):
    """
    Calculate all performance metrics for a set of trades.
    Returns a dict of metrics and prints a summary.

    with_ci=True adds bootstrap 95% confidence intervals so the metrics
    read as "point estimate ± uncertainty" rather than bare numbers that
    hide how much they'd wobble on a different sample of trades.
    """
    if len(trades) == 0:
        print(f"{strategy_name}: No trades generated")
        return {}

    net_rets = trades["Net_return"].dropna()
    wins     = trades["Win"].dropna()

    win_rate = wins.mean() * 100

    gross_profit = net_rets[net_rets > 0].sum()
    gross_loss   = abs(net_rets[net_rets < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    total_return = net_rets.sum() * 100

    mean_return = net_rets.mean() * 100
    if net_rets.std() > 0:
        annualise    = np.sqrt(252 / HOLD_DAYS)
        sharpe       = (net_rets.mean() / net_rets.std()) * annualise
    else:
        sharpe = 0.0

    trades_sorted = trades.sort_values("Date")
    cum_ret       = (1 + trades_sorted["Net_return"].fillna(0)).cumprod()
    rolling_max   = cum_ret.expanding().max()
    drawdown      = (cum_ret - rolling_max) / rolling_max
    max_drawdown  = drawdown.min() * 100

    metrics = {
        "Strategy":      strategy_name,
        "Trades":        len(net_rets),
        "Win Rate %":    round(win_rate, 2),
        "Profit Factor": round(profit_factor, 3),
        "Mean Ret %":    round(mean_return, 4),
        "Total Ret %":   round(total_return, 2),
        "Sharpe":        round(sharpe, 3),
        "Max DD %":      round(max_drawdown, 2),
    }

    if with_ci and len(net_rets) >= 10:
        net_arr = net_rets.values
        wins_arr = wins.values

        _, wr_low, wr_high = bootstrap_ci(wins_arr, lambda x: x.mean() * 100, n_boot=1000)
        _, sh_low, sh_high = bootstrap_ci(net_arr, _sharpe_stat, n_boot=1000)
        _, pf_low, pf_high = bootstrap_ci(net_arr, _profit_factor_stat, n_boot=1000)

        metrics["Win Rate CI"]    = f"[{wr_low:.1f}, {wr_high:.1f}]"
        metrics["Sharpe CI"]      = f"[{sh_low:.3f}, {sh_high:.3f}]"
        metrics["Profit Fact CI"] = f"[{pf_low:.3f}, {pf_high:.3f}]"

    return metrics


print("\n" + "="*70)
print("STRATEGY PERFORMANCE COMPARISON")
print("="*70)

results = []
for trades, name in [
    (ml_trades,     "ML-validated"),
    (sig_trades,    "Signal-only"),
    (always_trades, "Always-in"),
]:
    m = calc_metrics(trades, name)
    results.append(m)

metrics_df = pd.DataFrame(results).set_index("Strategy")
print(metrics_df.to_string())

print("\nMetric guide:")
print("  Win Rate  : % trades profitable after costs (>50% is good)")
print("  Prof Factor: gross profit / gross loss (>1.0 = overall profitable)")
print("  Mean Ret  : average return per trade after costs")
print("  Total Ret : sum of all trade returns (not compounded)")
print("  Sharpe    : risk-adjusted return, annualised (>0.5 acceptable)")
print("  Max DD    : worst peak-to-trough loss (smaller magnitude = better)")
print("  *_CI      : 95% bootstrap confidence interval for that metric")


print("\n" + "="*70)
print("SIGNIFICANCE TEST: does the ML filter actually beat Signal-only?")
print("="*70)
print("Two-sample Mann-Whitney U test on net returns (unpaired, distribution-")
print("free) plus a bootstrap CI on the difference in mean return. A bigger")
print("profit factor alone doesn't prove the ML filter helps — this checks")
print("whether the gap is unlikely to be sampling noise.")

sig_test = compare_strategies(
    ml_trades["Net_return"].values, sig_trades["Net_return"].values,
    label_a="ML-validated", label_b="Signal-only",
)
print(f"\n  n(ML-validated)={sig_test['n_a']:,}  n(Signal-only)={sig_test['n_b']:,}")
print(f"  Mean return diff: {sig_test['mean_diff']*100:.4f}%  "
      f"(95% CI: [{sig_test['ci_low']*100:.4f}%, {sig_test['ci_high']*100:.4f}%])")
print(f"  Mann-Whitney U={sig_test['u_statistic']:.1f}  p={sig_test['p_value']:.4g}  "
      f"{'SIGNIFICANT (p<0.05)' if sig_test['significant'] else 'not significant'}")


print("\n" + "="*70)
print("PROBABILITY CALIBRATION (is 'confidence' actually trustworthy?)")
print("="*70)
print("If the model says 60% confidence, does that trade actually win ~60%")
print("of the time? Brier score: 0=perfect, 0.25=what a constant 0.5 guess")
print("gets. The reliability table below compares predicted vs actual rate")
print("per probability bin using the same 10-day success label used to train.")

calib_table, brier = calibration_report(
    preds["Label_10d"].dropna().values,
    preds.loc[preds["Label_10d"].notna(), "Pred_proba"].values,
    n_bins=10,
)
print(f"\n  Brier score: {brier:.4f}")
print(calib_table.to_string(index=False))


print("\n" + "="*70)
print("ML-VALIDATED STRATEGY: PERFORMANCE BY FOLD")
print("="*70)
print(f"{'Fold':<6} {'Trades':>7} {'Win%':>7} {'ProfFact':>9} "
      f"{'MeanRet%':>9} {'Sharpe':>8}")
print("-"*50)

for fold_num in sorted(ml_trades["Fold"].unique()):
    fold_t = ml_trades[ml_trades["Fold"] == fold_num]
    m      = calc_metrics(fold_t, f"Fold {fold_num}")
    if m:
        print(f"  {fold_num:<4} {m['Trades']:>7,} {m['Win Rate %']:>7.1f} "
              f"{m['Profit Factor']:>9.3f} {m['Mean Ret %']:>9.4f} "
              f"{m['Sharpe']:>8.3f}")

print("\n" + "="*70)
print("THRESHOLD SENSITIVITY (ML-validated strategy)")
print("="*70)
print(f"{'Threshold':>10} {'Trades':>8} {'Win%':>7} {'ProfFact':>10} {'Sharpe':>8}")
print("-"*50)

for thresh in [0.50, 0.52, 0.55, 0.58, 0.60, 0.63, 0.65]:
    mask   = preds["Pred_proba"] >= thresh
    trades = simulate_strategy(preds, mask, f"thresh_{thresh}")
    if len(trades) > 50:
        m = calc_metrics(trades, str(thresh))
        print(f"  {thresh:>9.2f} {m['Trades']:>8,} {m['Win Rate %']:>7.1f} "
              f"{m['Profit Factor']:>10.3f} {m['Sharpe']:>8.3f}")
    else:
        print(f"  {thresh:>9.2f}  < 50 trades — threshold too high")


fig, axes = plt.subplots(2, 1, figsize=(13, 9))

ax1 = axes[0]
for trades, name, color in [
    (ml_trades,     "ML-validated", "steelblue"),
    (sig_trades,    "Signal-only",  "orange"),
    (always_trades, "Always-in",    "gray"),
]:
    if len(trades) == 0:
        continue
    t = trades.sort_values("Date").copy()
    t["Cum_return"] = (1 + t["Net_return"].fillna(0)).cumprod() - 1
    ax1.plot(t["Date"], t["Cum_return"] * 100,
             label=name, color=color, linewidth=1.5, alpha=0.85)

ax1.axhline(0, color="black", linewidth=0.8, linestyle="--")
ax1.set_title("Cumulative net return by strategy")
ax1.set_ylabel("Cumulative return (%)")
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2 = axes[1]
ax2.hist(preds["Pred_proba"], bins=60, color="steelblue",
         alpha=0.7, edgecolor="none", label="All predictions")
ax2.axvline(PROB_THRESHOLD, color="red", linestyle="--",
            linewidth=2, label=f"Threshold = {PROB_THRESHOLD}")
ax2.set_title("Distribution of predicted probabilities")
ax2.set_xlabel("Predicted probability (P = signal succeeds)")
ax2.set_ylabel("Count")
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"backtest_results{MODEL_SUFFIX}.png"), dpi=150)
plt.show()

metrics_df.to_csv(os.path.join(OUTPUTS_DIR, f"strategy_metrics{MODEL_SUFFIX}.csv"))
ml_trades.to_parquet(os.path.join(PROCESSED_DIR, f"ml_trades{MODEL_SUFFIX}.parquet"), index=False)

pd.DataFrame([sig_test]).to_csv(
    os.path.join(OUTPUTS_DIR, f"significance_test{MODEL_SUFFIX}.csv"), index=False
)
calib_table.to_csv(os.path.join(OUTPUTS_DIR, f"calibration{MODEL_SUFFIX}.csv"), index=False)
with open(os.path.join(OUTPUTS_DIR, f"brier_score{MODEL_SUFFIX}.txt"), "w") as fp:
    fp.write(f"{brier:.6f}\n")

print(f"\n Saved strategy metrics    → strategy_metrics{MODEL_SUFFIX}.csv")
print(f" Saved ML trades           → ml_trades{MODEL_SUFFIX}.parquet")
print(f" Saved significance test   → significance_test{MODEL_SUFFIX}.csv")
print(f" Saved calibration table   → calibration{MODEL_SUFFIX}.csv")
print(f"\n Backtesting complete! Next: reporting layer.")