"""
Unit Tests — CDU Supervisor (Python Reference Model)
"""

import pytest
from .fb_cdu_supervisor import CDUSupervisor, CDURole


class TestCDUSupervisorInit:
    def test_assigns_lead_and_standby(self):
        sup = CDUSupervisor(num_cdus=4)
        sup.enable()
        sup.execute()
        assert sup.roles[0] == CDURole.LEAD
        assert sup.roles[1] == CDURole.STANDBY
        assert sup.roles[2] == CDURole.STANDBY
        assert sup.roles[3] == CDURole.STANDBY
        assert sup.lead_index == 0

    def test_disabled_all_offline(self):
        sup = CDUSupervisor(num_cdus=4)
        sup.disable()
        assert sup.lead_index == -1
        assert all(r == CDURole.OFFLINE for r in sup.roles[:4])


class TestCDUSupervisorSwitchover:
    def test_fault_on_lead_switches_to_standby(self):
        sup = CDUSupervisor(num_cdus=4)
        sup.enable()
        sup.execute([False]*8)
        assert sup.lead_index == 0
        # Lead faults
        faults = [False]*8
        faults[0] = True
        sup.execute(faults)
        assert sup.lead_index == 1
        assert sup.roles[0] == CDURole.FAULTED
        assert sup.roles[1] == CDURole.LEAD
        assert sup.switchover_count == 1

    def test_switchover_happens_within_limit(self):
        sup = CDUSupervisor(num_cdus=4)
        sup.enable()
        sup.execute([False]*8)
        faults = [False]*8
        faults[0] = True
        # Single execution should switch
        sup.execute(faults)
        assert sup.lead_index == 1

    def test_recovered_cdu_becomes_standby(self):
        sup = CDUSupervisor(num_cdus=4)
        sup.enable()
        sup.execute([False]*8)
        # Fault CDU 2
        faults = [False]*8
        faults[2] = True
        sup.execute(faults)
        assert sup.roles[2] == CDURole.FAULTED
        # Recover CDU 2
        faults[2] = False
        sup.execute(faults)
        assert sup.roles[2] == CDURole.STANDBY


class TestCDUSupervisorAllFault:
    def test_all_faulted_sets_emergency(self):
        sup = CDUSupervisor(num_cdus=3)
        sup.enable()
        sup.execute([False]*8)
        # Fault all CDUs
        faults = [True, True, True] + [False]*5
        sup.execute(faults)
        sup.execute(faults)  # Second scan to process all
        assert sup.all_faulted is True
        assert sup.emergency_flag is True


class TestCDUSupervisorRotation:
    def test_rotation_after_interval(self):
        # Use a small rotation interval for testing
        sup = CDUSupervisor(num_cdus=4)
        sup.ROTATION_INTERVAL_SCANS = 100
        sup.enable()
        sup.execute([False]*8)
        assert sup.lead_index == 0
        # Run to rotation
        for _ in range(100):
            sup.execute([False]*8)
        assert sup.lead_index == 1
        assert sup.roles[0] == CDURole.STANDBY
        assert sup.roles[1] == CDURole.LEAD
