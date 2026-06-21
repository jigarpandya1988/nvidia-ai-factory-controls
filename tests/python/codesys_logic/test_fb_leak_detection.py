"""
Unit Tests — Leak Detection (Python Reference Model)
"""

import pytest
from .fb_leak_detection import LeakDetection, LeakSeverity


class TestLeakSingleZone:
    def test_single_zone_after_debounce_is_minor(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [False] * 16
        inputs[3] = True  # Zone 3 leak
        # Run past debounce (250 scans)
        for _ in range(260):
            ld.execute(inputs)
        assert ld.severity == LeakSeverity.MINOR
        assert ld.active_zone_count == 1
        assert ld.trip_request is False
        assert ld.zone_status[3] is True

    def test_zone_clears_when_input_clears(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [False] * 16
        inputs[0] = True
        for _ in range(260):
            ld.execute(inputs)
        assert ld.zone_status[0] is True
        # Clear the input
        inputs[0] = False
        ld.execute(inputs)
        assert ld.zone_status[0] is False
        assert ld.severity == LeakSeverity.NONE


class TestLeakMultipleZones:
    def test_two_zones_is_major_with_trip(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [False] * 16
        inputs[1] = True
        inputs[5] = True
        for _ in range(260):
            ld.execute(inputs)
        assert ld.severity == LeakSeverity.MAJOR
        assert ld.active_zone_count == 2
        assert ld.trip_request is True

    def test_many_zones_still_major(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [True] * 16
        for _ in range(260):
            ld.execute(inputs)
        assert ld.severity == LeakSeverity.MAJOR
        assert ld.active_zone_count == 16
        assert ld.trip_request is True


class TestLeakDebounce:
    def test_short_pulse_rejected(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [False] * 16
        inputs[7] = True
        # Only 100 scans (< 250 debounce)
        for _ in range(100):
            ld.execute(inputs)
        assert ld.zone_status[7] is False
        assert ld.severity == LeakSeverity.NONE

    def test_exactly_at_debounce_threshold(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [False] * 16
        inputs[2] = True
        # Run exactly 250 scans
        for _ in range(250):
            ld.execute(inputs)
        assert ld.zone_status[2] is True


class TestLeakSafeState:
    def test_disabled_no_trip(self):
        ld = LeakDetection()
        ld.disable()
        inputs = [True] * 16
        ld.execute(inputs)
        assert ld.trip_request is False
        assert ld.severity == LeakSeverity.NONE
        assert ld.active_zone_count == 0

    def test_disable_clears_active_zones(self):
        ld = LeakDetection()
        ld.enable()
        inputs = [True] * 16
        for _ in range(260):
            ld.execute(inputs)
        assert ld.trip_request is True
        ld.disable()
        assert ld.trip_request is False
        assert ld.active_zone_count == 0
