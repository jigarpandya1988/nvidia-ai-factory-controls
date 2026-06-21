"""
FB_EnvironmentZone — Python Reference Implementation
=====================================================
Mirrors the CODESYS FB_EnvironmentZone.
Dual temperature sensors, dew point (Magnus-Tetens), condensation risk.
"""

from dataclasses import dataclass, field
import math


@dataclass
class EnvironmentZone:
    """Python equivalent of FB_EnvironmentZone."""

    # Configuration
    temp_range_low: float = -10.0
    temp_range_high: float = 60.0
    condensation_margin_c: float = 3.0  # Alarm when T - dewpoint < margin
    cycle_time_s: float = 0.005

    # --- State ---
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    temperature: float = field(default=0.0, init=False)
    dew_point: float = field(default=0.0, init=False)
    condensation_margin: float = field(default=100.0, init=False)
    sensor1_valid: bool = field(default=True, init=False)
    sensor2_valid: bool = field(default=True, init=False)
    alm_condensation: bool = field(default=False, init=False)
    alm_sensor_fault: bool = field(default=False, init=False)
    using_fallback: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
        self.alm_condensation = False
        self.alm_sensor_fault = False

    def execute(
        self,
        temp_sensor1: float = 20.0,
        temp_sensor2: float = 20.0,
        sensor1_quality: bool = True,
        sensor2_quality: bool = True,
        relative_humidity: float = 50.0,
    ):
        """Execute one environment zone cycle."""
        if not self._enabled:
            return

        self.sensor1_valid = sensor1_quality and (self.temp_range_low <= temp_sensor1 <= self.temp_range_high)
        self.sensor2_valid = sensor2_quality and (self.temp_range_low <= temp_sensor2 <= self.temp_range_high)

        # Temperature selection
        if self.sensor1_valid and self.sensor2_valid:
            self.temperature = (temp_sensor1 + temp_sensor2) / 2.0
            self.using_fallback = False
            self.alm_sensor_fault = False
        elif self.sensor1_valid:
            self.temperature = temp_sensor1
            self.using_fallback = True
            self.alm_sensor_fault = False
        elif self.sensor2_valid:
            self.temperature = temp_sensor2
            self.using_fallback = True
            self.alm_sensor_fault = False
        else:
            # Both invalid
            self.alm_sensor_fault = True
            self.using_fallback = True
            # Hold last value (don't update temperature)

        # Dew point calculation (Magnus-Tetens approximation)
        # gamma = ln(RH/100) + (17.27*T)/(237.7+T)
        # dp = (237.7*gamma)/(17.27-gamma)
        rh_clamped = max(1.0, min(relative_humidity, 100.0))
        t = self.temperature
        gamma = math.log(rh_clamped / 100.0) + (17.27 * t) / (237.7 + t)
        if 17.27 - gamma != 0:
            self.dew_point = (237.7 * gamma) / (17.27 - gamma)
        else:
            self.dew_point = t  # Edge case

        # Condensation risk
        self.condensation_margin = self.temperature - self.dew_point
        self.alm_condensation = self.condensation_margin < self.condensation_margin_c
