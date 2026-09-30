"""
NEPSE secondary-market transaction costs for simulated trades.

Every rate lives here so a schedule change is a one-line edit. Values follow
the SEBON/NEPSE schedule for equity trades by individual investors; verify
against the current circular before relying on them for anything but practice.
"""

from dataclasses import asdict, dataclass

# (upper bound of trade value in NPR, commission rate). The whole trade value
# is charged at the rate of the bracket it falls in (not marginally).
BROKER_COMMISSION_TIERS: tuple[tuple[float, float], ...] = (
    (50_000, 0.0036),
    (500_000, 0.0033),
    (2_000_000, 0.0031),
    (10_000_000, 0.0027),
    (float("inf"), 0.0024),
)
MIN_BROKER_COMMISSION = 10.0
SEBON_FEE_RATE = 0.00015
DP_CHARGE_PER_SELL = 25.0
CGT_SHORT_TERM_RATE = 0.075  # held < LONG_TERM_HOLDING_DAYS
CGT_LONG_TERM_RATE = 0.05
LONG_TERM_HOLDING_DAYS = 365


def _money(value: float) -> float:
    return round(value + 0.0, 2)


@dataclass(frozen=True)
class FeeBreakdown:
    side: str
    trade_value: float
    broker_commission: float
    commission_rate: float
    sebon_fee: float
    dp_charge: float
    capital_gains_tax: float
    cgt_rate: float
    realized_gain: float  # before CGT; 0 for buys
    total_fees: float  # commission + SEBON + DP + CGT
    net_amount: float  # cash paid (buy) or received (sell)

    def to_dict(self) -> dict:
        return asdict(self)


def broker_commission(trade_value: float) -> tuple[float, float]:
    """Return (commission, rate) for a trade value."""
    for upper, rate in BROKER_COMMISSION_TIERS:
        if trade_value <= upper:
            return _money(max(trade_value * rate, MIN_BROKER_COMMISSION)), rate
    raise AssertionError("unreachable: last tier is unbounded")


def buy_cost(price: float, qty: int) -> FeeBreakdown:
    value = _money(price * qty)
    commission, rate = broker_commission(value)
    sebon = _money(value * SEBON_FEE_RATE)
    fees = _money(commission + sebon)
    return FeeBreakdown(
        side="buy",
        trade_value=value,
        broker_commission=commission,
        commission_rate=rate,
        sebon_fee=sebon,
        dp_charge=0.0,
        capital_gains_tax=0.0,
        cgt_rate=0.0,
        realized_gain=0.0,
        total_fees=fees,
        net_amount=_money(value + fees),
    )


def sell_proceeds(price: float, qty: int, avg_cost: float, holding_days: int) -> FeeBreakdown:
    """
    Cash received for a sale. avg_cost is the per-share cost basis including
    buy-side fees (NEPSE's WACC), so the taxable gain is net of both sides' fees.
    """
    value = _money(price * qty)
    commission, rate = broker_commission(value)
    sebon = _money(value * SEBON_FEE_RATE)
    dp = DP_CHARGE_PER_SELL
    gain = _money(value - commission - sebon - dp - avg_cost * qty)
    cgt_rate = CGT_LONG_TERM_RATE if holding_days >= LONG_TERM_HOLDING_DAYS else CGT_SHORT_TERM_RATE
    cgt = _money(gain * cgt_rate) if gain > 0 else 0.0
    fees = _money(commission + sebon + dp + cgt)
    return FeeBreakdown(
        side="sell",
        trade_value=value,
        broker_commission=commission,
        commission_rate=rate,
        sebon_fee=sebon,
        dp_charge=dp,
        capital_gains_tax=cgt,
        cgt_rate=cgt_rate if gain > 0 else 0.0,
        realized_gain=gain,
        total_fees=fees,
        net_amount=_money(value - fees),
    )
