"""
Unit Tests — Ramp Generator (Python Reference Model)
"""

import pytest
from .fb_ramp_generator import RampGenerator


class TestRampLinear:
    def test_ramps_linearly_up(self):
        rg = RampGenerator(rate=10.0, cycle_time_s=0.1)  # 1 unit/cycle
        rg.enable()
        rg.execute(target=5.0)
        assert abs(rg.output - 1.0) < 0.01
        rg.execute(target=5.0)
        assert abs(rg.output - 2.0) < 0.01

    def test_ramps_linearly_down(self):
        rg = RampGenerator(rate=10.0, cycle_time_s=0.1)
        rg.reset(50.0)
        rg.enable()
        rg.execute(target=45.0)
        assert abs(rg.output - 49.0) < 0.01
        rg.execute(target=45.0)
        assert abs(rg.output - 48.0) < 0.01

    def test_reaches_target_exactly(self):
        rg = RampGenerator(rate=10.0, cycle_time_s=0.1)  # 1 unit/cycle
        rg.enable()
        for _ in range(10):
            rg.execute(target=5.0)
        assert abs(rg.output - 5.0) < 0.01
        assert rg.at_target is True
        assert rg.ramping is False


class TestRampRate:
    def test_respects_configured_rate(self):
        rg = RampGenerator(rate=20.0, cycle_time_s=0.05)  # 1 unit/cycle
        rg.enable()
        rg.execute(target=100.0)
        assert abs(rg.output - 1.0) < 0.01

    def test_faster_rate_reaches_sooner(self):
        rg_slow = RampGenerator(rate=5.0, cycle_time_s=0.1)   # 0.5/cycle
        rg_fast = RampGenerator(rate=50.0, cycle_time_s=0.1)   # 5/cycle
        rg_slow.enable()
        rg_fast.enable()
        for _ in range(10):
            rg_slow.execute(target=50.0)
            rg_fast.execute(target=50.0)
        assert rg_fast.output > rg_slow.output


class TestRampClamp:
    def test_clamps_at_max(self):
        rg = RampGenerator(rate=100.0, output_max=80.0, cycle_time_s=0.1)
        rg.enable()
        for _ in range(100):
            rg.execute(target=200.0)
        assert rg.output == 80.0

    def test_clamps_at_min(self):
        rg = RampGenerator(rate=100.0, output_min=10.0, cycle_time_s=0.1)
        rg.reset(50.0)
        rg.enable()
        for _ in range(100):
            rg.execute(target=-50.0)
        assert rg.output == 10.0


class TestRampReset:
    def test_reset_jumps_to_target(self):
        rg = RampGenerator(rate=1.0, cycle_time_s=0.1)
        rg.enable()
        rg.execute(target=50.0)
        assert rg.output < 50.0  # Still ramping
        rg.reset(50.0)
        assert rg.output == 50.0
        assert rg.at_target is True


class TestRampHold:
    def test_hold_freezes_output(self):
        rg = RampGenerator(rate=10.0, cycle_time_s=0.1)
        rg.enable()
        for _ in range(3):
            rg.execute(target=50.0)
        held_value = rg.output
        rg.disable()  # Hold
        for _ in range(10):
            rg.execute(target=50.0)
        assert rg.output == held_value
