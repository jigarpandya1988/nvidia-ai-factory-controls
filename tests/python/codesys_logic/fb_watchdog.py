"""
FB_Watchdog — Python Reference Implementation
===============================================
Mirrors the CODESYS FB_Watchdog.
Monitors external heartbeat counter. Times out if counter
doesn't change within configured timeout.
"""

from dataclasses import dataclass, field


@dataclass
class Watchdog:
    """Python equivalent of FB_Watchdog."""

    # Configuration
    timeout_ms: int = 1000     # Timeout in ms
    cycle_time_ms: int = 5     # Cycle time in ms

    # --- State ---
    _last_counter: int = field(default=0, init=False)
    _timer: int = field(default=0, init=False)
    _first_scan: bool = field(default=True, init=False)
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    alive: bool = field(default=False, init=False)
    timed_out: bool = field(default=False, init=False)
    elapsed_ms: int = field(default=0, init=False)

    @property
    def timeout_scans(self) -> int:
        """Timeout in scan counts."""
        return self.timeout_ms // self.cycle_time_ms

    def enable(self):
        self._enabled = True
        self._first_scan = True

    def disable(self):
        self._enabled = False
        self.alive = False
        self.timed_out = False
        self._timer = 0

    def execute(self, heartbeat_counter: int):
        """Execute one watchdog cycle."""
        if not self._enabled:
            self.alive = False
            self.timed_out = False
            return

        if self._first_scan:
            self._last_counter = heartbeat_counter
            self._first_scan = False
            self.alive = True
            self.timed_out = False
            return

        if heartbeat_counter != self._last_counter:
            # Counter changed — alive
            self._last_counter = heartbeat_counter
            self._timer = 0
            self.alive = True
            self.timed_out = False
        else:
            # Counter frozen — increment timer
            self._timer += 1
            if self._timer >= self.timeout_scans:
                self.alive = False
                self.timed_out = True

        self.elapsed_ms = self._timer * self.cycle_time_ms
