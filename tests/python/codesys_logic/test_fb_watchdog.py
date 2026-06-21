"""
Unit Tests — Watchdog (Python Reference Model)
"""

import pytest
from .fb_watchdog import Watchdog


class TestWatchdogAlive:
    def test_changing_counter_stays_alive(self):
        wd = Watchdog(timeout_ms=100, cycle_time_ms=5)
        wd.enable()
        for i in range(20):
            wd.execute(heartbeat_counter=i)
        assert wd.alive is True
        assert wd.timed_out is False

    def test_first_scan_is_alive(self):
        wd = Watchdog(timeout_ms=50, cycle_time_ms=5)
        wd.enable()
        wd.execute(heartbeat_counter=0)
        assert wd.alive is True

    def test_counter_increment_any_amount(self):
        wd = Watchdog(timeout_ms=100, cycle_time_ms=5)
        wd.enable()
        wd.execute(heartbeat_counter=100)
        wd.execute(heartbeat_counter=500)
        wd.execute(heartbeat_counter=501)
        assert wd.alive is True


class TestWatchdogTimeout:
    def test_frozen_counter_times_out(self):
        wd = Watchdog(timeout_ms=100, cycle_time_ms=5)
        wd.enable()
        wd.execute(heartbeat_counter=42)  # First scan
        # Freeze counter for timeout period (100ms / 5ms = 20 scans)
        for _ in range(25):
            wd.execute(heartbeat_counter=42)
        assert wd.timed_out is True
        assert wd.alive is False

    def test_timeout_at_exact_boundary(self):
        wd = Watchdog(timeout_ms=50, cycle_time_ms=5)  # 10 scans
        wd.enable()
        wd.execute(heartbeat_counter=10)  # First scan
        for _ in range(9):
            wd.execute(heartbeat_counter=10)
        assert wd.timed_out is False  # Not yet
        wd.execute(heartbeat_counter=10)  # 10th frozen scan
        assert wd.timed_out is True

    def test_recovery_after_timeout(self):
        wd = Watchdog(timeout_ms=50, cycle_time_ms=5)
        wd.enable()
        wd.execute(heartbeat_counter=5)
        for _ in range(15):
            wd.execute(heartbeat_counter=5)  # Times out
        assert wd.timed_out is True
        # Counter starts changing again
        wd.execute(heartbeat_counter=6)
        assert wd.alive is True
        assert wd.timed_out is False


class TestWatchdogDisabled:
    def test_disabled_not_alive_not_timed_out(self):
        wd = Watchdog(timeout_ms=50, cycle_time_ms=5)
        wd.disable()
        wd.execute(heartbeat_counter=0)
        assert wd.alive is False
        assert wd.timed_out is False

    def test_elapsed_resets_on_counter_change(self):
        wd = Watchdog(timeout_ms=100, cycle_time_ms=5)
        wd.enable()
        wd.execute(heartbeat_counter=1)
        for _ in range(5):
            wd.execute(heartbeat_counter=1)
        assert wd.elapsed_ms == 25
        wd.execute(heartbeat_counter=2)
        assert wd.elapsed_ms == 0
