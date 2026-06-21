"""
FB_LeakDetection — Python Reference Implementation
====================================================
Mirrors the CODESYS FB_LeakDetection logic.
16 leak zones, 500ms debounce (250 scans at 2ms cycle),
MINOR (1 zone) vs MAJOR (2+ zones), trip request on MAJOR.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List


class LeakSeverity(IntEnum):
    NONE = 0
    MINOR = 1
    MAJOR = 2


@dataclass
class LeakDetection:
    """Python equivalent of FB_LeakDetection."""

    MAX_ZONES: int = 16
    DEBOUNCE_SCANS: int = 250  # 500ms / 2ms cycle
    CYCLE_TIME_MS: int = 2

    # --- State ---
    _debounce_count: List[int] = field(default_factory=lambda: [0] * 16, init=False)
    _zone_active: List[bool] = field(default_factory=lambda: [False] * 16, init=False)
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    severity: LeakSeverity = field(default=LeakSeverity.NONE, init=False)
    active_zone_count: int = field(default=0, init=False)
    trip_request: bool = field(default=False, init=False)
    zone_status: List[bool] = field(default_factory=lambda: [False] * 16, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
        self._safe_state()

    def execute(self, zone_inputs: List[bool]):
        """Execute one leak detection cycle (2ms equivalent)."""
        if not self._enabled:
            self._safe_state()
            return

        # Debounce each zone
        for i in range(self.MAX_ZONES):
            if zone_inputs[i]:
                if self._debounce_count[i] < self.DEBOUNCE_SCANS:
                    self._debounce_count[i] += 1
                if self._debounce_count[i] >= self.DEBOUNCE_SCANS:
                    self._zone_active[i] = True
            else:
                self._debounce_count[i] = 0
                self._zone_active[i] = False

        # Count active zones
        self.active_zone_count = sum(self._zone_active)

        # Copy status
        self.zone_status = list(self._zone_active)

        # Classify severity
        if self.active_zone_count == 0:
            self.severity = LeakSeverity.NONE
            self.trip_request = False
        elif self.active_zone_count == 1:
            self.severity = LeakSeverity.MINOR
            self.trip_request = False
        else:  # 2+
            self.severity = LeakSeverity.MAJOR
            self.trip_request = True

    def _safe_state(self):
        """Safe state: no trip, clear all."""
        self.severity = LeakSeverity.NONE
        self.active_zone_count = 0
        self.trip_request = False
        self.zone_status = [False] * self.MAX_ZONES
        self._zone_active = [False] * self.MAX_ZONES
        self._debounce_count = [0] * self.MAX_ZONES
