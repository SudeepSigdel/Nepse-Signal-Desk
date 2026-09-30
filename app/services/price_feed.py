"""
Price quotes for paper trading.

During NEPSE hours, quotes come from a NepseAPI-Unofficial server's /LiveMarket
(one snapshot for every symbol, cached briefly so users don't fan out requests).
Outside hours - or if that server is unset/unreachable - quotes fall back to the
latest daily bar from the pipeline's feature parquet, marked source="eod".

Market hours come from the clock (app/trading/rules.py), which doesn't know
public holidays. When the server is configured, its /IsNepseOpen can veto a
clock "open", so a holiday reads as closed; it is only asked during clock
hours and falls back to the clock if unreachable.
"""

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable, Optional

import httpx

from app.logging_config import get_logger
from app.repositories.stock_repository import StockRepository
from app.trading.rules import circuit_band, is_market_open, nepal_now

logger = get_logger(__name__)

LIVE_CACHE_SECONDS = 30.0
STATUS_CACHE_SECONDS = 60.0
LIVE_TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    prev_close: Optional[float]
    day_high: Optional[float]
    day_low: Optional[float]
    as_of: str
    source: str  # live | eod
    # Circuit band for the session an order would trade in: around prev_close while
    # live, around the latest close for EOD quotes (that close is the next session's
    # reference price).
    band_reference: Optional[float] = None
    circuit_low: Optional[float] = None
    circuit_high: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _num(value) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # NaN -> None


def _with_band(quote: Quote, reference: Optional[float]) -> Quote:
    if not reference:
        return quote
    low, high = circuit_band(reference)
    return Quote(**{**quote.to_dict(), "band_reference": reference, "circuit_low": low, "circuit_high": high})


class PriceFeed:
    def __init__(
        self,
        stock_repository: StockRepository,
        nepse_api_url: str = "",
        market_open: Callable[[], bool] = is_market_open,
        http_get: Optional[Callable[[str], list]] = None,
        shared_cache=None,
    ):
        self.stock_repository = stock_repository
        self.nepse_api_url = nepse_api_url.rstrip("/")
        self.market_open = market_open
        self._http_get = http_get or self._default_http_get
        # Optional app.cache.ResponseCache: with Redis behind it, all workers share
        # one /LiveMarket snapshot, so the upstream sees ~1 request per 30 s total.
        self.shared_cache = shared_cache
        self._lock = threading.Lock()
        self._live: dict[str, Quote] = {}
        self._live_fetched_at = 0.0
        self._status: Optional[bool] = None
        self._status_fetched_at = -STATUS_CACHE_SECONDS

    @staticmethod
    def _default_http_get(url: str) -> list:
        response = httpx.get(url, timeout=LIVE_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def _live_snapshot(self) -> dict[str, Quote]:
        with self._lock:
            if time.monotonic() - self._live_fetched_at < LIVE_CACHE_SECONDS:
                return self._live
            # Mark the attempt first so a down server isn't retried on every request.
            self._live_fetched_at = time.monotonic()
            rows = None
            shared = self.shared_cache.get("live-market") if self.shared_cache else None
            if shared is not None:
                rows = json.loads(shared)
            else:
                try:
                    rows = self._http_get(f"{self.nepse_api_url}/LiveMarket")
                except Exception as exc:
                    logger.warning("Live quotes unavailable (%s); using end-of-day prices", exc)
                    self._live = {}
                    return self._live
                if self.shared_cache and isinstance(rows, list):
                    self.shared_cache.set("live-market", json.dumps(rows).encode(), ttl=LIVE_CACHE_SECONDS)

            snapshot = {}
            for row in rows if isinstance(rows, list) else []:
                symbol = str(row.get("symbol", "")).upper()
                price = _num(row.get("lastTradedPrice"))
                if not symbol or not price:
                    continue
                snapshot[symbol] = _with_band(
                    Quote(
                        symbol=symbol,
                        price=price,
                        prev_close=_num(row.get("previousClose")),
                        day_high=_num(row.get("highPrice")),
                        day_low=_num(row.get("lowPrice")),
                        as_of=str(row.get("lastUpdatedDateTime") or nepal_now().isoformat()),
                        source="live",
                    ),
                    _num(row.get("previousClose")),
                )
            self._live = snapshot
            return snapshot

    @staticmethod
    def _parse_status(payload) -> Optional[bool]:
        """NEPSE's market-open payload looks like {"isOpen": "OPEN" | "CLOSE" | ...}."""
        if not isinstance(payload, dict) or "isOpen" not in payload:
            return None
        value = payload["isOpen"]
        if isinstance(value, bool):
            return value
        return str(value).strip().upper() == "OPEN"

    def _exchange_status(self) -> Optional[bool]:
        """The exchange's own open/closed flag, or None when it can't be read."""
        with self._lock:
            if time.monotonic() - self._status_fetched_at < STATUS_CACHE_SECONDS:
                return self._status
            self._status_fetched_at = time.monotonic()
            shared = self.shared_cache.get("nepse-open") if self.shared_cache else None
            if shared is not None:
                self._status = self._parse_status(json.loads(shared))
                return self._status
            try:
                payload = self._http_get(f"{self.nepse_api_url}/IsNepseOpen")
            except Exception as exc:
                logger.warning("Market status unavailable (%s); using the trading calendar", exc)
                self._status = None
                return None
            self._status = self._parse_status(payload)
            if self._status is not None and self.shared_cache:
                self.shared_cache.set("nepse-open", json.dumps(payload).encode(), ttl=STATUS_CACHE_SECONDS)
            return self._status

    def is_open(self) -> bool:
        """Clock-based session hours, vetoed by the exchange's flag (holidays) when available."""
        if not self.market_open():
            return False
        if not self.nepse_api_url:
            return True
        return self._exchange_status() is not False

    def live_quote(self, symbol: str) -> Optional[Quote]:
        if not self.nepse_api_url or not self.is_open():
            return None
        return self._live_snapshot().get(symbol.upper())

    def eod_quote(self, symbol: str) -> Optional[Quote]:
        history = self.stock_repository.get_stock_data(symbol.upper(), days=2)
        if history is None or history.empty:
            return None
        last = history.iloc[-1]
        price = _num(last.get("Close"))
        if not price:
            return None
        prev_close = _num(history.iloc[-2]["Close"]) if len(history) > 1 else None
        as_of = last["Date"]
        return _with_band(
            Quote(
                symbol=symbol.upper(),
                price=price,
                prev_close=prev_close,
                day_high=_num(last.get("High")),
                day_low=_num(last.get("Low")),
                as_of=as_of.date().isoformat() if isinstance(as_of, datetime) else str(as_of)[:10],
                source="eod",
            ),
            price,
        )

    def get_quote(self, symbol: str) -> Optional[Quote]:
        return self.live_quote(symbol) or self.eod_quote(symbol)

    def last_prices(self, symbols) -> dict[str, float]:
        prices = {}
        for symbol in symbols:
            quote = self.get_quote(symbol)
            if quote:
                prices[symbol] = quote.price
        return prices
