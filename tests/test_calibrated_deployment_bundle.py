"""Regression tests for compact, calibrator-only deployment bundles."""

import numpy as np
import pandas as pd

from app.services.signal_service import SignalService


class IdentityScaler:
    def transform(self, values):
        return values


class FixedCalibrator:
    def predict_proba(self, values):
        assert values.shape == (1, 1)
        return np.array([[0.25, 0.75]])


class StockRows:
    def get_latest_row(self, symbol, required_columns=None):
        assert symbol == "NABIL"
        assert required_columns == ["feature"]
        return pd.Series({"feature": 1.0})


def test_predict_accepts_calibrator_without_duplicate_raw_model():
    service = SignalService(model_repository=object(), stock_repository=StockRows())
    bundle = {
        "model": None,
        "calibrator": FixedCalibrator(),
        "scaler": IdentityScaler(),
        "features": ["feature"],
    }

    assert service._predict("NABIL", bundle, "random_forest", "BUY") == 0.75
