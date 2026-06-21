"""
Unit Tests — Fire Suppression (Python Reference Model)
"""

import pytest
from .fb_fire_suppression import FireSuppression, FireState


class TestFireNormal:
    def test_starts_normal(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute()
        assert fs.state == FireState.NORMAL
        assert fs.discharge_command is False

    def test_no_detection_stays_normal(self):
        fs = FireSuppression()
        fs.enable()
        for _ in range(100):
            fs.execute(vesda_level=0, spot_detectors=[False]*8)
        assert fs.state == FireState.NORMAL


class TestFireVESDA:
    def test_vesda_level1_goes_to_alert(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute(vesda_level=1)
        assert fs.state == FireState.ALERT
        assert fs.discharge_command is False

    def test_vesda_level2_goes_to_prealarm(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute(vesda_level=2)
        assert fs.state == FireState.PRE_ALARM

    def test_vesda_level3_goes_to_alarm_then_countdown(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute(vesda_level=3)
        # First scan: NORMAL → ALARM, next scan: ALARM → COUNTDOWN
        assert fs.state == FireState.ALARM
        fs.execute(vesda_level=3)
        assert fs.state == FireState.COUNTDOWN

    def test_vesda_level3_full_countdown_discharges(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute(vesda_level=3)  # → ALARM
        # Run countdown (15000 scans + 1 for ALARM→COUNTDOWN transition)
        for _ in range(15001):
            fs.execute(vesda_level=3)
        assert fs.state == FireState.DISCHARGED
        assert fs.discharge_command is True


class TestFireSpotDetectors:
    def test_two_spots_triggers_alarm(self):
        fs = FireSuppression()
        fs.enable()
        spots = [False] * 8
        spots[0] = True
        spots[3] = True
        fs.execute(vesda_level=0, spot_detectors=spots)
        assert fs.state == FireState.ALARM

    def test_single_spot_is_alert_only(self):
        fs = FireSuppression()
        fs.enable()
        spots = [False] * 8
        spots[5] = True
        fs.execute(vesda_level=0, spot_detectors=spots)
        assert fs.state == FireState.ALERT
        assert fs.discharge_command is False


class TestFireAbort:
    def test_abort_stops_countdown(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute(vesda_level=3)  # → ALARM
        fs.execute(vesda_level=3)  # → COUNTDOWN
        assert fs.state == FireState.COUNTDOWN
        # Run some countdown
        for _ in range(1000):
            fs.execute(vesda_level=3)
        assert fs.state == FireState.COUNTDOWN
        # Press abort
        fs.execute(vesda_level=3, abort_button=True)
        assert fs.state == FireState.ALARM
        assert fs.discharge_command is False

    def test_abort_resets_countdown_timer(self):
        fs = FireSuppression()
        fs.enable()
        fs.execute(vesda_level=3)  # → ALARM
        fs.execute(vesda_level=3)  # → COUNTDOWN
        for _ in range(14000):
            fs.execute(vesda_level=3)
        # Abort near end
        fs.execute(vesda_level=3, abort_button=True)
        # Re-enter countdown and run another 14000 — should NOT discharge
        fs.execute(vesda_level=3)  # ALARM → COUNTDOWN
        for _ in range(14000):
            fs.execute(vesda_level=3)
        assert fs.state == FireState.COUNTDOWN
        assert fs.discharge_command is False


class TestFireSafeState:
    def test_disabled_no_discharge(self):
        fs = FireSuppression()
        fs.disable()
        fs.execute(vesda_level=3, spot_detectors=[True]*8)
        assert fs.discharge_command is False
        assert fs.state == FireState.NORMAL
