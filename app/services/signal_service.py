"""
Signal generation service: centralized business logic for computing and
interpreting BUY/SELL confidence signals.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config import settings
from app.constants import THRESHOLD_HIGH, THRESHOLD_LOW, THRESHOLD_MEDIUM
from app.logging_config import get_logger
from app.repositories.model_repository import ModelRepository
from app.repositories.stock_repository import StockRepository

logger = get_logger(__name__)


def safe_val(v):
    """Convert values to safe JSON types, handling NaN and inf."""
    if pd.isna(v) or (isinstance(v, float) and np.isinf(v)):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return round(float(v), 4)
    return v


class SignalService:
    """Generate and interpret BUY/SELL signals for stocks."""

    def __init__(self, model_repository: ModelRepository, stock_repository: StockRepository):
        self.models = model_repository
        self.stocks = stock_repository
        self._confidence_cache: Dict[Tuple[str, str, str], Optional[float]] = {}
        self._relative_strength_cache: Dict[str, Optional[float]] = {}
        self._cache_data_version: Optional[float] = None

    def is_liquid_enough(self, symbol: str) -> bool:
        """Return True when a symbol has enough recent trading activity for display."""
        stock_df = self.stocks.get_stock_data(symbol, settings.liquidity_lookback_days)
        if stock_df is None or stock_df.empty:
            return False

        traded = stock_df.dropna(subset=["Close", "Volume"]).copy()
        traded = traded[(traded["Close"] > 0) & (traded["Volume"] > 0)]
        if len(traded) < settings.min_liquid_trading_days:
            return False

        turnover = traded.get("Turnover")
        if turnover is None:
            turnover = traded["Close"] * traded["Volume"]
        else:
            turnover = turnover.fillna(traded["Close"] * traded["Volume"])

        return (
            float(traded["Volume"].median()) >= settings.min_median_volume
            and float(turnover.median()) >= settings.min_median_turnover
        )

    @staticmethod
    def verdict_code(buy_confidence: float, sell_confidence: Optional[float]) -> str:
        if buy_confidence >= 0.65:
            return "BUY"
        if buy_confidence >= 0.55:
            return "MODERATE"
        if sell_confidence is not None and sell_confidence >= 0.65:
            return "SELL"
        if sell_confidence is not None and sell_confidence >= 0.55:
            return "WEAK_SELL"
        if buy_confidence >= THRESHOLD_LOW:
            return "HOLD"
        return "AVOID"

    def compute_confidence(self, symbol: str) -> Optional[float]:
        """Compute BUY confidence score from the default (loaded) model."""
        return self.compute_confidence_for_family(symbol, None)

    def compute_confidence_for_family(self, symbol: str, family: Optional[str]) -> Optional[float]:
        """Compute BUY confidence using a specific model family (or the default if family is None)."""
        return self._cached_predict(symbol, family, kind="BUY")

    def compute_sell_confidence(self, symbol: str) -> Optional[float]:
        """Compute SELL confidence using the default loaded SELL model."""
        return self.compute_sell_confidence_for_family(symbol, None)

    def compute_sell_confidence_for_family(self, symbol: str, family: Optional[str]) -> Optional[float]:
        """Compute SELL confidence using a specific family (or the default if family is None)."""
        return self._cached_predict(symbol, family, kind="SELL")

    def compute_relative_strength(self, symbol: str) -> Optional[float]:
        """P(this stock beats the average NEPSE stock's return over the next
        10 days) - NOT a profit signal. A stock can score high here while
        still losing money in a falling market; it answers a relative
        question, not an absolute one. See src/06c_train_relative_model.py
        and app/schemas.py for the full caveat served alongside this value.
        """
        self._invalidate_caches_if_stale()

        if symbol in self._relative_strength_cache:
            return self._relative_strength_cache[symbol]

        bundle = self.models.get_relative_bundle()
        result = self._predict(symbol, bundle, family=None, kind="RELATIVE")
        self._relative_strength_cache[symbol] = result
        return result

    def _invalidate_caches_if_stale(self) -> None:
        """Both _confidence_cache and _relative_strength_cache must be
        cleared together on a data-version bump - clearing only one (e.g.
        each cache-user checking the version independently) lets whichever
        method runs first "claim" the version change and leave the other
        cache stale for that request."""
        current_version = self.stocks.data_version()
        if current_version != self._cache_data_version:
            self._confidence_cache.clear()
            self._relative_strength_cache.clear()
            self._cache_data_version = current_version

    def _cached_predict(self, symbol: str, family: Optional[str], kind: str) -> Optional[float]:
        """Memoize per-symbol confidence for the lifetime of the current data version.

        /api/stocks and /api/summary would otherwise re-run predict_proba for
        every symbol on every request even though the feature data (and
        therefore the result) only changes once per daily pipeline run.
        """
        self._invalidate_caches_if_stale()

        cache_key = (symbol, family or "__default__", kind)
        if cache_key in self._confidence_cache:
            return self._confidence_cache[cache_key]

        bundle = self.models.get_buy_bundle(family) if kind == "BUY" else self.models.get_sell_bundle(family)
        result = self._predict(symbol, bundle, family, kind)
        self._confidence_cache[cache_key] = result
        return result

    def _predict(self, symbol: str, bundle: Optional[Dict], family: Optional[str], kind: str) -> Optional[float]:
        predictor = bundle and (bundle.get("calibrator") or bundle.get("model"))
        if not bundle or predictor is None or bundle.get("scaler") is None or not bundle.get("features"):
            return None

        features = bundle["features"]
        latest_row = self.stocks.get_latest_row(symbol, required_columns=features)
        if latest_row is None:
            return None

        try:
            X = bundle["scaler"].transform(latest_row[features].values.reshape(1, -1))
            # Raw model probabilities are overconfident (confirmed via calibration
            # curve - a 0.63 raw score only won ~40% of the time). The calibrator
            # (CalibratedClassifierCV, fit in 06_train_model.py) corrects this;
            # fall back to the raw model only for older bundles that predate it.
            conf = float(predictor.predict_proba(X)[0, 1])
            return round(conf, 4)
        except Exception as e:
            logger.error("Error computing %s confidence for %s (family=%s): %s", kind, symbol, family, e)
            return None

    def get_tier(self, confidence: float) -> str:
        """Get tier (High/Medium/Low) from confidence using unified thresholds."""
        if confidence >= THRESHOLD_HIGH:
            return "High"
        elif confidence >= THRESHOLD_MEDIUM:
            return "Medium"
        elif confidence >= THRESHOLD_LOW:
            return "Low"
        else:
            return "Weak"

    def get_active_signals(self, row: pd.Series) -> List[str]:
        """Extract active signals from row."""
        signals = []
        if safe_val(row.get("Signal_RSI_oversold")):
            signals.append("RSI Oversold Recovery")
        if safe_val(row.get("Signal_MACD_cross")):
            signals.append("MACD Bullish Crossover")
        if safe_val(row.get("Signal_BB_lower")):
            signals.append("BB Lower Band Touch")
        return signals

    def get_indicator_context(self, row: pd.Series) -> Dict:
        """Extract and interpret indicator values from row."""
        rsi_val = safe_val(row.get("RSI_14"))
        rsi_zone = ("oversold" if rsi_val and rsi_val < 30 else
                   "overbought" if rsi_val and rsi_val > 70 else
                   "neutral")

        macd_val = safe_val(row.get("MACD"))
        macd_sig = safe_val(row.get("MACD_Signal"))
        macd_hist = round((macd_val or 0) - (macd_sig or 0), 4)
        macd_bias = "bullish" if macd_hist > 0 else "bearish"

        bb_pctb = safe_val(row.get("BB_pctB"))
        bb_zone = ("below lower band" if bb_pctb and bb_pctb < 0 else
                  "above upper band" if bb_pctb and bb_pctb > 1 else
                  "within bands")

        in_uptrend = bool(safe_val(row.get("In_uptrend")))
        vol_ratio = safe_val(row.get("Volume_ratio"))
        vol_note = ("high volume" if vol_ratio and vol_ratio > 2 else
                   "low volume" if vol_ratio and vol_ratio < 0.5 else
                   "normal volume")

        return {
            "rsi": rsi_val,
            "rsi_zone": rsi_zone,
            "macd": macd_val,
            "macd_signal": macd_sig,
            "macd_hist": macd_hist,
            "macd_bias": macd_bias,
            "bb_pctb": bb_pctb,
            "bb_zone": bb_zone,
            "in_uptrend": in_uptrend,
            "volume_ratio": vol_ratio,
            "volume_note": vol_note,
        }

    def get_verdict(self, buy_confidence: float, sell_confidence: Optional[float] = None) -> Tuple[str, str, str]:
        """Get verdict (text), color, and description based on buy and sell confidences.

        5-level signal system:
        - buy_conf >= 0.65: BUY (green) — Strong buy opportunity
        - buy_conf >= 0.55: MODERATE (orange) — Some buy potential
        - sell_conf >= 0.65: SELL (red) — High downside risk
        - sell_conf >= 0.55: WEAK_SELL (yellow) — Some downside risk
        - else: HOLD (gray) — No clear signal

        Important: Model outputs probabilities.
        - BUY confidence: P(stock goes up >1% in 10 days)
        - SELL confidence: P(stock drops >1% in 10 days)
        """
        if buy_confidence >= THRESHOLD_HIGH:
            verdict = "Strong buy signal"
            color = "green"
            description = ("Stock shows strong upward momentum 📈. More buyers than sellers. "
                          "Our AI thinks this stock will likely go up in the next 10 days. "
                          "This is a good time to consider buying. "
                          "Remember: Check company news first and set a stop-loss 5-10% below to limit losses.")

        elif buy_confidence >= THRESHOLD_MEDIUM:
            verdict = "Moderate buy signal"
            color = "orange"
            description = ("Stock shows some bullish signs 📊, but not strong enough for a confident buy. "
                          "Wait for a better entry price (a 5% dip) or more confirmation signals. "
                          "If you buy now, use a smaller position size.")

        elif sell_confidence and sell_confidence >= THRESHOLD_HIGH:
            verdict = "Sell signal"
            color = "red"
            description = ("Stock shows bearish signals 📉 with HIGH downside risk. More sellers than buyers. "
                          "Our AI predicts this stock will likely drop >1% in the next 10 days. "
                          "This is NOT a good time to buy. "
                          "If you already own it, consider selling into strength (during rallies). "
                          "Otherwise, stay away and look for better opportunities.")

        elif sell_confidence and sell_confidence >= THRESHOLD_MEDIUM:
            verdict = "Weak sell signal"
            color = "yellow"
            description = ("Stock shows some bearish signs ⚠️ with SOME downside risk. "
                          "Our AI predicts a modest chance (>55%) the stock will drop in the next 10 days. "
                          "Risky to buy now. If you own it, consider taking some profits. "
                          "Better to wait for more bullish confirmation.")

        elif buy_confidence >= THRESHOLD_LOW:
            verdict = "Weak signal"
            color = "gray"
            description = ("We can't see a clear reason to buy this stock right now ⚪. "
                          "This stock is in a holding pattern with no strong momentum either direction. "
                          "Better opportunities might appear later. "
                          "If you already own it, hold or consider taking some profits.")

        else:
            verdict = "Avoid for now"
            color = "red"
            description = ("Stock shows neutral to bearish signals. "
                          "Neither a strong buy nor a strong sell opportunity. "
                          "Better to wait for clearer signals or look elsewhere.")

        return verdict, color, description

    def get_signal(self, symbol: str, family: Optional[str] = None) -> Optional[Dict]:
        """Get complete signal for a stock (BUY + SELL models)."""
        buy_confidence = self.compute_confidence_for_family(symbol, family) if family else self.compute_confidence(symbol)
        if buy_confidence is None:
            return None

        sell_confidence = self.compute_sell_confidence_for_family(symbol, family) if family else self.compute_sell_confidence(symbol)
        relative_strength = self.compute_relative_strength(symbol)

        buy_bundle = self.models.get_buy_bundle(family)
        latest_row = self.stocks.get_latest_row(symbol, required_columns=buy_bundle["features"] if buy_bundle else None)
        if latest_row is None:
            return None

        verdict, color, description = self.get_verdict(buy_confidence, sell_confidence)
        indicators = self.get_indicator_context(latest_row)
        active_signals = self.get_active_signals(latest_row)

        return {
            "symbol": symbol,
            "date": str(latest_row["Date"].date()),
            "close": safe_val(latest_row.get("Close")),
            "buy_confidence": round(buy_confidence, 3),
            "sell_confidence": round(sell_confidence, 3) if sell_confidence else None,
            "relative_strength": round(relative_strength, 3) if relative_strength is not None else None,
            "relative_strength_note": (
                "P(beats the average NEPSE stock over 10 days) - not a profit signal; "
                "a stock can score high here while still losing money in a falling market."
            ),
            "verdict": verdict,
            "verdict_color": color,
            "description": description,
            "active_signals": active_signals,
            "indicators": indicators,
            "thresholds": {
                "buy_high": THRESHOLD_HIGH,
                "buy_medium": THRESHOLD_MEDIUM,
                "buy_low": THRESHOLD_LOW,
            }
        }
