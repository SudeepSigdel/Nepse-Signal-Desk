import json
import os
import pickle
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from sklearn.metrics import auc, roc_curve

warnings.filterwarnings("ignore", category=FutureWarning)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROCESSED_DIR / "report"
REPORT_DIR.mkdir(exist_ok=True)

TRANS_COST = 0.01
PROB_THRESHOLD = 0.55


def normalize_model_family(raw_family: str | None) -> str:
    family = (raw_family or "xgboost").strip().lower().replace("-", "_")
    if family in {"rf", "randomforest", "random_forest", "random forest"}:
        return "random_forest"
    return "xgboost"


def family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


def fold_period_label(fold_num: int, fold_configs: dict[int, dict]) -> str:
    fold = fold_configs.get(fold_num)
    if not fold:
        return str(fold_num)

    start = pd.to_datetime(fold["test_start"])
    end = pd.to_datetime(fold["test_end"])
    if start.year == end.year:
        return str(start.year)
    return f"{start.year}-{str(end.year)[-2:]}"


def fold_training_label(fold_num: int, fold_configs: dict[int, dict]) -> str:
    fold = fold_configs.get(fold_num)
    if not fold:
        return f"fold {fold_num}"
    train_end = pd.to_datetime(fold["train_end"]).date()
    return f"trained through {train_end}"


def profit_factor(net_returns: pd.Series) -> float:
    gross_profit = net_returns[net_returns > 0].sum()
    gross_loss = abs(net_returns[net_returns < 0].sum())
    return gross_profit / gross_loss if gross_loss > 0 else np.inf


def annualized_sharpe(net_returns: pd.Series, min_count: int = 1) -> float:
    std = net_returns.std()
    if len(net_returns) < min_count or not np.isfinite(std) or std <= 0:
        return 0.0
    return (net_returns.mean() / std) * np.sqrt(252 / 10)


def active_signal_text(row: pd.Series) -> str:
    labels = []
    if row["Signal_RSI_oversold"]:
        labels.append("RSI-oversold")
    if row["Signal_MACD_cross"]:
        labels.append("MACD-cross")
    if row["Signal_BB_lower"]:
        labels.append("BB-lower")
    return ", ".join(labels) if labels else "none"


MODEL_FAMILY = normalize_model_family(os.getenv("MODEL_FAMILY"))
MODEL_SUFFIX = family_suffix(MODEL_FAMILY)
MODEL_NAME = "Random Forest" if MODEL_FAMILY == "random_forest" else "XGBoost"

preds = pd.read_parquet(PROCESSED_DIR / f"oos_predictions{MODEL_SUFFIX}.parquet")
preds["Date"] = pd.to_datetime(preds["Date"])

with open(PROCESSED_DIR / "fold_config.json", encoding="utf-8") as fp:
    config = json.load(fp)

FEATURE_COLS = config["feature_cols"]
LABEL_COL = config["label_col"]
FOLD_CONFIGS = {int(fold["fold"]): fold for fold in config["folds"]}
PRED_FOLDS = sorted(int(fold) for fold in preds["Fold"].dropna().unique())
LATEST_FOLD = max(PRED_FOLDS)

latest_model_path = PROCESSED_DIR / "models" / f"model_fold{LATEST_FOLD}{MODEL_SUFFIX}.pkl"
with open(latest_model_path, "rb") as fp:
    model_bundle = pickle.load(fp)

model = model_bundle["model"]
scaler = model_bundle["scaler"]

print(f"All files loaded for {MODEL_NAME}. Latest model fold: {LATEST_FOLD}.")


fig, ax = plt.subplots(figsize=(8, 7))

fold_aucs = []
colors = plt.cm.Blues(np.linspace(0.4, 0.95, len(PRED_FOLDS)))  # type: ignore

for fold_num, color in zip(PRED_FOLDS, colors):
    fold_data = preds[preds["Fold"] == fold_num].dropna(
        subset=[LABEL_COL, "Pred_proba"]
    )
    if len(fold_data) < 100:
        continue
    fpr, tpr, _ = roc_curve(fold_data[LABEL_COL], fold_data["Pred_proba"])
    fold_auc = auc(fpr, tpr)
    fold_aucs.append(fold_auc)
    year_label = fold_period_label(fold_num, FOLD_CONFIGS)
    ax.plot(
        fpr,
        tpr,
        color=color,
        linewidth=1.8,
        label=f"Fold {fold_num} ({year_label})  AUC={fold_auc:.3f}",
    )

ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random (AUC=0.500)")
ax.fill_between([0, 1], [0, 1], alpha=0.05, color="gray")

ax.set_xlabel("False Positive Rate", fontsize=12)
ax.set_ylabel("True Positive Rate", fontsize=12)
ax.set_title(
    "ROC Curves - Walk-Forward Folds\nEach curve is fully out-of-sample",
    fontsize=13,
)
ax.legend(fontsize=9, loc="lower right")
ax.grid(True, alpha=0.3)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1])

plt.tight_layout()
plt.savefig(REPORT_DIR / f"fig1_roc_curves{MODEL_SUFFIX}.png", dpi=150)
plt.close()
print(" Figure 1: ROC curves saved")


thresholds = np.arange(0.50, 0.70, 0.01)
thresh_results = []

for threshold in thresholds:
    trades = preds[preds["Pred_proba"] >= threshold].copy()
    trades["Net_return"] = trades["Fwd_ret_10d"] - TRANS_COST

    if len(trades) < 30:
        break

    net = trades["Net_return"].dropna()
    thresh_results.append(
        {
            "threshold": threshold,
            "trades": len(net),
            "win_rate": (net > 0).mean() * 100,
            "pf": profit_factor(net),
            "sharpe": annualized_sharpe(net),
        }
    )

tdf = pd.DataFrame(thresh_results)

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

axes[0, 0].plot(tdf["threshold"], tdf["win_rate"], "steelblue", linewidth=2)
axes[0, 0].axhline(50, color="red", linestyle="--", linewidth=1)
axes[0, 0].set_title("Win Rate vs Threshold")
axes[0, 0].set_ylabel("Win Rate (%)")
axes[0, 0].grid(True, alpha=0.3)

axes[0, 1].plot(tdf["threshold"], tdf["pf"], "green", linewidth=2)
axes[0, 1].axhline(1.0, color="red", linestyle="--", linewidth=1, label="Break-even")
axes[0, 1].set_title("Profit Factor vs Threshold")
axes[0, 1].set_ylabel("Profit Factor")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

axes[1, 0].plot(tdf["threshold"], tdf["sharpe"], "purple", linewidth=2)
axes[1, 0].axhline(0, color="red", linestyle="--", linewidth=1)
axes[1, 0].set_title("Sharpe Ratio vs Threshold")
axes[1, 0].set_ylabel("Sharpe Ratio")
axes[1, 0].set_xlabel("Probability Threshold")
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].bar(tdf["threshold"], tdf["trades"], width=0.008, color="steelblue", alpha=0.7)
axes[1, 1].set_title("Number of Trades vs Threshold")
axes[1, 1].set_ylabel("Trade Count")
axes[1, 1].set_xlabel("Probability Threshold")
axes[1, 1].grid(True, alpha=0.3)

plt.suptitle(
    "Threshold Sensitivity Analysis\nHigher threshold = fewer but better-quality trades",
    fontsize=13,
)
plt.tight_layout()
plt.savefig(REPORT_DIR / f"fig2_threshold_analysis{MODEL_SUFFIX}.png", dpi=150)
plt.close()
print(" Figure 2: Threshold analysis saved")


importances = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(
    ascending=True
)

category_colors = {
    "RSI": "#4472C4",
    "MACD": "#ED7D31",
    "EMA": "#ED7D31",
    "Price": "#ED7D31",
    "BB": "#A9D18E",
    "ATR": "#A9D18E",
    "Vol": "#A9D18E",
    "Volume": "#FFD966",
    "OBV": "#FFD966",
    "Ret": "#9DC3E6",
    "In_": "#C5A5CF",
    "HL": "#C5A5CF",
    "Gap": "#C5A5CF",
}

bar_colors = []
for feat in importances.index:
    color = "#AAAAAA"
    for prefix, category_color in category_colors.items():
        if feat.startswith(prefix):
            color = category_color
            break
    bar_colors.append(color)

fig, ax = plt.subplots(figsize=(9, 8))
bars = ax.barh(
    importances.index,
    importances.values,  # type: ignore
    color=bar_colors,
    edgecolor="none",
    height=0.7,
)
ax.axvline(
    1 / len(FEATURE_COLS),
    color="red",
    linestyle="--",
    linewidth=1.2,
    label="Uniform baseline",
)
ax.set_title(
    f"Feature Importance - Fold {LATEST_FOLD} {MODEL_NAME} Model\n"
    f"({fold_training_label(LATEST_FOLD, FOLD_CONFIGS)})",
    fontsize=13,
)
ax.set_xlabel("Importance Score")
ax.grid(True, alpha=0.2, axis="x")

for bar, val in zip(bars, importances.values):
    ax.text(val + 0.001, bar.get_y() + bar.get_height() / 2, f"{val:.3f}", va="center", fontsize=8)

legend_items = [
    Patch(color="#4472C4", label="Momentum (RSI)"),
    Patch(color="#ED7D31", label="Momentum (MACD/EMA/Price)"),
    Patch(color="#A9D18E", label="Volatility (BB/ATR)"),
    Patch(color="#FFD966", label="Volume (OBV)"),
    Patch(color="#9DC3E6", label="Returns"),
    Patch(color="#C5A5CF", label="Context"),
]
ax.legend(handles=legend_items, fontsize=8, loc="lower right")

plt.tight_layout()
plt.savefig(REPORT_DIR / f"fig3_feature_importance{MODEL_SUFFIX}.png", dpi=150)
plt.close()
print(" Figure 3: Feature importance saved")


fold_summary = []

for fold_num in PRED_FOLDS:
    fd = preds[preds["Fold"] == fold_num].dropna(
        subset=[LABEL_COL, "Pred_proba", "Fwd_ret_10d"]
    )

    fpr, tpr, _ = roc_curve(fd[LABEL_COL], fd["Pred_proba"])
    fold_auc = auc(fpr, tpr)

    trades = fd[fd["Pred_proba"] >= PROB_THRESHOLD].copy()
    trades["Net_return"] = trades["Fwd_ret_10d"] - TRANS_COST
    net = trades["Net_return"].dropna()

    fold_summary.append(
        {
            "fold": fold_num,
            "year": fold_period_label(fold_num, FOLD_CONFIGS),
            "auc": fold_auc,
            "sharpe": annualized_sharpe(net, min_count=11),
        }
    )

fsdf = pd.DataFrame(fold_summary)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

bar_colors_auc = [
    "#c0392b" if value < 0.50 else "#f39c12" if value < 0.54 else "#27ae60"
    for value in fsdf["auc"]
]
ax1.bar(fsdf["year"], fsdf["auc"], color=bar_colors_auc, edgecolor="none")
ax1.axhline(0.50, color="black", linestyle="--", linewidth=1.2, label="Random (0.50)")
ax1.axhline(
    fsdf["auc"].mean(),
    color="steelblue",
    linestyle=":",
    linewidth=1.2,
    label=f"Mean ({fsdf['auc'].mean():.3f})",
)
ax1.set_title("AUC per Fold")
ax1.set_ylabel("ROC-AUC")
ax1.set_ylim([0.44, 0.62])
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

bar_colors_sr = [
    "#c0392b" if value < 0 else "#f39c12" if value < 0.5 else "#27ae60"
    for value in fsdf["sharpe"]
]
ax2.bar(fsdf["year"], fsdf["sharpe"], color=bar_colors_sr, edgecolor="none")
ax2.axhline(0, color="black", linestyle="--", linewidth=1.2)
ax2.axhline(0.5, color="steelblue", linestyle=":", linewidth=1.2, label="0.5 target")
ax2.set_title(f"Sharpe Ratio per Fold (threshold={PROB_THRESHOLD})")
ax2.set_ylabel("Annualised Sharpe Ratio")
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

plt.suptitle(
    "Walk-Forward Performance by Year\nRed = poor, Orange = marginal, Green = good",
    fontsize=13,
)
plt.tight_layout()
plt.savefig(REPORT_DIR / f"fig4_fold_performance{MODEL_SUFFIX}.png", dpi=150)
plt.close()
print(" Figure 4: Fold performance saved")


sig_mask = (
    (preds["Signal_RSI_oversold"] == 1)
    | (preds["Signal_MACD_cross"] == 1)
    | (preds["Signal_BB_lower"] == 1)
)
sig_net = (preds[sig_mask]["Fwd_ret_10d"] - TRANS_COST).dropna()
sig_pf = profit_factor(sig_net)
sig_sharpe = annualized_sharpe(sig_net)

print("\n" + "=" * 65)
print("FINAL SUMMARY TABLE - for your project report")
print("=" * 65)

summary_rows = []
for thresh in [0.55, 0.60, 0.65]:
    trades = preds[preds["Pred_proba"] >= thresh].copy()
    trades["Net_return"] = trades["Fwd_ret_10d"] - TRANS_COST
    net = trades["Net_return"].dropna()
    pf = profit_factor(net)

    summary_rows.append(
        {
            "Threshold": thresh,
            "Trades": len(net),
            "Win Rate %": round((net > 0).mean() * 100, 1),
            "Profit Factor": round(pf, 3) if np.isfinite(pf) else "inf",
            "Mean Ret/Trade %": round(net.mean() * 100, 4),
            "Sharpe (ann.)": round(annualized_sharpe(net), 3),
            "Signal-only PF": round(sig_pf, 3) if np.isfinite(sig_pf) else "inf",
            "PF Lift vs Signal-only": round(pf - sig_pf, 3)
            if np.isfinite(pf) and np.isfinite(sig_pf)
            else np.nan,
        }
    )

summary_df = pd.DataFrame(summary_rows)
print(summary_df.to_string(index=False))

print("\nBaseline (signal-only, no ML filter):")
print(
    f"  Trades: {len(sig_net):,} | Win Rate: {(sig_net > 0).mean() * 100:.1f}% | "
    f"Profit Factor: {sig_pf:.3f} | Sharpe: {sig_sharpe:.3f}"
)


print("\n" + "=" * 65)
print("SIGNAL INTERPRETER - most recent signals across all stocks")
print("=" * 65)

full_df = pd.read_parquet(PROCESSED_DIR / "all_stocks_features.parquet")
full_df["Date"] = pd.to_datetime(full_df["Date"])

latest = full_df.sort_values("Date").groupby("Symbol").tail(1).copy()
latest_complete_symbols = set(latest.dropna(subset=FEATURE_COLS)["Symbol"])

latest_clean = (
    full_df.dropna(subset=FEATURE_COLS)
    .sort_values("Date")
    .groupby("Symbol", group_keys=False)
    .tail(1)
    .copy()
)

fallback_symbols = set(latest_clean["Symbol"]) - latest_complete_symbols
if fallback_symbols:
    print(
        "Using each symbol's most recent complete-feature row for "
        f"{len(fallback_symbols)} symbols with incomplete latest rows."
    )

if latest_clean.empty:
    print("No complete feature rows found for signal interpretation.")
    latest_clean = latest.head(0).copy()
    latest_clean["ML_confidence"] = np.nan
else:
    x_latest = scaler.transform(latest_clean[FEATURE_COLS].values)
    latest_clean["ML_confidence"] = model.predict_proba(x_latest)[:, 1]

latest_clean["Active_signals"] = latest_clean.apply(active_signal_text, axis=1)

high_conf = (
    latest_clean[latest_clean["ML_confidence"] >= 0.60][
        ["Symbol", "Date", "Close", "RSI_14", "Active_signals", "ML_confidence"]
    ]
    .sort_values("ML_confidence", ascending=False)
    .head(20)
)

if len(high_conf) > 0:
    print("\nStocks with ML confidence >= 0.60 as of latest data:")
    print(f"{'Symbol':<8} {'Date':<12} {'Close':>8} {'RSI':>6} {'Signals':<20} {'Confidence':>10}")
    print("-" * 68)
    for _, row in high_conf.iterrows():
        print(
            f"  {row['Symbol']:<6} {str(row['Date'].date()):<12} "
            f"{row['Close']:>8.2f} {row['RSI_14']:>6.1f} "
            f"{row['Active_signals']:<20} {row['ML_confidence']:>10.3f}"
        )
else:
    print("No stocks currently above 0.60 confidence threshold.")

print(f"\nConfidence distribution across all {len(latest_clean)} stocks:")
for low, high, label in [
    (0.0, 0.45, "Low (<0.45)"),
    (0.45, 0.55, "Neutral (0.45-0.55)"),
    (0.55, 0.65, "Moderate (0.55-0.65)"),
    (0.65, 1.01, "High (>0.65)"),
]:
    count = (
        (latest_clean["ML_confidence"] >= low)
        & (latest_clean["ML_confidence"] < high)
    ).sum()
    print(f"  {label:<25}: {count:>3} stocks")


summary_df.to_csv(REPORT_DIR / f"summary_table{MODEL_SUFFIX}.csv", index=False)
latest_clean[
    [
        "Symbol",
        "Date",
        "Close",
        "RSI_14",
        "MACD",
        "BB_pctB",
        "Volume_ratio",
        "ML_confidence",
        "Active_signals",
    ]
].to_csv(REPORT_DIR / f"latest_signals{MODEL_SUFFIX}.csv", index=False)

print(f"\n Report figures saved to: {REPORT_DIR}")
print(f"   fig1_roc_curves{MODEL_SUFFIX}.png")
print(f"   fig2_threshold_analysis{MODEL_SUFFIX}.png")
print(f"   fig3_feature_importance{MODEL_SUFFIX}.png")
print(f"   fig4_fold_performance{MODEL_SUFFIX}.png")
print(f"   summary_table{MODEL_SUFFIX}.csv")
print(f"   latest_signals{MODEL_SUFFIX}.csv")
print("\n All steps complete. Your project pipeline is fully built.")
