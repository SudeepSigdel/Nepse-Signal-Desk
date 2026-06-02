"""
Data loader: Centralized model, scaler, features, and config loading.
Handles all initialization logic in one place for easy testing and maintenance.
"""

import json
import glob
import os
import pickle
import re
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _normalize_model_family(raw_family: Optional[str]) -> str:
    family = (raw_family or "xgboost").strip().lower().replace("-", "_")
    if family in {"rf", "randomforest", "random_forest", "random forest"}:
        return "random_forest"
    return "xgboost"


def _family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


def _buy_model_pattern_for_family(family: str) -> str:
    suffix = _family_suffix(family)
    return f"model_fold*{suffix}.pkl"


def _latest_buy_model_name(family: str) -> str:
    return f"model_latest{_family_suffix(family)}.pkl"


def _latest_sell_model_name(family: str) -> str:
    return f"model_latest{_family_suffix(family)}_sell.pkl"


def _model_sort_key(path: str, family: str, sell: bool = False) -> int:
    basename = os.path.basename(path)
    if basename == (_latest_sell_model_name(family) if sell else _latest_buy_model_name(family)):
        return 10**9

    suffix = _family_suffix(family)
    pattern = (
        rf"model_fold(\d+){re.escape(suffix)}_sell\.pkl$"
        if sell
        else rf"model_fold(\d+){re.escape(suffix)}\.pkl$"
    )
    match = re.search(pattern, basename)
    return int(match.group(1)) if match else -1


class DataLoader:
    """Loads and manages ML model, features, scaler, and configuration."""
    
    _instance = None  # For singleton pattern
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model_buy = None
        self.model_sell = None
        self.scaler_buy = None
        self.scaler_sell = None
        self.feature_cols = None
        self.config = {}
        self.features_df = None
        self.all_symbols = []
        self.model_family = self._select_model_family(settings.model_family)
        self._family_bundles: Dict[str, Dict[str, Any]] = {}
        
        self._load_all()
        self._initialized = True

    def _has_buy_model_for_family(self, family: str) -> bool:
        suffix = _family_suffix(family)
        candidates = glob.glob(str(settings.model_dir / _buy_model_pattern_for_family(family)))
        candidates.extend(glob.glob(str(settings.model_dir / _latest_buy_model_name(family))))
        candidates = [p for p in candidates if "_sell" not in os.path.basename(p)]
        if not suffix:
            candidates = [p for p in candidates if "_rf" not in os.path.basename(p)]
        return bool(candidates)

    def _select_model_family(self, requested_family: Optional[str]) -> str:
        """Use the requested family when available; otherwise fall back to local artifacts."""
        requested = _normalize_model_family(requested_family)
        if self._has_buy_model_for_family(requested):
            return requested

        for candidate in ("random_forest", "xgboost"):
            if candidate != requested and self._has_buy_model_for_family(candidate):
                logger.warning(
                    "Requested model family '%s' has no BUY model; falling back to '%s'",
                    requested,
                    candidate,
                )
                return candidate

        return requested
    
    def _load_all(self):
        """Load all components in order."""
        logger.info("DataLoader: Initializing...")
        self._load_config()
        self._load_models()
        self._load_features()
        logger.info(f"DataLoader: Ready. {len(self.all_symbols)} symbols loaded.")
    
    def _load_config(self):
        """Load fold config."""
        config_path = settings.data_processed_dir / "fold_config.json"
        try:
            with open(config_path, encoding="utf-8") as f:
                self.config = json.load(f)
            logger.info(f"Loaded config from {config_path}")
        except FileNotFoundError as e:
            logger.warning(f"fold_config.json not found; using model bundle features when available: {e}")
            self.config = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in fold_config.json: {e}")
            self.config = {}
    
    def _load_models(self):
        """Load both BUY and SELL models from model_fold*.pkl and model_fold*_sell.pkl files."""
        suffix = _family_suffix(self.model_family)

        # Load BUY model (latest fold for the selected family)
        buy_pattern = _buy_model_pattern_for_family(self.model_family)
        buy_candidates = glob.glob(str(settings.model_dir / buy_pattern))
        buy_candidates.extend(glob.glob(str(settings.model_dir / _latest_buy_model_name(self.model_family))))
        buy_candidates = [
            p for p in buy_candidates
            if "_sell" not in os.path.basename(p)
            and (suffix or "_rf" not in os.path.basename(p))
        ]
        
        if buy_candidates:
            model_path = max(buy_candidates, key=lambda path: _model_sort_key(path, self.model_family))
            logger.info(f"Loading BUY model ({self.model_family}) from {model_path}")
            
            try:
                with open(model_path, "rb") as f:
                    bundle = pickle.load(f)
                    self.model_buy = bundle["model"]
                    self.scaler_buy = bundle["scaler"]
                    self.feature_cols = bundle.get("feature_cols") or bundle.get("features") or self.config.get("feature_cols")
                
                if not self.feature_cols:
                    logger.warning("feature_cols missing in both model bundle and fold_config.json")
                else:
                    logger.info(f"BUY model loaded. Features: {len(self.feature_cols)}")
            except Exception as e:
                logger.error(f"Failed to load BUY model: {e}")
                self.model_buy = None
                self.scaler_buy = None
        else:
            logger.error(f"No BUY model files found in {settings.model_dir} for family {self.model_family}")
        
        # Load SELL model (latest fold with _sell suffix and the selected family)
        sell_pattern = f"model_fold*{suffix}_sell.pkl" if suffix else "model_fold*_sell.pkl"
        sell_candidates = glob.glob(str(settings.model_dir / sell_pattern))
        sell_candidates.extend(glob.glob(str(settings.model_dir / _latest_sell_model_name(self.model_family))))
        if not suffix:
            sell_candidates = [p for p in sell_candidates if "_rf" not in os.path.basename(p)]
        
        if sell_candidates:
            model_path = max(sell_candidates, key=lambda path: _model_sort_key(path, self.model_family, sell=True))
            logger.info(f"Loading SELL model ({self.model_family}) from {model_path}")
            
            try:
                with open(model_path, "rb") as f:
                    bundle = pickle.load(f)
                    self.model_sell = bundle["model"]
                    self.scaler_sell = bundle["scaler"]
                logger.info(f"SELL model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load SELL model: {e}")
                self.model_sell = None
                self.scaler_sell = None
        else:
            logger.warning(
                f"No SELL model files found in {settings.model_dir} for family {self.model_family} "
                "(optional - will use BUY only)"
            )

    
    def _load_features(self):
        """Load features parquet file."""
        features_path = settings.data_processed_dir / "all_stocks_features.parquet"
        try:
            self.features_df = pd.read_parquet(features_path)
            self.features_df["Date"] = pd.to_datetime(self.features_df["Date"])
            self.all_symbols = sorted(self.features_df["Symbol"].unique().tolist())
            logger.info(f"Loaded {len(self.features_df)} rows, {len(self.all_symbols)} symbols")
        except FileNotFoundError:
            logger.error(f"Features file not found: {features_path}")
            self.features_df = None
            self.all_symbols = []
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            self.features_df = None
            self.all_symbols = []
    
    def is_ready(self) -> bool:
        """Check if all components are loaded."""
        return (self.model_buy is not None and 
                self.scaler_buy is not None and 
                self.features_df is not None and 
                len(self.all_symbols) > 0)
    
    def get_stock_data(self, symbol: str, days: int = 180) -> Optional[pd.DataFrame]:
        """Get stock data for a symbol."""
        if self.features_df is None:
            return None
        
        stock_df = (self.features_df[self.features_df["Symbol"] == symbol]
                   .sort_values("Date")
                   .tail(days)
                   .copy())
        
        return stock_df if not stock_df.empty else None
    
    def get_latest_row(self, symbol: str) -> Optional[pd.Series]:
        """Get latest row for a symbol."""
        if self.features_df is None or self.feature_cols is None:
            return None
        
        stock_df = self.features_df[self.features_df["Symbol"] == symbol]
        latest = stock_df.dropna(subset=self.feature_cols).sort_values("Date").tail(1)
        
        return latest.iloc[0] if not latest.empty else None
    
    @property
    def model(self):
        """Backward compatibility: return BUY model."""
        return self.model_buy
    
    @property
    def scaler(self):
        """Backward compatibility: return BUY scaler."""
        return self.scaler_buy

    def get_bundle_for_family(self, family: Optional[str]) -> Optional[Dict[str, Any]]:
        """Return a loaded model bundle for the requested family.

        The bundle contains keys: 'model', 'scaler', 'features'. Caches results per instance.
        """
        fam = _normalize_model_family(family)
        cached_bundle = self._family_bundles.get(fam)
        if cached_bundle is not None:
            return cached_bundle

        suffix = _family_suffix(fam)
        # Search for latest BUY model for this family
        buy_pattern = f"model_fold*{suffix}.pkl"
        candidates = glob.glob(str(settings.model_dir / buy_pattern))
        candidates.extend(glob.glob(str(settings.model_dir / _latest_buy_model_name(fam))))
        candidates = [p for p in candidates if "_sell" not in os.path.basename(p)]
        if not suffix:
            candidates = [p for p in candidates if "_rf" not in os.path.basename(p)]

        if not candidates:
            logger.warning(f"No model files found for family '{fam}'")
            self._family_bundles[fam] = None
            return None

        model_path = max(candidates, key=lambda path: _model_sort_key(path, fam))
        try:
            with open(model_path, "rb") as f:
                bundle = pickle.load(f)
                # Normalise keys
                features = bundle.get("feature_cols") or bundle.get("features")
                result = {"model": bundle.get("model"), "scaler": bundle.get("scaler"), "features": features}
                self._family_bundles[fam] = result
                logger.info(f"Loaded model bundle for family '{fam}' from {model_path}")
                return result
        except Exception as e:
            logger.error(f"Failed loading model bundle for family '{fam}': {e}")
            self._family_bundles[fam] = None
            return None

