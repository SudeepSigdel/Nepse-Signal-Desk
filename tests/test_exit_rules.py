"""
Tests for exit rules service and API integration.
"""

import pytest
from datetime import datetime, timedelta
from app.services.exit_rules import ExitRulesService


@pytest.fixture
def exit_rules():
    """Create ExitRulesService with default config."""
    return ExitRulesService(
        exit_days=10,
        stop_loss_pct=5.0,
        min_buy_conf=0.45
    )


class TestExitRulesService:
    """Test ExitRulesService logic."""

    def test_time_based_exit_at_10_days(self, exit_rules):
        """Exit trigger: Time-based, exactly 10 days."""
        entry = datetime.now() - timedelta(days=10)
        signal = exit_rules.check_exit(
            entry_date=entry,
            entry_price=100.0,
            current_price=100.0,
            current_buy_conf=0.7
        )
        assert signal.should_exit == True
        assert signal.reason_type == "time_based"
        assert signal.days_held == 10

    def test_time_based_exit_beyond_10_days(self, exit_rules):
        """Exit trigger: Time-based, beyond 10 days."""
        entry = datetime.now() - timedelta(days=15)
        signal = exit_rules.check_exit(
            entry_date=entry,
            entry_price=100.0,
            current_price=100.0,
            current_buy_conf=0.7
        )
        assert signal.should_exit == True
        assert signal.reason_type == "time_based"

    def test_time_based_no_exit_before_10_days(self, exit_rules):
        """No exit if time-based not triggered."""
        entry = datetime.now() - timedelta(days=5)
        signal = exit_rules.check_exit(
            entry_date=entry,
            entry_price=100.0,
            current_price=100.0,
            current_buy_conf=0.7
        )
        assert signal.should_exit == False
        assert signal.days_held == 5

    def test_stop_loss_exit_at_5_percent(self, exit_rules):
        """Exit trigger: Stop-loss, exactly 5% loss."""
        signal = exit_rules.check_exit(
            entry_date=datetime.now(),
            entry_price=100.0,
            current_price=95.0,  # Exactly 5% down
            current_buy_conf=0.7
        )
        assert signal.should_exit == True
        assert signal.reason_type == "stop_loss"
        assert signal.exit_return_pct == -5.0

    def test_stop_loss_no_exit_before_5_percent(self, exit_rules):
        """No exit if stop-loss not triggered."""
        signal = exit_rules.check_exit(
            entry_date=datetime.now(),
            entry_price=100.0,
            current_price=96.0,  # 4% down
            current_buy_conf=0.7
        )
        assert signal.should_exit == False

    def test_signal_decay_exit_at_threshold(self, exit_rules):
        """Exit trigger: Signal decay, confidence at 0.45."""
        signal = exit_rules.check_exit(
            entry_date=datetime.now(),
            entry_price=100.0,
            current_price=100.0,
            current_buy_conf=0.45
        )
        assert signal.should_exit == True
        assert signal.reason_type == "signal_decay"

    def test_signal_decay_no_exit_above_threshold(self, exit_rules):
        """No exit if confidence above threshold."""
        signal = exit_rules.check_exit(
            entry_date=datetime.now(),
            entry_price=100.0,
            current_price=100.0,
            current_buy_conf=0.50
        )
        assert signal.should_exit == False

    def test_no_exit_all_conditions_good(self, exit_rules):
        """No exit if all conditions are good."""
        entry = datetime.now() - timedelta(days=5)
        signal = exit_rules.check_exit(
            entry_date=entry,
            entry_price=100.0,
            current_price=105.0,  # Up 5%
            current_buy_conf=0.70  # Strong confidence
        )
        assert signal.should_exit == False
        assert signal.days_held == 5

    def test_exit_status_structure(self, exit_rules):
        """Verify get_exit_status returns correct structure."""
        entry = datetime.now() - timedelta(days=5)
        status = exit_rules.get_exit_status(
            entry_date=entry,
            entry_price=100.0,
            current_price=103.0,
            current_buy_conf=0.68
        )
        
        assert 'days_held' in status
        assert 'days_remaining' in status
        assert 'current_return_pct' in status
        assert 'distance_to_stop_loss_pct' in status
        assert 'risks' in status

    def test_exit_status_days_calculation(self, exit_rules):
        """Verify days held and remaining calculated correctly."""
        entry = datetime.now() - timedelta(days=3)
        status = exit_rules.get_exit_status(
            entry_date=entry,
            entry_price=100.0,
            current_price=100.0,
            current_buy_conf=0.70
        )
        
        assert status['days_held'] == 3
        assert status['days_remaining'] == 7  # 10 - 3

    def test_multiple_triggers_priority(self, exit_rules):
        """When multiple triggers fire, time-based takes priority."""
        # All three would trigger
        entry = datetime.now() - timedelta(days=10)
        signal = exit_rules.check_exit(
            entry_date=entry,
            entry_price=100.0,
            current_price=94.0,  # Also triggers stop-loss
            current_buy_conf=0.40  # Also triggers signal decay
        )
        
        # Time-based should be the priority
        assert signal.reason_type == "time_based"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
