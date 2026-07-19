"""
Statistical toolkit shared by the training/backtest/reporting scripts.

Adds the measures the pipeline was missing: uncertainty bounds on point
estimates (bootstrap CI), a significance test for the "ML filter beats
signal-only" claim, probability calibration, importance that's stable
across folds, and a redundant-feature audit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score


def bootstrap_ci(
    values: np.ndarray,
    statistic=np.mean,
    n_boot: int = 2000,
    ci: float = 0.95,
    random_state: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap CI for any 1D statistic (mean, win-rate, Sharpe, ...).

    Returns (point_estimate, lower, upper).
    """
    values = np.asarray(values)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return (np.nan, np.nan, np.nan)

    rng = np.random.default_rng(random_state)
    point = statistic(values)
    boot_stats = np.empty(n_boot)
    n = len(values)
    for i in range(n_boot):
        sample = values[rng.integers(0, n, n)]
        boot_stats[i] = statistic(sample)

    alpha = (1 - ci) / 2
    lower, upper = np.quantile(boot_stats, [alpha, 1 - alpha])
    return (point, lower, upper)


def bootstrap_auc_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    random_state: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap CI for ROC-AUC. Resamples (row, label, score) pairs together."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    rng = np.random.default_rng(random_state)
    n = len(y_true)
    point = roc_auc_score(y_true, y_score)

    boot_aucs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yt, ys = y_true[idx], y_score[idx]
        if len(np.unique(yt)) < 2:
            continue
        boot_aucs.append(roc_auc_score(yt, ys))

    if not boot_aucs:
        return (point, np.nan, np.nan)

    alpha = (1 - ci) / 2
    lower, upper = np.quantile(boot_aucs, [alpha, 1 - alpha])
    return (point, lower, upper)


def compare_strategies(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    label_a: str = "A",
    label_b: str = "B",
    n_boot: int = 2000,
    random_state: int = 42,
) -> dict:
    """Test whether strategy A's net returns are significantly better than B's.

    The two return series come from different, unpaired trade sets (different
    entry masks/dates/sizes), so this uses a two-sample Mann-Whitney U test
    (no pairing or normality assumption) plus a bootstrap CI on the
    difference in mean return for effect size.
    """
    a = np.asarray(returns_a)
    a = a[~np.isnan(a)]
    b = np.asarray(returns_b)
    b = b[~np.isnan(b)]

    if len(a) < 5 or len(b) < 5:
        return {
            "label_a": label_a, "label_b": label_b,
            "n_a": len(a), "n_b": len(b),
            "mean_diff": np.nan, "ci_low": np.nan, "ci_high": np.nan,
            "u_statistic": np.nan, "p_value": np.nan, "significant": False,
        }

    u_stat, p_value = stats.mannwhitneyu(a, b, alternative="greater")

    rng = np.random.default_rng(random_state)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        sa = a[rng.integers(0, len(a), len(a))]
        sb = b[rng.integers(0, len(b), len(b))]
        diffs[i] = sa.mean() - sb.mean()
    ci_low, ci_high = np.quantile(diffs, [0.025, 0.975])

    return {
        "label_a": label_a, "label_b": label_b,
        "n_a": len(a), "n_b": len(b),
        "mean_diff": a.mean() - b.mean(),
        "ci_low": ci_low, "ci_high": ci_high,
        "u_statistic": u_stat, "p_value": p_value,
        "significant": bool(p_value < 0.05),
    }


def calibration_report(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[pd.DataFrame, float]:
    """Reliability table (predicted vs actual win rate per probability bin) + Brier score.

    Brier score = mean squared error between predicted probability and
    outcome; 0 is perfect, 0.25 is what a constant 0.5 predictor gets.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)

    brier = float(np.mean((y_prob - y_true) ** 2))

    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.clip(np.digitize(y_prob, bins) - 1, 0, n_bins - 1)

    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        rows.append({
            "bin_low": bins[b],
            "bin_high": bins[b + 1],
            "count": int(mask.sum()),
            "mean_predicted": y_prob[mask].mean(),
            "mean_actual": y_true[mask].mean(),
        })

    return pd.DataFrame(rows), brier


def permutation_importance_single_fold(
    model,
    scaler,
    X_test_raw: np.ndarray,
    y_test: np.ndarray,
    n_repeats: int = 10,
    random_state: int = 42,
    scoring: str = "roc_auc",
) -> np.ndarray:
    """Permutation importance for one fold's held-out test set.

    Call this right after training each fold, instead of collecting every
    fold's model/scaler/test-data into a list and processing them all at
    the end - holding N folds' full models (e.g. 9 Random Forests with 400
    trees each, plus their joblib worker pools) resident simultaneously is
    what caused an out-of-memory pickle-write crash on a 16GB machine (see
    06_train_model.py / 06b_train_sell_model.py). Keeping only one fold's
    model in memory at a time bounds peak memory to a single fold.

    Returns the raw importances_mean array (aligned with the feature column
    order used to build X_test_raw) - aggregate across folds with
    aggregate_importance_arrays.
    """
    X_test = scaler.transform(X_test_raw)
    result = permutation_importance(
        model, X_test, y_test,
        n_repeats=n_repeats, random_state=random_state,
        scoring=scoring, n_jobs=-1,
    )
    return result.importances_mean


def aggregate_importance_arrays(
    per_fold_importances: list[np.ndarray],
    feature_cols: list[str],
) -> pd.DataFrame:
    """Aggregate mean/std of per-fold importance arrays (see
    permutation_importance_single_fold) into one ranked table.

    Gain/impurity importance (what the pipeline used before) is biased
    toward high-cardinality/correlated features and only ever looked at one
    fold's model. This aggregates a model-agnostic importance computed per
    fold on that fold's own test data — a feature only ranks highly here if
    it consistently helps out-of-sample.
    """
    stacked = np.vstack(per_fold_importances)  # (n_folds, n_features)
    return pd.DataFrame({
        "feature": feature_cols,
        "importance_mean": stacked.mean(axis=0),
        "importance_std": stacked.std(axis=0),
        "n_folds": stacked.shape[0],
    }).sort_values("importance_mean", ascending=False).reset_index(drop=True)


def correlation_redundancy_audit(
    df: pd.DataFrame,
    feature_cols: list[str],
    threshold: float = 0.85,
) -> pd.DataFrame:
    """Flag feature pairs with |correlation| above threshold.

    High correlation between two features means gain-based importance can
    arbitrarily split credit between them, or one masks the other. Doesn't
    auto-drop anything — just surfaces candidates for manual pruning.
    """
    corr = df[feature_cols].corr().abs()
    pairs = []
    cols = corr.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            value = corr.iloc[i, j]
            if value >= threshold:
                pairs.append({
                    "feature_a": cols[i],
                    "feature_b": cols[j],
                    "abs_correlation": value,
                })

    return pd.DataFrame(pairs).sort_values(
        "abs_correlation", ascending=False
    ).reset_index(drop=True) if pairs else pd.DataFrame(
        columns=["feature_a", "feature_b", "abs_correlation"]
    )
