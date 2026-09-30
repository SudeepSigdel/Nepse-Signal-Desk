"""Tests for the performance layer: response cache, batch scoring, indexed lookups."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.cache import ResponseCache, cached_json_response
from app.repositories.stock_repository import StockRepository
from app.services.signal_service import SignalService


# ─── Response cache ────────────────────────────────────────


class FakeRedis:
    def __init__(self):
        self.store, self.fail = {}, False

    def _check(self):
        if self.fail:
            raise ConnectionError("redis down")

    def get(self, key):
        self._check()
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self._check()
        self.store[key] = value

    def ttl(self, key):
        return 100


def test_local_cache_builds_once_and_evicts_lru():
    cache = ResponseCache(local_max_entries=2)
    calls = []
    build = lambda: calls.append(1) or b"x"  # noqa: E731
    assert cache.get_or_build("a", build) == b"x"
    assert cache.get_or_build("a", build) == b"x"
    assert len(calls) == 1 and (cache.hits, cache.misses) == (1, 1)

    cache.set("b", b"b")
    cache.set("c", b"c")  # evicts "a", the least recently used
    assert cache.get("a") is None and cache.get("c") == b"c"


def test_expired_entries_are_rebuilt(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr("app.cache.time.monotonic", lambda: clock["t"])
    cache = ResponseCache()
    cache.set("k", b"old", ttl=10)
    clock["t"] = 11
    assert cache.get("k") is None


def test_redis_shares_entries_between_instances():
    redis = FakeRedis()
    worker_a, worker_b = ResponseCache(redis_client=redis), ResponseCache(redis_client=redis)
    worker_a.set("stocks", b"payload")
    assert worker_b.get("stocks") == b"payload"  # another worker / after restart


def test_redis_outage_fails_open_to_memory():
    redis = FakeRedis()
    cache = ResponseCache(redis_client=redis)
    redis.fail = True
    assert cache.get_or_build("k", lambda: b"v") == b"v"  # no exception
    assert cache.redis is None  # backing off
    assert cache.get("k") == b"v"  # served from memory


def test_cached_json_response_etag_and_304():
    app = FastAPI()
    cache = ResponseCache()
    builds = []

    @app.get("/thing")
    def thing(request: Request):
        return cached_json_response(request, cache, "thing", lambda: builds.append(1) or b'{"a":1}')

    client = TestClient(app)
    first = client.get("/thing")
    assert first.status_code == 200 and first.json() == {"a": 1}
    etag = first.headers["etag"]
    assert "max-age" in first.headers["cache-control"]

    again = client.get("/thing", headers={"If-None-Match": etag})
    assert again.status_code == 304 and again.content == b""
    assert len(builds) == 1


# ─── Indexed repository + batch scoring ────────────────────


def _repo():
    rng = np.random.default_rng(0)
    rows = []
    for sym in ["CCC", "AAA", "BBB"]:  # deliberately unsorted
        for day in pd.date_range("2026-01-01", periods=5)[::-1]:  # and newest-first
            rows.append({"Symbol": sym, "Date": day, "Close": float(rng.integers(100, 200)),
                         "f1": float(rng.random()), "f2": float(rng.random())})
    df = pd.DataFrame(rows)
    df.loc[(df["Symbol"] == "BBB") & (df["Date"] == "2026-01-05"), "f2"] = np.nan
    repo = StockRepository(Path("unused.parquet"))
    repo.load_frame(df)
    return repo


def test_indexed_lookups_match_a_full_scan():
    repo = _repo()
    df = repo.features_df.copy()
    for sym in ["AAA", "BBB", "CCC"]:
        expected = df[df["Symbol"] == sym].sort_values("Date")
        got = repo.get_stock_data(sym, days=3)
        assert list(got["Date"]) == list(expected["Date"].tail(3))
        assert repo.get_latest_row(sym)["Date"] == expected["Date"].max()
    # BBB's newest row lacks f2 -> the latest *complete* row is a day earlier.
    assert repo.get_latest_row("BBB", ["f1", "f2"])["Date"] == pd.Timestamp("2026-01-04")
    assert repo.get_latest_row("ZZZ") is None
    assert repo.all_symbols == ["AAA", "BBB", "CCC"]


class ScaleBy2:
    def transform(self, X):
        return np.asarray(X) * 2


class SumModel:
    """predict_proba depends on each row, so batching bugs would show."""

    def __init__(self):
        self.calls = []

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        self.calls.append(len(X))
        p = 1 / (1 + np.exp(-X.sum(axis=1)))
        return np.column_stack([1 - p, p])


class Models:
    def __init__(self, bundle):
        self.bundle = bundle

    def get_buy_bundle(self, family=None):
        return self.bundle

    def get_sell_bundle(self, family=None):
        return self.bundle

    def get_relative_bundle(self):
        return None


def test_batch_scores_equal_single_row_scores():
    repo = _repo()
    model = SumModel()
    bundle = {"model": model, "calibrator": None, "scaler": ScaleBy2(), "features": ["f1", "f2"]}

    single = SignalService(Models(bundle), repo)
    expected = {s: single._predict(s, bundle, None, "BUY") for s in repo.all_symbols}

    batched = SignalService(Models(bundle), repo)
    model.calls.clear()
    got = {s: batched.compute_confidence(s) for s in repo.all_symbols}

    assert all(v is not None for v in expected.values())
    assert got == pytest.approx(expected)
    assert model.calls == [3]  # one predict_proba call for every symbol
