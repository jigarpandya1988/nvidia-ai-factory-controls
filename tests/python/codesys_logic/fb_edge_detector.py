"""
FB_EdgeDetector — Python Reference Implementation
===================================================
Mirrors the CODESYS FB_EdgeDetector.
Combined rising + falling edge detection in one FB.
"""

from dataclasses import dataclass, field


@dataclass
class EdgeDetector:
    """Python equivalent of FB_EdgeDetector."""

    # --- State ---
    _prev_input: bool = field(default=False, init=False)
    _first_scan: bool = field(default=True, init=False)

    # --- Outputs ---
    rising: bool = field(default=False, init=False)
    falling: bool = field(default=False, init=False)

    def execute(self, signal: bool):
        """Execute one edge detection cycle."""
        if self._first_scan:
            self._prev_input = signal
            self._first_scan = False
            self.rising = False
            self.falling = False
            return

        # Rising edge: 0 → 1
        self.rising = signal and not self._prev_input
        # Falling edge: 1 → 0
        self.falling = not signal and self._prev_input

        self._prev_input = signal

    def reset(self):
        """Reset edge detector state."""
        self._prev_input = False
        self._first_scan = True
        self.rising = False
        self.falling = False
