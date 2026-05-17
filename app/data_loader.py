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
        self.model_family = _normalize_model_family(settings.model_family)
        
        self._load_all()
        self._initialized = True
    
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
            logger.error(f"fold_config.json not found: {e}")
            self.config = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in fold_config.json: {e}")
            self.config = {}
    
    def _load_models(self):
        """Load both BUY and SELL models from model_fold*.pkl and model_fold*_sell.pkl files."""
        suffix = _family_suffix(self.model_family)

        # Load BUY model (latest fold for the selected family)
        buy_pattern = f"model_fold*{suffix}.pkl"
        buy_candidates = glob.glob(str(settings.model_dir / buy_pattern))
        buy_candidates = [
            p for p in buy_candidates
            if "_sell" not in os.path.basename(p)
            and (suffix or "_rf" not in os.path.basename(p))
        ]
        
        if buy_candidates:
            def fold_num(path):
                m = re.search(rf"model_fold(\d+){re.escape(suffix)}\.pkl$", os.path.basename(path))
                return int(m.group(1)) if m else -1
            
            model_path = max(buy_candidates, key=fold_num)
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
        if not suffix:
            sell_candidates = [p for p in sell_candidates if "_rf" not in os.path.basename(p)]
        
        if sell_candidates:
            def fold_num_sell(path):
                m = re.search(rf"model_fold(\d+){re.escape(suffix)}_sell\.pkl$", os.path.basename(path))
                return int(m.group(1)) if m else -1
            
            model_path = max(sell_candidates, key=fold_num_sell)
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

