"""
FB_RampGenerator — Python Reference Implementation
====================================================
Mirrors the CODESYS FB_RampGenerator.
Linear ramp from current to target at configured rate.
Clamp between min/max, reset = jump to target, enable=False = hold.
"""

from dataclasses import dataclass, field


@dataclass
class RampGenerator:
    """Python equivalent of FB_RampGenerator."""

    # Configuration
    rate: float = 10.0         # units/second
    output_min: float = 0.0
    output_max: float = 100.0
    cycle_time_s: float = 0.005

    # --- State ---
    _output: float = field(default=0.0, init=False)
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    output: float = field(default=0.0, init=False)
    at_target: bool = field(default=True, init=False)
    ramping: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        """Disable = hold current output."""
        self._enabled = False

    def reset(self, target: float):
        """Jump immediately to target (clamped)."""
        self._output = max(self.output_min, min(target, self.output_max))
        self.output = self._output
        self.at_target = True
        self.ramping = False

    def execute(self, target: float):
        """Execute one ramp cycle."""
        if not self._enabled:
            # Hold — don't change output
            self.ramping = False
            self.output = self._output
            self.at_target = abs(self._output - target) < 1e-6
            return

        # Clamp target
        clamped_target = max(self.output_min, min(target, self.output_max))

        # Calculate max step this cycle
        max_step = self.rate * self.cycle_time_s

        diff = clamped_target - self._output
        if abs(diff) <= max_step:
            # Reached target
            self._output = clamped_target
            self.at_target = True
            self.ramping = False
        else:
            # Ramp toward target
            if diff > 0:
                self._output += max_step
            else:
                self._output -= max_step
            self.at_target = False
            self.ramping = True

        # Clamp output
        self._output = max(self.output_min, min(self._output, self.output_max))
        self.output = self._output
