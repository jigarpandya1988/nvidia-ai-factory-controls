"""
FB_FireSuppression — Python Reference Implementation
=====================================================
Mirrors the CODESYS FB_FireSuppression state machine.
States: NORMAL → ALERT → PRE_ALARM → ALARM → COUNTDOWN → DISCHARGED
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List


class FireState(IntEnum):
    NORMAL = 0
    ALERT = 1
    PRE_ALARM = 2
    ALARM = 3
    COUNTDOWN = 4
    DISCHARGED = 5


@dataclass
class FireSuppression:
    """Python equivalent of FB_FireSuppression."""

    NUM_SPOT_DETECTORS: int = 8
    COUNTDOWN_SCANS: int = 15000  # 30s at 2ms cycle
    CYCLE_TIME_MS: int = 2

    # --- State ---
    _state: FireState = field(default=FireState.NORMAL, init=False)
    _countdown_count: int = field(default=0, init=False)
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    state: FireState = field(default=FireState.NORMAL, init=False)
    discharge_command: bool = field(default=False, init=False)
    countdown_remaining_s: float = field(default=0.0, init=False)
    alarm_active: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
        self._safe_state()

    def execute(
        self,
        vesda_level: int = 0,
        spot_detectors: List[bool] = None,
        abort_button: bool = False,
        manual_release: bool = False,
        reset: bool = False,
    ):
        """Execute one fire suppression cycle (2ms equivalent)."""
        if spot_detectors is None:
            spot_detectors = [False] * self.NUM_SPOT_DETECTORS

        if not self._enabled:
            self._safe_state()
            return

        # Reset from DISCHARGED
        if reset and self._state == FireState.DISCHARGED:
            self._state = FireState.NORMAL
            self._countdown_count = 0
            self.discharge_command = False

        # Determine detection level
        spots_active = sum(spot_detectors)

        # State machine
        if self._state == FireState.NORMAL:
            if vesda_level >= 1 or spots_active >= 1:
                self._state = FireState.ALERT
            if vesda_level >= 2:
                self._state = FireState.PRE_ALARM
            if vesda_level >= 3 or spots_active >= 2 or manual_release:
                self._state = FireState.ALARM

        elif self._state == FireState.ALERT:
            if vesda_level == 0 and spots_active == 0:
                self._state = FireState.NORMAL
            elif vesda_level >= 2:
                self._state = FireState.PRE_ALARM
            elif vesda_level >= 3 or spots_active >= 2 or manual_release:
                self._state = FireState.ALARM

        elif self._state == FireState.PRE_ALARM:
            if vesda_level == 0 and spots_active == 0:
                self._state = FireState.NORMAL
            elif vesda_level < 2 and spots_active < 2:
                self._state = FireState.ALERT
            elif vesda_level >= 3 or spots_active >= 2 or manual_release:
                self._state = FireState.ALARM

        elif self._state == FireState.ALARM:
            # Transition to countdown
            self._state = FireState.COUNTDOWN
            self._countdown_count = 0

        elif self._state == FireState.COUNTDOWN:
            if abort_button:
                # Abort resets countdown back to ALARM (will re-enter COUNTDOWN next scan)
                self._state = FireState.ALARM
                self._countdown_count = 0
            else:
                self._countdown_count += 1
                if self._countdown_count >= self.COUNTDOWN_SCANS:
                    self._state = FireState.DISCHARGED
                    self.discharge_command = True

        elif self._state == FireState.DISCHARGED:
            self.discharge_command = True  # Stays discharged

        # Update outputs
        self.state = self._state
        self.alarm_active = self._state in (FireState.ALARM, FireState.COUNTDOWN, FireState.DISCHARGED)
        if self._state == FireState.COUNTDOWN:
            remaining = (self.COUNTDOWN_SCANS - self._countdown_count) * self.CYCLE_TIME_MS / 1000.0
            self.countdown_remaining_s = max(0.0, remaining)
        else:
            self.countdown_remaining_s = 0.0

    def _safe_state(self):
        """Safe state: no discharge."""
        self._state = FireState.NORMAL
        self.state = FireState.NORMAL
        self.discharge_command = False
        self.countdown_remaining_s = 0.0
        self.alarm_active = False
        self._countdown_count = 0
