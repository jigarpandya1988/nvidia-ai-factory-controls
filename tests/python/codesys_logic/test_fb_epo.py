"""
Unit Tests — EPO Controller (Python Reference Model)
"""

import pytest
from .fb_epo import EPOController


class TestEPONormalState:
    def test_all_relays_energized(self):
        epo = EPOController()
        epo.enable()
        ch1 = [False] * 8
        ch2 = [False] * 8
        zone_map = list(range(8))
        epo.execute(ch1, ch2, zone_map)
        assert all(epo.relay)
        assert not epo.any_zone_tripped
        assert epo.system_armed

    def test_no_trips_no_faults(self):
        epo = EPOController()
        epo.enable()
        epo.execute([False]*8, [False]*8, list(range(8)))
        assert epo.tripped_zone_count == 0
        assert not epo.any_input_fault


class TestEPOManualTrip:
    def test_button_trips_zone(self):
        epo = EPOController()
        epo.enable()
        ch1 = [False] * 8
        ch2 = [False] * 8
        ch1[0] = True  # Button 1 pressed
        ch2[0] = True
        zone_map = list(range(8))
        epo.execute(ch1, ch2, zone_map)
        assert epo.relay[0] is False  # Zone 0 de-energized
        assert epo.relay[1] is True   # Other zones OK
        assert epo.any_zone_tripped
        assert epo.tripped_zone_count == 1

    def test_trip_latches_after_release(self):
        epo = EPOController()
        epo.enable()
        ch1 = [True] + [False]*7
        ch2 = [True] + [False]*7
        epo.execute(ch1, ch2, list(range(8)))
        # Release button
        ch1[0] = False
        ch2[0] = False
        epo.execute(ch1, ch2, list(range(8)))
        # Should still be tripped (latched)
        assert epo.any_zone_tripped
        assert epo.relay[0] is False


class TestEPOAutoTrip:
    def test_fire_trips_all_zones(self):
        epo = EPOController()
        epo.enable()
        epo.execute([False]*8, [False]*8, list(range(8)), trip_fire=True)
        assert epo.tripped_zone_count == 8
        assert all(r is False for r in epo.relay)


class TestEPOReset:
    def test_requires_all_three_inputs(self):
        epo = EPOController()
        epo.enable()
        # Trip
        epo.execute([False]*8, [False]*8, list(range(8)), trip_fire=True)
        assert epo.any_zone_tripped

        # Try reset with only key (should NOT work)
        for _ in range(2000):
            epo.execute([False]*8, [False]*8, list(range(8)),
                       reset_key=True, reset_button=False, reset_authorized=False)
        assert epo.any_zone_tripped  # Still tripped

    def test_full_reset_clears_trips(self):
        epo = EPOController()
        epo.enable()
        epo.execute([False]*8, [False]*8, list(range(8)), trip_fire=True)
        # Hold all three for 3 seconds (1500 scans at 2ms)
        for _ in range(1600):
            epo.execute([False]*8, [False]*8, list(range(8)),
                       reset_key=True, reset_button=True, reset_authorized=True)
        assert not epo.any_zone_tripped
        assert all(epo.relay)


class TestEPODualChannel:
    def test_discrepancy_detected(self):
        epo = EPOController()
        epo.enable()
        ch1 = [False]*8
        ch2 = [False]*8
        ch1[2] = True   # Only channel 1 active (fault)
        ch2[2] = False
        # Run for discrepancy timeout
        for _ in range(150):
            epo.execute(ch1, ch2, list(range(8)))
        assert epo.any_input_fault

    def test_pessimistic_single_channel_trips(self):
        epo = EPOController()
        epo.enable()
        ch1 = [False]*8
        ch2 = [False]*8
        ch1[2] = True
        ch2[2] = False  # Discrepancy
        # After fault detected, single channel should still trip
        for _ in range(150):
            epo.execute(ch1, ch2, list(range(8)))
        assert epo.any_zone_tripped  # Pessimistic: trips anyway


class TestEPOSafeState:
    def test_disabled_all_relays_off(self):
        epo = EPOController()
        epo.disable()
        epo.execute([False]*8, [False]*8, list(range(8)))
        assert all(r is False for r in epo.relay)
        assert not epo.system_armed
