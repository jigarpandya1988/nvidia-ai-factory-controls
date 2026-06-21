"""
Unit Tests — FB_Base Lifecycle (Python Reference Model)
========================================================
Validates the FB_Base state machine: DISABLED → INIT → RUNNING → FAULT
"""

import pytest
from .fb_base import FBBase, Lifecycle


class TestLifecycleTransitions:
    def test_starts_disabled(self):
        fb = FBBase()
        fb.execute()
        assert fb.state == Lifecycle.DISABLED

    def test_enable_transitions_to_running(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        assert fb.state == Lifecycle.RUNNING

    def test_disable_transitions_to_disabled(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        assert fb.state == Lifecycle.RUNNING
        fb.disable()
        fb.execute()
        assert fb.state == Lifecycle.DISABLED

    def test_fault_latches(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        fb.set_fault(code=42, message="overtemp")
        fb.execute()
        assert fb.state == Lifecycle.FAULT
        assert fb.fault_active is True
        assert fb.fault_code == 42

    def test_fault_stays_latched_without_reset(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        fb.set_fault(code=1)
        # Multiple executions should not auto-recover
        for _ in range(10):
            fb.execute()
        assert fb.state == Lifecycle.FAULT

    def test_reset_clears_fault(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        fb.set_fault(code=99)
        fb.execute()
        assert fb.state == Lifecycle.FAULT
        fb.reset()
        fb.execute()
        assert fb.state == Lifecycle.RUNNING
        assert fb.fault_active is False
        assert fb.fault_code == 0


class TestHeartbeat:
    def test_increments_while_running(self):
        fb = FBBase()
        fb.enable()
        for _ in range(5):
            fb.execute()
        assert fb.heartbeat == 5

    def test_does_not_increment_when_disabled(self):
        fb = FBBase()
        for _ in range(5):
            fb.execute()
        assert fb.heartbeat == 0

    def test_does_not_increment_when_faulted(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        hb_before = fb.heartbeat
        fb.set_fault(code=1)
        for _ in range(5):
            fb.execute()
        assert fb.heartbeat == hb_before


class TestSafeState:
    def test_safe_state_called_when_disabled(self):
        fb = FBBase()
        fb.execute()
        assert fb._safe_state_called is True

    def test_safe_state_called_when_faulted(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        fb._safe_state_called = False
        fb.set_fault(code=1)
        fb.execute()
        assert fb._safe_state_called is True

    def test_safe_state_called_on_disable(self):
        fb = FBBase()
        fb.enable()
        fb.execute()
        fb._safe_state_called = False
        fb.disable()
        assert fb._safe_state_called is True
