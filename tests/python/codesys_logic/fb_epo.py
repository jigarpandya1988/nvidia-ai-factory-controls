"""
FB_EPO_Controller — Python Reference Implementation
=====================================================
Mirrors the CODESYS EPO controller safety logic.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class EPOController:
    """Python equivalent of FB_EPO_Controller."""

    MAX_ZONES: int = 8
    DISCREPANCY_LIMIT_SCANS: int = 100  # 200ms / 2ms cycle
    RESET_HOLD_SCANS: int = 1500        # 3s / 2ms cycle

    # State
    _trip_latch: List[bool] = field(default_factory=lambda: [False] * 8, init=False)
    _channel_fault: List[bool] = field(default_factory=lambda: [False] * 8, init=False)
    _discrepancy_count: List[int] = field(default_factory=lambda: [0] * 8, init=False)
    _reset_hold_count: int = field(default=0, init=False)
    _enabled: bool = field(default=False, init=False)

    # Outputs
    relay: List[bool] = field(default_factory=lambda: [True] * 8, init=False)
    any_zone_tripped: bool = field(default=False, init=False)
    any_input_fault: bool = field(default=False, init=False)
    tripped_zone_count: int = field(default=0, init=False)
    system_armed: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
        self.relay = [False] * self.MAX_ZONES  # All relays off (safe)
        self.system_armed = False

    def execute(
        self,
        ch1: List[bool],
        ch2: List[bool],
        button_to_zone: List[int],
        trip_fire: bool = False,
        trip_leak: bool = False,
        trip_seismic: bool = False,
        trip_thermal: bool = False,
        reset_key: bool = False,
        reset_button: bool = False,
        reset_authorized: bool = False,
        test_mode: bool = False,
    ):
        """Execute one EPO cycle (2ms equivalent)."""
        if not self._enabled:
            self.relay = [False] * self.MAX_ZONES
            self.system_armed = False
            return

        # STEP 1: Dual-channel monitoring
        self.any_input_fault = False
        for i in range(self.MAX_ZONES):
            if ch1[i] != ch2[i]:
                self._discrepancy_count[i] += 1
            else:
                self._discrepancy_count[i] = 0

            self._channel_fault[i] = self._discrepancy_count[i] >= self.DISCREPANCY_LIMIT_SCANS
            if self._channel_fault[i]:
                self.any_input_fault = True

        # STEP 2: Manual trip (pessimistic)
        for i in range(self.MAX_ZONES):
            valid_trip = ch1[i] and ch2[i]
            # Pessimistic: single channel with fault still trips
            if not valid_trip and self._channel_fault[i]:
                valid_trip = ch1[i] or ch2[i]

            if valid_trip:
                zone = button_to_zone[i]
                if 0 <= zone < self.MAX_ZONES:
                    self._trip_latch[zone] = True

        # STEP 3: Automatic trips (all zones)
        if trip_fire or trip_leak or trip_seismic or trip_thermal:
            for i in range(self.MAX_ZONES):
                self._trip_latch[i] = True

        # STEP 4: Output relay states
        self.any_zone_tripped = False
        self.tripped_zone_count = 0
        for i in range(self.MAX_ZONES):
            if self._trip_latch[i]:
                self.any_zone_tripped = True
                self.tripped_zone_count += 1
                if not test_mode:
                    self.relay[i] = False  # De-energize (safe)
            else:
                self.relay[i] = True  # Energized (power ON)

        # STEP 5: Reset sequence
        if reset_key and reset_button and reset_authorized and self.any_zone_tripped:
            self._reset_hold_count += 1
        else:
            self._reset_hold_count = 0

        if self._reset_hold_count >= self.RESET_HOLD_SCANS:
            self._trip_latch = [False] * self.MAX_ZONES
            self._reset_hold_count = 0

        self.system_armed = self._enabled and not self.any_input_fault
