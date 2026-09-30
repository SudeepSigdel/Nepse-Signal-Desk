"""
Paper trading: persists the pure engine (app/trading) to the database.

Fill model (hybrid):
- NEPSE open and a live quote available -> market orders (and marketable limits)
  fill immediately at the last traded price.
- Otherwise the order rests as "pending" and is settled by settle_pending() after
  the daily pipeline, against that session's close / high-low range. Orders
  placed after a session's close wait for the next session, so nobody trades on
  a price they've already seen.

Pending buys reserve cash (and pending sells reserve shares) so a user can't
commit the same money twice.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.db_models import PaperAccount, PaperEquitySnapshot, PaperOrder, PaperPosition, User
from app.services.price_feed import PriceFeed, Quote
from app.trading.engine import Portfolio, Position, TradeError, apply_buy, apply_sell, limit_fill_price, mark_to_market
from app.trading.fees import buy_cost
from app.trading.rules import MARKET_CLOSE, NEPAL_TZ, is_market_open, nepal_now, validate_order

DEFAULT_STARTING_CASH = 1_000_000.0
MAX_STARTING_CASH = 100_000_000.0
MAX_ACCOUNTS_PER_USER = 5


@dataclass(frozen=True)
class Bar:
    close: float
    high: Optional[float] = None
    low: Optional[float] = None


def as_utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for timezone=True columns.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def session_close(trade_date: date) -> datetime:
    return datetime.combine(trade_date, MARKET_CLOSE, tzinfo=NEPAL_TZ)


def _fees_total(order: PaperOrder) -> float:
    if not order.fees_json:
        return 0.0
    return float(json.loads(order.fees_json).get("total_fees", 0.0))


class PaperTradingService:
    def __init__(
        self,
        price_feed: PriceFeed,
        clock: Callable[[], datetime] = nepal_now,
        market_open: Callable[[datetime], bool] = is_market_open,
        is_liquid: Optional[Callable[[str], bool]] = None,
    ):
        self.price_feed = price_feed
        self.clock = clock
        self.market_open = market_open
        # Which stocks count as "the market" for benchmarks (SignalService.is_liquid_enough in the app).
        self.is_liquid = is_liquid or (lambda symbol: True)

    # ─── Accounts ────────────────────────────────────────────

    def list_accounts(self, db: Session, user: User) -> list[PaperAccount]:
        return db.query(PaperAccount).filter(PaperAccount.user_id == user.id).order_by(PaperAccount.id).all()

    def create_account(self, db: Session, user: User, name: str, starting_cash: float) -> PaperAccount:
        if len(self.list_accounts(db, user)) >= MAX_ACCOUNTS_PER_USER:
            raise ValueError(f"You can have at most {MAX_ACCOUNTS_PER_USER} paper accounts.")
        if not 0 < starting_cash <= MAX_STARTING_CASH:
            raise ValueError(f"Starting cash must be between Rs 1 and Rs {MAX_STARTING_CASH:,.0f}.")
        account = PaperAccount(
            user_id=user.id, name=name.strip() or "Paper account", starting_cash=starting_cash, cash=starting_cash
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def get_account(self, db: Session, user: User, account_id: int, lock: bool = False) -> Optional[PaperAccount]:
        query = db.query(PaperAccount).filter(PaperAccount.id == account_id, PaperAccount.user_id == user.id)
        if lock:
            query = query.with_for_update()
        return query.first()

    def reset_account(self, db: Session, account: PaperAccount) -> PaperAccount:
        for collection in (account.positions, account.orders, account.snapshots):
            for row in list(collection):
                db.delete(row)
        account.cash = account.starting_cash
        db.commit()
        db.refresh(account)
        return account

    # ─── Portfolio <-> rows ──────────────────────────────────

    @staticmethod
    def _portfolio(account: PaperAccount) -> Portfolio:
        return Portfolio(
            cash=account.cash,
            positions={
                p.symbol: Position(p.symbol, p.qty, p.avg_cost, p.first_buy_date) for p in account.positions
            },
        )

    @staticmethod
    def _save_portfolio(db: Session, account: PaperAccount, portfolio: Portfolio) -> None:
        account.cash = portfolio.cash
        rows = {p.symbol: p for p in account.positions}
        for symbol, row in rows.items():
            if symbol not in portfolio.positions:
                account.positions.remove(row)
                db.delete(row)
        for symbol, position in portfolio.positions.items():
            row = rows.get(symbol)
            if row is None:
                account.positions.append(
                    PaperPosition(
                        symbol=symbol, qty=position.qty, avg_cost=position.avg_cost,
                        first_buy_date=position.first_buy_date,
                    )
                )
            else:
                row.qty, row.avg_cost, row.first_buy_date = position.qty, position.avg_cost, position.first_buy_date

    @staticmethod
    def _pending(account: PaperAccount) -> list[PaperOrder]:
        return [o for o in account.orders if o.status == "pending"]

    def available_cash(self, account: PaperAccount) -> float:
        return round(account.cash - sum(o.reserved_cash for o in self._pending(account)), 2)

    def available_shares(self, account: PaperAccount, symbol: str) -> int:
        held = next((p.qty for p in account.positions if p.symbol == symbol), 0)
        committed = sum(o.qty for o in self._pending(account) if o.side == "sell" and o.symbol == symbol)
        return held - committed

    # ─── Orders ──────────────────────────────────────────────

    def _fill(self, db: Session, account: PaperAccount, order: PaperOrder, price: float, source: str,
              when: datetime) -> None:
        portfolio = self._portfolio(account)
        trade_day = when.astimezone(NEPAL_TZ).date()
        order.reserved_cash = 0.0
        try:
            if order.side == "buy":
                fill = apply_buy(portfolio, order.symbol, order.qty, price, trade_day)
            else:
                fill = apply_sell(portfolio, order.symbol, order.qty, price, trade_day)
        except TradeError as exc:
            order.status, order.reject_reason = "rejected", str(exc)
            return
        self._save_portfolio(db, account, portfolio)
        order.status = "filled"
        order.fill_price = price
        order.price_source = source
        order.filled_at = when.astimezone(timezone.utc)
        order.fees_json = json.dumps(fill.fees.to_dict())
        order.realized_pnl = fill.realized_pnl if order.side == "sell" else None

    def place_order(
        self,
        db: Session,
        account: PaperAccount,
        symbol: str,
        side: str,
        order_type: str,
        qty: int,
        limit_price: Optional[float] = None,
        note: Optional[str] = None,
    ) -> PaperOrder:
        now = self.clock()
        symbol = symbol.strip().upper()
        # Measured before the new order joins account.orders, so it doesn't count against itself.
        available_cash = self.available_cash(account)
        available_shares = self.available_shares(account, symbol)
        order = PaperOrder(
            account_id=account.id, symbol=symbol, side=side, order_type=order_type, qty=qty,
            limit_price=limit_price if order_type == "limit" else None, status="pending", reserved_cash=0.0,
            created_at=now.astimezone(timezone.utc), note=note,
        )
        account.orders.append(order)

        quote: Optional[Quote] = self.price_feed.get_quote(symbol)
        live = quote is not None and quote.source == "live" and self.market_open(now)
        fill_now_price = None
        if live:
            if order_type == "market":
                fill_now_price = quote.price
            elif limit_price is not None and (
                (side == "buy" and quote.price <= limit_price) or (side == "sell" and quote.price >= limit_price)
            ):
                fill_now_price = quote.price  # marketable limit fills at the better, live price

        if quote is None:
            order.status, order.reject_reason = "rejected", f"No price data for {symbol}; is it a listed stock?"
            db.commit()
            return order

        # Worst-case buy price for the cash check / reservation.
        if fill_now_price is not None:
            est_price = fill_now_price
        elif order_type == "limit":
            est_price = limit_price or 0.0
        else:
            est_price = quote.circuit_high or quote.price
        est_total = buy_cost(est_price, qty).net_amount if side == "buy" and est_price > 0 and qty > 0 else 0.0

        check = validate_order(
            side=side, order_type=order_type, qty=qty, limit_price=limit_price,
            prev_close=quote.band_reference, held_qty=available_shares,
            available_cash=available_cash, estimated_buy_total=est_total,
        )
        if not check.ok:
            order.status, order.reject_reason = "rejected", check.reason
        elif fill_now_price is not None:
            self._fill(db, account, order, fill_now_price, "live", now)
        else:
            order.reserved_cash = est_total if side == "buy" else 0.0
        db.commit()
        db.refresh(order)
        return order

    def cancel_order(self, db: Session, order: PaperOrder) -> PaperOrder:
        if order.status != "pending":
            raise ValueError(f"Only pending orders can be cancelled (this one is {order.status}).")
        order.status, order.reserved_cash = "cancelled", 0.0
        db.commit()
        db.refresh(order)
        return order

    def get_order(self, db: Session, user: User, order_id: int) -> Optional[PaperOrder]:
        return (
            db.query(PaperOrder)
            .join(PaperAccount)
            .filter(PaperOrder.id == order_id, PaperAccount.user_id == user.id)
            .first()
        )

    # ─── Daily settlement ───────────────────────────────────

    def settle_pending(self, db: Session, trade_date: date, bars: dict[str, Bar]) -> dict[str, int]:
        """
        Settle orders placed before trade_date's close against that day's bars,
        then snapshot every account's equity. Safe to run more than once per date.
        """
        cutoff = session_close(trade_date)
        stats = {"filled": 0, "expired": 0, "rejected": 0, "waiting": 0, "snapshots": 0}
        pending = (
            db.query(PaperOrder).filter(PaperOrder.status == "pending").order_by(PaperOrder.created_at).all()
        )
        for order in pending:
            if as_utc(order.created_at) >= cutoff:
                stats["waiting"] += 1
                continue
            account = order.account
            bar = bars.get(order.symbol)
            if bar is None:
                order.status, order.reserved_cash = "expired", 0.0
                order.reject_reason = f"{order.symbol} did not trade on {trade_date.isoformat()}."
                stats["expired"] += 1
                continue
            if order.order_type == "market":
                price = bar.close
            else:
                price = limit_fill_price(order.side, order.limit_price, bar.low, bar.high, bar.close)
            if price is None:
                order.status, order.reserved_cash = "expired", 0.0
                order.reject_reason = f"Limit {order.limit_price:.2f} not reached on {trade_date.isoformat()}."
                stats["expired"] += 1
                continue
            self._fill(db, account, order, price, "eod", cutoff)
            stats["filled" if order.status == "filled" else "rejected"] += 1
        db.flush()

        for account in db.query(PaperAccount).all():
            prices = {p.symbol: bars[p.symbol].close for p in account.positions if p.symbol in bars}
            missing = [p.symbol for p in account.positions if p.symbol not in bars]
            prices.update(self.price_feed.last_prices(missing))
            equity, _ = mark_to_market(self._portfolio(account), prices)
            snapshot = (
                db.query(PaperEquitySnapshot)
                .filter(PaperEquitySnapshot.account_id == account.id, PaperEquitySnapshot.date == trade_date)
                .first()
            )
            if snapshot is None:
                snapshot = PaperEquitySnapshot(account_id=account.id, date=trade_date, cash=0.0, equity=0.0)
                db.add(snapshot)
            snapshot.cash, snapshot.equity = account.cash, equity
            stats["snapshots"] += 1
        db.commit()
        return stats

    # ─── Read models ─────────────────────────────────────────

    def account_summary(self, account: PaperAccount) -> dict:
        portfolio = self._portfolio(account)
        quotes = {symbol: self.price_feed.get_quote(symbol) for symbol in portfolio.positions}
        prices = {symbol: q.price for symbol, q in quotes.items() if q}
        equity, unrealized = mark_to_market(portfolio, prices)
        filled = [o for o in account.orders if o.status == "filled"]
        positions = []
        for p in sorted(account.positions, key=lambda row: row.symbol):
            quote = quotes.get(p.symbol)
            price = quote.price if quote else None
            value = p.qty * price if price is not None else None
            positions.append(
                {
                    "symbol": p.symbol,
                    "qty": p.qty,
                    "avg_cost": round(p.avg_cost, 2),
                    "last_price": price,
                    "price_source": quote.source if quote else None,
                    "market_value": round(value, 2) if value is not None else None,
                    "unrealized_pnl": round(value - p.qty * p.avg_cost, 2) if value is not None else None,
                    "unrealized_pct": round((price / p.avg_cost - 1) * 100, 2) if price and p.avg_cost else None,
                    "first_buy_date": p.first_buy_date.isoformat(),
                }
            )
        return {
            "id": account.id,
            "name": account.name,
            "is_agent": account.is_agent,
            "starting_cash": account.starting_cash,
            "cash": round(account.cash, 2),
            "available_cash": self.available_cash(account),
            "equity": equity,
            "unrealized_pnl": unrealized,
            "realized_pnl": round(sum(o.realized_pnl or 0.0 for o in filled), 2),
            "fees_paid": round(sum(_fees_total(o) for o in filled), 2),
            "return_pct": round((equity / account.starting_cash - 1) * 100, 2) if account.starting_cash else 0.0,
            "positions": positions,
            "created_at": as_utc(account.created_at).isoformat(),
        }

    def market_benchmark(self, account: PaperAccount) -> dict:
        """
        Equal-weight return of liquid NEPSE stocks since the account opened:
        "what if you had simply bought the whole market on day one?" (no fees).
        """
        repo = self.price_feed.stock_repository
        opened = as_utc(account.created_at).astimezone(NEPAL_TZ).date()
        changes, starts, ends = [], [], []
        for symbol in repo.all_symbols:
            if not self.is_liquid(symbol):
                continue
            window = repo.close_change_since(symbol, opened)
            if window is None:
                continue
            first_date, first_close, last_close = window
            changes.append(last_close / first_close - 1)
            starts.append(first_date)
        latest = None
        if repo.features_df is not None and len(repo.features_df):
            latest = repo.features_df["Date"].max()
        return {
            "account_id": account.id,
            "opened": opened.isoformat(),
            "start_date": min(starts).date().isoformat() if starts else None,
            "end_date": latest.date().isoformat() if latest is not None else None,
            "market_return_pct": round(sum(changes) / len(changes) * 100, 2) if changes else 0.0,
            "stocks": len(changes),
        }

    def equity_history(self, db: Session, account: PaperAccount) -> list[PaperEquitySnapshot]:
        return (
            db.query(PaperEquitySnapshot)
            .filter(PaperEquitySnapshot.account_id == account.id)
            .order_by(PaperEquitySnapshot.date)
            .all()
        )

    def leaderboard(self, db: Session, limit: int = 20) -> list[dict]:
        rows = []
        for account in db.query(PaperAccount).all():
            summary = self.account_summary(account)
            email = account.user.email if account.user else ""
            local, _, domain = email.partition("@")
            rows.append(
                {
                    "account_id": account.id,
                    "account_name": account.name,
                    "trader": f"{local[:2]}***@{domain}" if domain else "anonymous",
                    "is_agent": account.is_agent,
                    "equity": summary["equity"],
                    "return_pct": summary["return_pct"],
                    "trades": sum(1 for o in account.orders if o.status == "filled"),
                }
            )
        rows.sort(key=lambda r: r["return_pct"], reverse=True)
        return rows[:limit]
