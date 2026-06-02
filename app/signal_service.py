"""
Signal generation service: Centralized logic for computing and interpreting signals.
Handles confidence scoring, verdicts, descriptions, and indicator context.
"""

from typing import Optional, List, Dict, Tuple
import pandas as pd
import numpy as np
import os

from app.data_loader import DataLoader
from app.constants import THRESHOLD_HIGH, THRESHOLD_MEDIUM, THRESHOLD_LOW
from app.logging_config import get_logger
from app.config import settings
import glob
import pickle
import re

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
    """Generate and interpret signals for stocks."""
    
    def __init__(self, loader: DataLoader):
        self.loader = loader
    
    def compute_confidence(self, symbol: str) -> Optional[float]:
        """Compute BUY confidence score from default (loaded) model."""
        return self.compute_confidence_for_family(symbol, None)

    def compute_confidence_for_family(self, symbol: str, family: Optional[str]) -> Optional[float]:
        """Compute BUY confidence using a specific model family (xgboost or random_forest).

        If family is None, use the loader's default in-memory model.
        """
        latest_row = self.loader.get_latest_row(symbol)
        if latest_row is None:
            return None

        if family is None:
            model = self.loader.model_buy
            scaler = self.loader.scaler_buy
            features = self.loader.feature_cols
        else:
            bundle = self.loader.get_bundle_for_family(family)
            if not bundle:
                return None
            model = bundle.get("model")
            scaler = bundle.get("scaler")
            features = bundle.get("features")

        if model is None or scaler is None or features is None:
            return None

        try:
            X = scaler.transform(latest_row[features].values.reshape(1, -1))
            conf = float(model.predict_proba(X)[0, 1])
            return round(conf, 4)
        except Exception as e:
            logger.error(f"Error computing BUY confidence for {symbol} (family={family}): {e}")
            return None
    
    def compute_sell_confidence(self, symbol: str) -> Optional[float]:
        """Compute SELL confidence using default loaded SELL model."""
        return self.compute_sell_confidence_for_family(symbol, None)

    def compute_sell_confidence_for_family(self, symbol: str, family: Optional[str]) -> Optional[float]:
        """Compute SELL confidence using a specific family. If family is None, use in-memory SELL model."""
        latest_row = self.loader.get_latest_row(symbol)
        if latest_row is None:
            return None

        if family is None:
            model = self.loader.model_sell
            scaler = self.loader.scaler_sell
            features = self.loader.feature_cols
        else:
            # Look for a sell model for the family (filename suffix _sell)
            bundle = self.loader.get_bundle_for_family(family)
            if not bundle:
                return None
            # For sell, expect file with _sell; the bundle loader returns BUY models only,
            # so attempt to load sell model by pattern here
            suffix = "" if family == "xgboost" else "_rf"
            sell_path = None
            sell_pattern = f"model_fold*{suffix}_sell.pkl"
            candidates = glob.glob(str(settings.model_dir / sell_pattern))
            if not suffix:
                candidates = [p for p in candidates if "_rf" not in os.path.basename(p)]
            if candidates:
                def _fold_num(p):
                    m = re.search(rf"model_fold(\d+){re.escape(suffix)}_sell\.pkl$", os.path.basename(p))
                    return int(m.group(1)) if m else -1
                sell_path = max(candidates, key=_fold_num)

            if sell_path:
                try:
                    with open(sell_path, "rb") as f:
                        sb = pickle.load(f)
                        model = sb.get("model")
                        scaler = sb.get("scaler")
                        features = sb.get("feature_cols") or sb.get("features")
                except Exception as e:
                    logger.error(f"Failed loading SELL model for family {family}: {e}")
                    return None
            else:
                return None

        if model is None or scaler is None or features is None:
            return None

        try:
            X = scaler.transform(latest_row[features].values.reshape(1, -1))
            conf = float(model.predict_proba(X)[0, 1])
            return round(conf, 4)
        except Exception as e:
            logger.error(f"Error computing SELL confidence for {symbol} (family={family}): {e}")
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
        # BUY signal takes priority
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
        
        # Check for SELL signals (only if SELL model is available)
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
        """Get complete signal for a stock (BUY + SELL models).

        If `family` is provided, compute confidences using that model family.
        """
        latest_row = self.loader.get_latest_row(symbol)
        if latest_row is None:
            return None
        
        buy_confidence = self.compute_confidence_for_family(symbol, family) if family else self.compute_confidence(symbol)
        if buy_confidence is None:
            return None
        
        # SELL confidence is optional (if SELL model not available, remains None)
        sell_confidence = self.compute_sell_confidence_for_family(symbol, family) if family else self.compute_sell_confidence(symbol)
        
        verdict, color, description = self.get_verdict(buy_confidence, sell_confidence)
        indicators = self.get_indicator_context(latest_row)
        active_signals = self.get_active_signals(latest_row)
        
        signal_data = {
            "symbol": symbol,
            "date": str(latest_row["Date"].date()),
            "close": safe_val(latest_row.get("Close")),
            "buy_confidence": round(buy_confidence, 3),
            "sell_confidence": round(sell_confidence, 3) if sell_confidence else None,
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
        
        return signal_data
