"""
FB_PowerDistribution — Python Reference Implementation
========================================================
Mirrors the CODESYS FB_PowerDistribution.
PUE calculation, phase imbalance detection, voltage alarms, energy accumulation.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class PowerDistribution:
    """Python equivalent of FB_PowerDistribution."""

    # Configuration
    num_phases: int = 3
    voltage_nominal: float = 480.0
    voltage_tolerance_pct: float = 5.0   # ±5% alarm threshold
    imbalance_alarm_pct: float = 10.0    # Phase imbalance alarm threshold
    cycle_time_s: float = 0.005

    # --- State ---
    _energy_kwh: float = field(default=0.0, init=False)
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    pue: float = field(default=1.0, init=False)
    phase_imbalance_pct: float = field(default=0.0, init=False)
    total_power_kw: float = field(default=0.0, init=False)
    it_power_kw: float = field(default=0.0, init=False)
    energy_kwh: float = field(default=0.0, init=False)
    alm_voltage_high: bool = field(default=False, init=False)
    alm_voltage_low: bool = field(default=False, init=False)
    alm_phase_imbalance: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
        self.pue = 1.0
        self.alm_voltage_high = False
        self.alm_voltage_low = False
        self.alm_phase_imbalance = False

    def execute(
        self,
        total_power_kw: float = 0.0,
        it_power_kw: float = 0.0,
        phase_voltages: List[float] = None,
        phase_currents: List[float] = None,
    ):
        """Execute one power distribution cycle."""
        if phase_voltages is None:
            phase_voltages = [self.voltage_nominal] * self.num_phases
        if phase_currents is None:
            phase_currents = [0.0] * self.num_phases

        if not self._enabled:
            return

        # PUE Calculation
        self.total_power_kw = total_power_kw
        self.it_power_kw = it_power_kw
        if it_power_kw > 0.0:
            self.pue = total_power_kw / it_power_kw
        else:
            self.pue = 1.0  # Undefined, default to 1.0

        # Phase imbalance: (max - min) / avg * 100
        if self.num_phases > 1 and len(phase_currents) >= self.num_phases:
            currents = phase_currents[:self.num_phases]
            max_c = max(currents)
            min_c = min(currents)
            avg_c = sum(currents) / self.num_phases
            if avg_c > 0:
                self.phase_imbalance_pct = (max_c - min_c) / avg_c * 100.0
            else:
                self.phase_imbalance_pct = 0.0
            self.alm_phase_imbalance = self.phase_imbalance_pct > self.imbalance_alarm_pct
        else:
            self.phase_imbalance_pct = 0.0
            self.alm_phase_imbalance = False

        # Voltage alarms
        v_high_limit = self.voltage_nominal * (1.0 + self.voltage_tolerance_pct / 100.0)
        v_low_limit = self.voltage_nominal * (1.0 - self.voltage_tolerance_pct / 100.0)
        self.alm_voltage_high = any(v > v_high_limit for v in phase_voltages[:self.num_phases])
        self.alm_voltage_low = any(v < v_low_limit for v in phase_voltages[:self.num_phases])

        # Energy accumulation (kW * time_in_hours)
        self._energy_kwh += total_power_kw * (self.cycle_time_s / 3600.0)
        self.energy_kwh = self._energy_kwh
