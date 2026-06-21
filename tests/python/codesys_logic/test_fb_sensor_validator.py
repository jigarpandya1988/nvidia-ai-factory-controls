"""
Unit Tests — Sensor Validator (Python Reference Model)
"""

import pytest
from .fb_sensor_validator import SensorValidator


class TestSensorRange:
    def test_valid_input_passes(self):
        sv = SensorValidator(range_low=0, range_high=100, cycle_time_s=0.005)
        sv.enable()
        for _ in range(5):
            sv.execute(35.0)
        assert sv.valid is True
        assert abs(sv.value - 35.0) < 2.0

    def test_out_of_range_detected(self):
        sv = SensorValidator(range_low=0, range_high=100, cycle_time_s=0.005, max_fault_count=3)
        sv.enable()
        for _ in range(10):
            sv.execute(150.0)  # Above range
        assert sv.alm_out_of_range is True

    def test_below_range_detected(self):
        sv = SensorValidator(range_low=0, range_high=100, cycle_time_s=0.005, max_fault_count=3)
        sv.enable()
        for _ in range(10):
            sv.execute(-20.0)
        assert sv.alm_out_of_range is True


class TestSensorRateOfChange:
    def test_spike_rejected(self):
        sv = SensorValidator(range_low=0, range_high=100, max_rate_of_change=10.0, cycle_time_s=0.1)
        sv.enable()
        sv.execute(30.0)  # Init
        for _ in range(3):
            sv.execute(30.0)
        # Spike: 30 → 80 in 0.1s = 500 units/s >> 10 limit
        sv.execute(80.0)
        assert sv.alm_rate_exceeded is True


class TestSensorRedundancy:
    def test_disagreement_detected(self):
        sv = SensorValidator(range_low=0, range_high=100, redundancy_tolerance=2.0, cycle_time_s=0.005)
        sv.enable()
        for _ in range(5):
            sv.execute(35.0, raw_redundant=45.0, use_redundancy=True)
        assert sv.alm_redundancy_fault is True

    def test_agreement_uses_average(self):
        sv = SensorValidator(range_low=0, range_high=100, redundancy_tolerance=2.0, cycle_time_s=0.005, filter_time_const=0.01)
        sv.enable()
        for _ in range(20):
            sv.execute(34.0, raw_redundant=36.0, use_redundancy=True)
        # Average of 34 and 36 = 35
        assert abs(sv.value - 35.0) < 1.0


class TestSensorFrozen:
    def test_frozen_signal_detected(self):
        sv = SensorValidator(range_low=0, range_high=100, frozen_timeout_s=1.0, cycle_time_s=0.1)
        sv.enable()
        sv.execute(50.0)
        # 15 scans × 0.1s = 1.5s > 1.0s timeout
        for _ in range(15):
            sv.execute(50.0)
        assert sv.alm_frozen is True


class TestSensorSafeState:
    def test_disabled_returns_fallback(self):
        sv = SensorValidator(fallback_value=-99.0)
        sv.disable()
        sv.execute(50.0)
        assert sv.value == -99.0
        assert sv.valid is False
