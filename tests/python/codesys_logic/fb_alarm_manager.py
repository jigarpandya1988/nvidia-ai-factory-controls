"""
FB_AlarmManager — Python Reference Implementation
===================================================
Mirrors the CODESYS FB_AlarmManager.
Circular buffer of 100 alarms. Raise, clear, acknowledge operations.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class AlarmSeverity(IntEnum):
    INFO = 0
    WARNING = 1
    CRITICAL = 2
    EMERGENCY = 3


@dataclass
class AlarmRecord:
    """Single alarm record."""
    alarm_id: int = 0
    severity: AlarmSeverity = AlarmSeverity.INFO
    source: str = ""
    message: str = ""
    active: bool = True
    acknowledged: bool = False
    timestamp: int = 0  # Scan counter as timestamp


@dataclass
class AlarmManager:
    """Python equivalent of FB_AlarmManager."""

    BUFFER_SIZE: int = 100

    # --- State ---
    _buffer: List[Optional[AlarmRecord]] = field(default_factory=lambda: [None] * 100, init=False)
    _write_index: int = field(default=0, init=False)
    _scan_counter: int = field(default=0, init=False)

    # --- Outputs ---
    total_alarms: int = field(default=0, init=False)
    active_count: int = field(default=0, init=False)
    unacknowledged_count: int = field(default=0, init=False)

    def execute(self):
        """Execute one cycle — updates counters."""
        self._scan_counter += 1
        self._update_counts()

    def raise_alarm(self, alarm_id: int, severity: AlarmSeverity, source: str = "", message: str = ""):
        """Raise a new alarm — adds to circular buffer."""
        record = AlarmRecord(
            alarm_id=alarm_id,
            severity=severity,
            source=source,
            message=message,
            active=True,
            acknowledged=False,
            timestamp=self._scan_counter,
        )
        self._buffer[self._write_index] = record
        self._write_index = (self._write_index + 1) % self.BUFFER_SIZE
        self.total_alarms += 1
        self._update_counts()

    def clear_alarm(self, alarm_id: int):
        """Clear an alarm by ID — marks inactive."""
        for i in range(self.BUFFER_SIZE):
            if self._buffer[i] is not None and self._buffer[i].alarm_id == alarm_id and self._buffer[i].active:
                self._buffer[i].active = False
        self._update_counts()

    def acknowledge(self, alarm_id: int):
        """Acknowledge an alarm by ID."""
        for i in range(self.BUFFER_SIZE):
            if self._buffer[i] is not None and self._buffer[i].alarm_id == alarm_id and not self._buffer[i].acknowledged:
                self._buffer[i].acknowledged = True
        self._update_counts()

    def get_alarm(self, alarm_id: int) -> Optional[AlarmRecord]:
        """Get the most recent alarm record for given ID."""
        for i in range(self.BUFFER_SIZE - 1, -1, -1):
            idx = (self._write_index - 1 - i) % self.BUFFER_SIZE
            if self._buffer[idx] is not None and self._buffer[idx].alarm_id == alarm_id:
                return self._buffer[idx]
        return None

    def _update_counts(self):
        """Recount active and unacknowledged alarms."""
        active = 0
        unacked = 0
        for i in range(self.BUFFER_SIZE):
            if self._buffer[i] is not None:
                if self._buffer[i].active:
                    active += 1
                if not self._buffer[i].acknowledged:
                    unacked += 1
        self.active_count = active
        self.unacknowledged_count = unacked
