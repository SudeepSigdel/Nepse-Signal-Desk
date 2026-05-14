"""
Exit Rules Service: Logic-based position exit management.
Determines when to exit a position based on time, stop-loss, or signal decay.

This complements model-based BUY signals with rule-based EXIT logic.
Most systematic traders use this approach: model tells when to ENTER, rules tell when to EXIT.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ExitSignal:
    """Result of checking if a position should exit."""
    should_exit: bool
    reason: Optional[str] = None
    reason_type: Optional[str] = None  # "time_based", "stop_loss", "signal_decay"
    days_held: int = 0
    exit_return_pct: float = 0.0


class ExitRulesService:
    """
    Manages exit rules for positions.
    
    Implements three exit strategies:
    1. Time-based: Exit after N days (matches model's 10-day lookback horizon)
    2. Stop-loss: Exit if price drops X% from entry
    3. Signal decay: Exit if buy confidence drops below threshold
    
    Usage:
        rules = ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)
        exit_signal = rules.check_exit(
            entry_date=datetime(2025, 5, 1),
            entry_price=100.0,
            current_price=97.0,
            current_buy_conf=0.42
        )
        if exit_signal.should_exit:
            print(f"EXIT: {exit_signal.reason}")
    """
    
    def __init__(
        self, 
        exit_days: int = 10,
        stop_loss_pct: float = 5.0,
        min_buy_conf: float = 0.45,
    ):
        """
        Initialize exit rules.
        
        Args:
            exit_days: Exit after this many days (default 10, matches model horizon)
            stop_loss_pct: Exit if price drops this % from entry (default 5%)
            min_buy_conf: Exit if buy_conf drops below this (default 0.45)
        """
        self.exit_days = exit_days
        self.stop_loss_pct = stop_loss_pct / 100.0  # Convert to decimal (5% → 0.05)
        self.min_buy_conf = min_buy_conf
        
        logger.info(
            f"ExitRulesService initialized: "
            f"exit_days={exit_days}, stop_loss={stop_loss_pct}%, min_buy_conf={min_buy_conf}"
        )
    
    def check_exit(
        self,
        entry_date: datetime,
        entry_price: float,
        current_price: float,
        current_buy_conf: float,
        current_date: Optional[datetime] = None
    ) -> ExitSignal:
        """
        Check if a position should be exited based on all rules.
        
        Args:
            entry_date: When the position was entered
            entry_price: Price when entering
            current_price: Current market price
            current_buy_conf: Current buy confidence (0-1)
            current_date: Today's date (default: now)
        
        Returns:
            ExitSignal with should_exit flag and reason
        """
        if current_date is None:
            current_date = datetime.now()
        
        # ─────────────────────────────────────────────────────────────────
        # Rule 1: TIME-BASED EXIT
        # ─────────────────────────────────────────────────────────────────
        # Model trained on 10-day forward returns. After 10 days, edge disappears.
        # Exit to redeploy capital to new opportunities.
        
        days_held = (current_date - entry_date).days
        
        if days_held >= self.exit_days:
            return ExitSignal(
                should_exit=True,
                reason=f"Held for {days_held} days (exit horizon: {self.exit_days} days)",
                reason_type="time_based",
                days_held=days_held,
                exit_return_pct=self._calculate_return(entry_price, current_price)
            )
        
        # ─────────────────────────────────────────────────────────────────
        # Rule 2: STOP-LOSS EXIT
        # ─────────────────────────────────────────────────────────────────
        # Limit losses. If price drops X% from entry, exit.
        # Example: Entry 100, Stop-loss 5% → Exit if price hits 95.
        
        stop_loss_price = entry_price * (1 - self.stop_loss_pct)
        
        if current_price <= stop_loss_price:
            loss_pct = self._calculate_return(entry_price, current_price)
            return ExitSignal(
                should_exit=True,
                reason=f"Stop-loss triggered: price dropped {abs(loss_pct):.1f}% (limit: {self.stop_loss_pct*100:.0f}%)",
                reason_type="stop_loss",
                days_held=days_held,
                exit_return_pct=loss_pct
            )
        
        # ─────────────────────────────────────────────────────────────────
        # Rule 3: SIGNAL DECAY EXIT
        # ─────────────────────────────────────────────────────────────────
        # Model's BUY confidence has weakened. Edge may be gone.
        # Exit if buy_conf drops below minimum threshold.
        
        if current_buy_conf < self.min_buy_conf:
            return ExitSignal(
                should_exit=True,
                reason=f"Buy signal weakened: confidence {current_buy_conf:.2f} < threshold {self.min_buy_conf:.2f}",
                reason_type="signal_decay",
                days_held=days_held,
                exit_return_pct=self._calculate_return(entry_price, current_price)
            )
        
        # ─────────────────────────────────────────────────────────────────
        # No exit triggered - position should remain open
        # ─────────────────────────────────────────────────────────────────
        
        return ExitSignal(
            should_exit=False,
            days_held=days_held,
            exit_return_pct=self._calculate_return(entry_price, current_price)
        )
    
    def get_exit_status(
        self,
        entry_date: datetime,
        entry_price: float,
        current_price: float,
        current_buy_conf: float,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed exit status without making the exit decision.
        Useful for displaying position status to users.
        
        Returns dict with:
        - days_held: Days position has been open
        - days_remaining: Days until time-based exit (if any)
        - stop_loss_price: Price where stop-loss triggers
        - distance_to_stop_loss: Current distance from stop-loss (%)
        - current_return: Current profit/loss (%)
        - buy_conf: Current confidence score
        - risks: List of active risks
        """
        if current_date is None:
            current_date = datetime.now()
        
        days_held = (current_date - entry_date).days
        days_remaining = max(0, self.exit_days - days_held)
        stop_loss_price = entry_price * (1 - self.stop_loss_pct)
        distance_to_stop = ((current_price - stop_loss_price) / stop_loss_price) * 100
        current_return = self._calculate_return(entry_price, current_price)
        
        risks = []
        if days_held >= self.exit_days * 0.8:
            risks.append(f"⏰ Approaching exit horizon ({days_remaining} days remaining)")
        if current_price < stop_loss_price * 1.02:  # Within 2% of stop
            risks.append(f"⚠️ Close to stop-loss ({distance_to_stop:.1f}% away)")
        if current_buy_conf < self.min_buy_conf:
            risks.append(f"📉 Buy signal weakening (confidence: {current_buy_conf:.2f})")
        
        return {
            "days_held": days_held,
            "days_remaining": days_remaining,
            "exit_horizon_pct": (days_held / self.exit_days) * 100,
            "stop_loss_price": round(stop_loss_price, 2),
            "current_price": round(current_price, 2),
            "distance_to_stop_loss_pct": round(distance_to_stop, 2),
            "current_return_pct": round(current_return, 2),
            "buy_confidence": round(current_buy_conf, 3),
            "min_confidence_threshold": self.min_buy_conf,
            "risks": risks,
            "should_exit_soon": len(risks) > 0
        }
    
    @staticmethod
    def _calculate_return(entry_price: float, current_price: float) -> float:
        """Calculate return percentage from entry to current price."""
        if entry_price == 0:
            return 0.0
        return ((current_price - entry_price) / entry_price) * 100
    
    def get_config(self) -> Dict[str, Any]:
        """Get current exit rules configuration."""
        return {
            "exit_days": self.exit_days,
            "stop_loss_pct": self.stop_loss_pct * 100,
            "min_buy_confidence": self.min_buy_conf,
            "description": (
                f"Exit after {self.exit_days} days, "
                f"or if price drops {self.stop_loss_pct*100:.0f}%, "
                f"or if buy_conf < {self.min_buy_conf}"
            )
        }
