"""
Model repository: sole owner of ML artifact discovery/loading (pickle files on disk).

Consolidates naming-convention parsing (model_fold*.pkl, family suffixes, sell suffixes)
that used to be duplicated between data_loader.py and signal_service.py.
"""

import glob
import json
import os
import pickle
import re
from pathlib import Path
from typing import Any, Dict, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


def normalize_model_family(raw_family: Optional[str]) -> str:
    family = (raw_family or "xgboost").strip().lower().replace("-", "_")
    if family in {"rf", "randomforest", "random_forest", "random forest"}:
        return "random_forest"
    return "xgboost"


def _family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


def _buy_pattern(family: str) -> str:
    return f"model_fold*{_family_suffix(family)}.pkl"


def _sell_pattern(family: str) -> str:
    return f"model_fold*{_family_suffix(family)}_sell.pkl"


def _latest_buy_name(family: str) -> str:
    return f"model_latest{_family_suffix(family)}.pkl"


def _latest_sell_name(family: str) -> str:
    return f"model_latest{_family_suffix(family)}_sell.pkl"


def _sort_key(path: str, family: str, sell: bool) -> int:
    basename = os.path.basename(path)
    if basename == (_latest_sell_name(family) if sell else _latest_buy_name(family)):
        return 10**9

    suffix = _family_suffix(family)
    pattern = (
        rf"model_fold(\d+){re.escape(suffix)}_sell\.pkl$"
        if sell
        else rf"model_fold(\d+){re.escape(suffix)}\.pkl$"
    )
    match = re.search(pattern, basename)
    return int(match.group(1)) if match else -1


class ModelRepository:
    """Loads and caches BUY/SELL model bundles (model, scaler, feature_cols) per family."""

    def __init__(self, model_dir: Path, data_processed_dir: Path, default_family: str):
        self.model_dir = model_dir
        self.data_processed_dir = data_processed_dir
        self.default_family = normalize_model_family(default_family)
        self.model_family = self.default_family
        self.config: Dict[str, Any] = {}
        self._buy_bundles: Dict[str, Optional[Dict[str, Any]]] = {}
        self._sell_bundles: Dict[str, Optional[Dict[str, Any]]] = {}

    def load(self) -> None:
        """Load fold config and select the effective model family, falling back if needed."""
        self._load_config()
        self.model_family = self._select_available_family(self.default_family)
        logger.info("ModelRepository: using model family '%s'", self.model_family)

    def _load_config(self) -> None:
        config_path = self.data_processed_dir / "fold_config.json"
        try:
            with open(config_path, encoding="utf-8") as f:
                self.config = json.load(f)
            logger.info("Loaded config from %s", config_path)
        except FileNotFoundError as e:
            logger.warning("fold_config.json not found; using model bundle features when available: %s", e)
            self.config = {}
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in fold_config.json: %s", e)
            self.config = {}

    def _has_buy_model(self, family: str) -> bool:
        suffix = _family_suffix(family)
        candidates = glob.glob(str(self.model_dir / _buy_pattern(family)))
        candidates.extend(glob.glob(str(self.model_dir / _latest_buy_name(family))))
        candidates = [p for p in candidates if "_sell" not in os.path.basename(p)]
        if not suffix:
            candidates = [p for p in candidates if "_rf" not in os.path.basename(p)]
        return bool(candidates)

    def _select_available_family(self, requested_family: str) -> str:
        if self._has_buy_model(requested_family):
            return requested_family
        for candidate in ("random_forest", "xgboost"):
            if candidate != requested_family and self._has_buy_model(candidate):
                logger.warning(
                    "Requested model family '%s' has no BUY model; falling back to '%s'",
                    requested_family,
                    candidate,
                )
                return candidate
        return requested_family

    def is_ready(self) -> bool:
        bundle = self.get_buy_bundle(self.model_family)
        return bool(bundle and bundle.get("model") and bundle.get("scaler") and bundle.get("features"))

    def get_buy_bundle(self, family: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return {'model', 'scaler', 'features'} for the BUY model of a family (cached)."""
        fam = normalize_model_family(family) if family else self.model_family
        if fam in self._buy_bundles:
            return self._buy_bundles[fam]

        suffix = _family_suffix(fam)
        candidates = glob.glob(str(self.model_dir / _buy_pattern(fam)))
        candidates.extend(glob.glob(str(self.model_dir / _latest_buy_name(fam))))
        candidates = [p for p in candidates if "_sell" not in os.path.basename(p)]
        if not suffix:
            candidates = [p for p in candidates if "_rf" not in os.path.basename(p)]

        if not candidates:
            logger.warning("No BUY model files found for family '%s' in %s", fam, self.model_dir)
            self._buy_bundles[fam] = None
            return None

        model_path = max(candidates, key=lambda path: _sort_key(path, fam, sell=False))
        bundle = self._load_bundle(model_path)
        if bundle:
            features = bundle.get("feature_cols") or bundle.get("features") or self.config.get("feature_cols")
            result = {"model": bundle.get("model"), "scaler": bundle.get("scaler"), "features": features}
            logger.info("Loaded BUY model for family '%s' from %s (%d features)",
                        fam, model_path, len(features) if features else 0)
        else:
            result = None
        self._buy_bundles[fam] = result
        return result

    def get_sell_bundle(self, family: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return {'model', 'scaler', 'features'} for the SELL model of a family (cached, optional)."""
        fam = normalize_model_family(family) if family else self.model_family
        if fam in self._sell_bundles:
            return self._sell_bundles[fam]

        suffix = _family_suffix(fam)
        candidates = glob.glob(str(self.model_dir / _sell_pattern(fam)))
        candidates.extend(glob.glob(str(self.model_dir / _latest_sell_name(fam))))
        if not suffix:
            candidates = [p for p in candidates if "_rf" not in os.path.basename(p)]

        if not candidates:
            logger.warning("No SELL model files found for family '%s' (optional)", fam)
            self._sell_bundles[fam] = None
            return None

        model_path = max(candidates, key=lambda path: _sort_key(path, fam, sell=True))
        bundle = self._load_bundle(model_path)
        if bundle:
            features = bundle.get("feature_cols") or bundle.get("features")
            result = {"model": bundle.get("model"), "scaler": bundle.get("scaler"), "features": features}
            logger.info("Loaded SELL model for family '%s' from %s", fam, model_path)
        else:
            result = None
        self._sell_bundles[fam] = result
        return result

    @staticmethod
    def _load_bundle(path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error("Failed loading model bundle from %s: %s", path, e)
            return None
