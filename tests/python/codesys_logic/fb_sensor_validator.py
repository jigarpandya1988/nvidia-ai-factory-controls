"""
FB_SensorValidator — Python Reference Implementation
=====================================================
Mirrors the CODESYS FB_SensorValidator validation pipeline.
"""

from dataclasses import dataclass, field


@dataclass
class SensorValidator:
    """Python equivalent of FB_SensorValidator."""

    # Configuration
    range_low: float = 0.0
    range_high: float = 100.0
    max_rate_of_change: float = 50.0  # units/s; 0 = disabled
    fallback_value: float = 0.0
    filter_time_const: float = 0.5  # seconds
    frozen_timeout_s: float = 30.0
    redundancy_tolerance: float = 2.0
    cycle_time_s: float = 0.005
    max_fault_count: int = 10

    # State
    _filtered: float = field(default=0.0, init=False)
    _filter_alpha: float = field(default=1.0, init=False)
    _prev_value: float = field(default=0.0, init=False)
    _frozen_timer: float = field(default=0.0, init=False)
    _frozen_last_value: float = field(default=0.0, init=False)
    _fault_count: int = field(default=0, init=False)
    _first_scan: bool = field(default=True, init=False)
    _enabled: bool = field(default=False, init=False)

    # Outputs
    value: float = field(default=0.0, init=False)
    valid: bool = field(default=False, init=False)
    rate_of_change: float = field(default=0.0, init=False)
    alm_out_of_range: bool = field(default=False, init=False)
    alm_rate_exceeded: bool = field(default=False, init=False)
    alm_redundancy_fault: bool = field(default=False, init=False)
    alm_frozen: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
        self.value = self.fallback_value
        self.valid = False

    def execute(self, raw_input: float, raw_redundant: float = 0.0, use_redundancy: bool = False) -> float:
        """Execute one validation cycle. Returns validated value."""
        if not self._enabled:
            self.value = self.fallback_value
            self.valid = False
            return self.value

        # First scan init
        if self._first_scan:
            self._prev_value = raw_input
            self._filtered = raw_input
            self._frozen_last_value = raw_input
            if self.filter_time_const > 0 and self.cycle_time_s > 0:
                self._filter_alpha = self.cycle_time_s / (self.filter_time_const + self.cycle_time_s)
            else:
                self._filter_alpha = 1.0
            self._first_scan = False
            self.value = raw_input
            self.valid = True
            return self.value

        # CHECK 1: Range
        range_ok = self.range_low <= raw_input <= self.range_high
        self.alm_out_of_range = not range_ok

        # CHECK 2: Rate of change
        if self.max_rate_of_change > 0 and self.cycle_time_s > 0:
            self.rate_of_change = abs(raw_input - self._prev_value) / self.cycle_time_s
            rate_ok = self.rate_of_change <= self.max_rate_of_change
        else:
            self.rate_of_change = 0.0
            rate_ok = True
        self.alm_rate_exceeded = not rate_ok

        # CHECK 3: Redundancy
        if use_redundancy:
            redundancy_ok = abs(raw_input - raw_redundant) <= self.redundancy_tolerance
            if redundancy_ok:
                selected_value = (raw_input + raw_redundant) / 2.0
            else:
                if range_ok:
                    selected_value = raw_input
                elif self.range_low <= raw_redundant <= self.range_high:
                    selected_value = raw_redundant
                else:
                    selected_value = self.fallback_value
        else:
            redundancy_ok = True
            selected_value = raw_input
        self.alm_redundancy_fault = not redundancy_ok

        # CHECK 4: Frozen signal
        if abs(raw_input - self._frozen_last_value) > 0.01:
            self._frozen_timer = 0.0
            self._frozen_last_value = raw_input
            frozen_ok = True
        else:
            self._frozen_timer += self.cycle_time_s
            frozen_ok = self._frozen_timer < self.frozen_timeout_s
        self.alm_frozen = not frozen_ok

        # Fault counter (hysteresis)
        all_ok = range_ok and rate_ok and redundancy_ok and frozen_ok
        if not all_ok:
            if self._fault_count < self.max_fault_count:
                self._fault_count += 1
        else:
            if self._fault_count > 0:
                self._fault_count -= 1

        # Filter (only on valid data)
        if self._fault_count < self.max_fault_count:
            self._filtered += self._filter_alpha * (selected_value - self._filtered)
        else:
            self._filtered = self.fallback_value

        # Output
        self.value = self._filtered
        self.valid = self._fault_count < self.max_fault_count
        self._prev_value = raw_input

        return self.value
