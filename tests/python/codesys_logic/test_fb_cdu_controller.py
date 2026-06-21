"""
Unit Tests — CDU Controller (Python Reference Model)
"""

import pytest
from .fb_cdu_controller import CDUController, CDUState


class TestCDUStartup:
    def test_starts_in_idle(self):
        cdu = CDUController()
        cdu.execute()
        assert cdu.state == CDUState.IDLE
        assert cdu.pump_output == 0.0
        assert cdu.valve_output == 0.0

    def test_enable_transitions_to_running(self):
        cdu = CDUController(pre_check_scans=10, start_ramp_scans=10)
        cdu.enable()
        # Run through PRE_CHECK
        for _ in range(11):
            cdu.execute(safety_permit=True)
        assert cdu.state == CDUState.STARTING
        # Run through STARTING
        for _ in range(11):
            cdu.execute(flow_rate=40.0, flow_setpoint=50.0, safety_permit=True)
        assert cdu.state == CDUState.RUNNING
        assert cdu.ready is True


class TestCDUEmergencyStop:
    def test_emergency_stop_immediate_zero_outputs(self):
        cdu = CDUController(pre_check_scans=5, start_ramp_scans=5)
        cdu.enable()
        for _ in range(20):
            cdu.execute(flow_rate=50.0, flow_setpoint=50.0, safety_permit=True)
        # Should be running now
        assert cdu.state == CDUState.RUNNING
        cdu.emergency_stop()
        assert cdu.state == CDUState.EMERGENCY_STOP
        assert cdu.pump_output == 0.0
        assert cdu.valve_output == 0.0

    def test_loss_of_safety_permit_triggers_estop(self):
        cdu = CDUController(pre_check_scans=5, start_ramp_scans=5)
        cdu.enable()
        for _ in range(20):
            cdu.execute(flow_rate=50.0, flow_setpoint=50.0, safety_permit=True)
        assert cdu.state == CDUState.RUNNING
        # Remove safety permit
        cdu.execute(safety_permit=False)
        assert cdu.state == CDUState.EMERGENCY_STOP
        assert cdu.pump_output == 0.0


class TestCDUFault:
    def test_leak_triggers_fault(self):
        cdu = CDUController(pre_check_scans=5, start_ramp_scans=5)
        cdu.enable()
        for _ in range(20):
            cdu.execute(flow_rate=50.0, flow_setpoint=50.0, safety_permit=True)
        assert cdu.state == CDUState.RUNNING
        cdu.execute(leak_detected=True, safety_permit=True)
        assert cdu.state == CDUState.FAULT
        assert cdu.fault_code == 10
        assert cdu.pump_output == 0.0

    def test_fault_requires_reset(self):
        cdu = CDUController(pre_check_scans=5, start_ramp_scans=5)
        cdu.enable()
        for _ in range(20):
            cdu.execute(flow_rate=50.0, flow_setpoint=50.0, safety_permit=True)
        cdu.execute(leak_detected=True, safety_permit=True)
        # Fault stays without reset
        for _ in range(10):
            cdu.execute(leak_detected=False, safety_permit=True)
        assert cdu.state == CDUState.FAULT
        # Reset clears
        cdu.reset()
        assert cdu.state == CDUState.IDLE
        assert cdu.fault_code == 0


class TestCDUSafeState:
    def test_safe_state_is_idempotent(self):
        cdu = CDUController()
        cdu.emergency_stop()
        cdu.execute(safety_permit=False)
        cdu.execute(safety_permit=False)
        cdu.execute(safety_permit=False)
        assert cdu.pump_output == 0.0
        assert cdu.valve_output == 0.0
        assert cdu.state == CDUState.EMERGENCY_STOP
