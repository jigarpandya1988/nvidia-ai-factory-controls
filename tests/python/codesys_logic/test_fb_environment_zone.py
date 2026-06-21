"""
Unit Tests — Environment Zone (Python Reference Model)
"""

import pytest
import math
from .fb_environment_zone import EnvironmentZone


class TestDualSensors:
    def test_average_of_two_valid_sensors(self):
        ez = EnvironmentZone()
        ez.enable()
        ez.execute(temp_sensor1=24.0, temp_sensor2=26.0)
        assert abs(ez.temperature - 25.0) < 0.01
        assert ez.using_fallback is False

    def test_fallback_to_sensor1_when_sensor2_invalid(self):
        ez = EnvironmentZone()
        ez.enable()
        ez.execute(temp_sensor1=25.0, temp_sensor2=25.0, sensor2_quality=False)
        assert abs(ez.temperature - 25.0) < 0.01
        assert ez.using_fallback is True

    def test_fallback_to_sensor2_when_sensor1_out_of_range(self):
        ez = EnvironmentZone(temp_range_high=50.0)
        ez.enable()
        ez.execute(temp_sensor1=999.0, temp_sensor2=30.0)
        assert abs(ez.temperature - 30.0) < 0.01
        assert ez.using_fallback is True

    def test_both_invalid_raises_fault(self):
        ez = EnvironmentZone()
        ez.enable()
        ez.execute(temp_sensor1=20.0, temp_sensor2=20.0,
                   sensor1_quality=False, sensor2_quality=False)
        assert ez.alm_sensor_fault is True


class TestDewPoint:
    def test_dew_point_calculation_accuracy(self):
        ez = EnvironmentZone()
        ez.enable()
        # At T=25°C, RH=50%:
        # gamma = ln(0.5) + (17.27*25)/(237.7+25) = -0.6931 + 1.6440 = 0.9509
        # dp = (237.7*0.9509)/(17.27-0.9509) = 226.03/16.32 ≈ 13.85°C
        ez.execute(temp_sensor1=25.0, temp_sensor2=25.0, relative_humidity=50.0)
        expected_gamma = math.log(50.0 / 100.0) + (17.27 * 25.0) / (237.7 + 25.0)
        expected_dp = (237.7 * expected_gamma) / (17.27 - expected_gamma)
        assert abs(ez.dew_point - expected_dp) < 0.01

    def test_high_humidity_dew_point_near_temp(self):
        ez = EnvironmentZone()
        ez.enable()
        ez.execute(temp_sensor1=20.0, temp_sensor2=20.0, relative_humidity=95.0)
        # At high humidity, dew point approaches temperature
        assert ez.dew_point > 18.0
        assert ez.dew_point < 20.0

    def test_low_humidity_dew_point_well_below_temp(self):
        ez = EnvironmentZone()
        ez.enable()
        ez.execute(temp_sensor1=25.0, temp_sensor2=25.0, relative_humidity=20.0)
        assert ez.dew_point < 5.0


class TestCondensation:
    def test_condensation_alarm_when_margin_below_threshold(self):
        ez = EnvironmentZone(condensation_margin_c=5.0)
        ez.enable()
        # At T=20°C, RH=90%, dew point ~18.3°C, margin ~1.7°C < 5.0
        ez.execute(temp_sensor1=20.0, temp_sensor2=20.0, relative_humidity=90.0)
        assert ez.alm_condensation is True
        assert ez.condensation_margin < 5.0

    def test_no_condensation_alarm_when_dry(self):
        ez = EnvironmentZone(condensation_margin_c=3.0)
        ez.enable()
        ez.execute(temp_sensor1=25.0, temp_sensor2=25.0, relative_humidity=30.0)
        assert ez.alm_condensation is False
        assert ez.condensation_margin > 3.0


class TestEnvironmentDisabled:
    def test_disabled_no_alarms(self):
        ez = EnvironmentZone()
        ez.disable()
        ez.execute(temp_sensor1=99.0, temp_sensor2=99.0, relative_humidity=100.0)
        assert ez.alm_condensation is False
        assert ez.alm_sensor_fault is False
