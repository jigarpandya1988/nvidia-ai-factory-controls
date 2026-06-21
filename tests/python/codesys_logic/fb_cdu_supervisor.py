"""
FB_CDU_Supervisor — Python Reference Implementation
=====================================================
Mirrors the CODESYS FB_CDU_Supervisor.
Manages N CDUs (up to 8) with N+1 redundancy.
Lead/standby assignment, auto switchover, lead rotation.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class CDURole(IntEnum):
    STANDBY = 0
    LEAD = 1
    FAULTED = 2
    OFFLINE = 3


@dataclass
class CDUSupervisor:
    """Python equivalent of FB_CDU_Supervisor."""

    MAX_CDUS: int = 8
    SWITCHOVER_LIMIT_SCANS: int = 1000  # 5s at 5ms cycle
    ROTATION_INTERVAL_SCANS: int = 120_960_000  # 168 hours at 5ms cycle (168*3600*200)
    CYCLE_TIME_MS: int = 5

    # Configuration
    num_cdus: int = 4

    # --- State ---
    _roles: List[CDURole] = field(default_factory=lambda: [CDURole.STANDBY] * 8, init=False)
    _lead_index: int = field(default=-1, init=False)
    _switchover_timer: int = field(default=0, init=False)
    _rotation_timer: int = field(default=0, init=False)
    _enabled: bool = field(default=False, init=False)
    _initialized: bool = field(default=False, init=False)

    # --- Outputs ---
    roles: List[CDURole] = field(default_factory=lambda: [CDURole.STANDBY] * 8, init=False)
    lead_index: int = field(default=-1, init=False)
    all_faulted: bool = field(default=False, init=False)
    emergency_flag: bool = field(default=False, init=False)
    switchover_count: int = field(default=0, init=False)

    def enable(self):
        self._enabled = True
        if not self._initialized:
            self._assign_initial_roles()
            self._initialized = True

    def disable(self):
        self._enabled = False
        self._roles = [CDURole.OFFLINE] * self.MAX_CDUS
        self._lead_index = -1
        self._update_outputs()

    def execute(self, cdu_faults: List[bool] = None):
        """Execute one supervisor cycle."""
        if cdu_faults is None:
            cdu_faults = [False] * self.MAX_CDUS

        if not self._enabled:
            self._update_outputs()
            return

        # Check if lead is faulted
        if self._lead_index >= 0 and cdu_faults[self._lead_index]:
            self._roles[self._lead_index] = CDURole.FAULTED
            self._switchover_timer += 1
            if self._switchover_timer <= self.SWITCHOVER_LIMIT_SCANS:
                # Try to switch to a standby
                new_lead = self._find_standby(cdu_faults)
                if new_lead >= 0:
                    self._roles[new_lead] = CDURole.LEAD
                    self._lead_index = new_lead
                    self._switchover_timer = 0
                    self.switchover_count += 1
        else:
            self._switchover_timer = 0

        # Update faults for non-lead CDUs
        for i in range(self.num_cdus):
            if i != self._lead_index:
                if cdu_faults[i]:
                    self._roles[i] = CDURole.FAULTED
                elif self._roles[i] == CDURole.FAULTED and not cdu_faults[i]:
                    # Recovered
                    self._roles[i] = CDURole.STANDBY

        # Check all faulted
        active_cdus = [i for i in range(self.num_cdus) if self._roles[i] != CDURole.FAULTED]
        self.all_faulted = len(active_cdus) == 0
        self.emergency_flag = self.all_faulted

        # Lead rotation
        self._rotation_timer += 1
        if self._rotation_timer >= self.ROTATION_INTERVAL_SCANS:
            self._rotate_lead(cdu_faults)
            self._rotation_timer = 0

        self._update_outputs()

    def _assign_initial_roles(self):
        """Assign first CDU as lead, rest as standby."""
        for i in range(self.MAX_CDUS):
            if i < self.num_cdus:
                self._roles[i] = CDURole.STANDBY
            else:
                self._roles[i] = CDURole.OFFLINE

        if self.num_cdus > 0:
            self._roles[0] = CDURole.LEAD
            self._lead_index = 0

    def _find_standby(self, cdu_faults: List[bool]) -> int:
        """Find first available standby CDU."""
        for i in range(self.num_cdus):
            if self._roles[i] == CDURole.STANDBY and not cdu_faults[i]:
                return i
        return -1

    def _rotate_lead(self, cdu_faults: List[bool]):
        """Rotate lead to next available CDU."""
        if self._lead_index < 0:
            return
        # Find next healthy CDU
        for offset in range(1, self.num_cdus):
            candidate = (self._lead_index + offset) % self.num_cdus
            if not cdu_faults[candidate] and self._roles[candidate] == CDURole.STANDBY:
                self._roles[self._lead_index] = CDURole.STANDBY
                self._roles[candidate] = CDURole.LEAD
                self._lead_index = candidate
                self.switchover_count += 1
                return

    def _update_outputs(self):
        """Sync internal state to outputs."""
        self.roles = list(self._roles)
        self.lead_index = self._lead_index
