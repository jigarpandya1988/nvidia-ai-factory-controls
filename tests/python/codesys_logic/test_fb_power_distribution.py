"""
Unit Tests — Power Distribution (Python Reference Model)
"""

import pytest
from .fb_power_distribution import PowerDistribution


class TestPUE:
    def test_pue_calculated_correctly(self):
        pd = PowerDistribution()
        pd.enable()
        pd.execute(total_power_kw=1200.0, it_power_kw=1000.0)
        assert abs(pd.pue - 1.2) < 0.001

    def test_pue_unity_when_equal(self):
        pd = PowerDistribution()
        pd.enable()
        pd.execute(total_power_kw=500.0, it_power_kw=500.0)
        assert abs(pd.pue - 1.0) < 0.001

    def test_pue_default_when_no_it_power(self):
        pd = PowerDistribution()
        pd.enable()
        pd.execute(total_power_kw=100.0, it_power_kw=0.0)
        assert pd.pue == 1.0  # Default when division by zero


class TestPhaseImbalance:
    def test_balanced_phases_no_alarm(self):
        pd = PowerDistribution(imbalance_alarm_pct=10.0)
        pd.enable()
        pd.execute(phase_currents=[100.0, 100.0, 100.0])
        assert pd.phase_imbalance_pct == 0.0
        assert pd.alm_phase_imbalance is False

    def test_imbalance_detected(self):
        pd = PowerDistribution(imbalance_alarm_pct=10.0)
        pd.enable()
        # (120-80)/100 * 100 = 40%
        pd.execute(phase_currents=[120.0, 100.0, 80.0])
        assert pd.phase_imbalance_pct == pytest.approx(40.0)
        assert pd.alm_phase_imbalance is True

    def test_slight_imbalance_no_alarm(self):
        pd = PowerDistribution(imbalance_alarm_pct=10.0)
        pd.enable()
        # (102-98)/100 * 100 = 4%
        pd.execute(phase_currents=[102.0, 100.0, 98.0])
        assert pd.phase_imbalance_pct == pytest.approx(4.0)
        assert pd.alm_phase_imbalance is False


class TestVoltageAlarms:
    def test_high_voltage_alarm(self):
        pd = PowerDistribution(voltage_nominal=480.0, voltage_tolerance_pct=5.0)
        pd.enable()
        # High limit = 480 * 1.05 = 504
        pd.execute(phase_voltages=[510.0, 480.0, 480.0])
        assert pd.alm_voltage_high is True
        assert pd.alm_voltage_low is False

    def test_low_voltage_alarm(self):
        pd = PowerDistribution(voltage_nominal=480.0, voltage_tolerance_pct=5.0)
        pd.enable()
        # Low limit = 480 * 0.95 = 456
        pd.execute(phase_voltages=[480.0, 450.0, 480.0])
        assert pd.alm_voltage_low is True
        assert pd.alm_voltage_high is False

    def test_normal_voltage_no_alarm(self):
        pd = PowerDistribution(voltage_nominal=480.0, voltage_tolerance_pct=5.0)
        pd.enable()
        pd.execute(phase_voltages=[480.0, 478.0, 482.0])
        assert pd.alm_voltage_high is False
        assert pd.alm_voltage_low is False


class TestEnergyAccumulation:
    def test_energy_accumulates(self):
        pd = PowerDistribution(cycle_time_s=1.0)
        pd.enable()
        # 100 kW for 1 second = 100/3600 kWh per cycle
        for _ in range(3600):
            pd.execute(total_power_kw=100.0, it_power_kw=80.0)
        # 100 kW * 3600s / 3600 = 100 kWh
        assert abs(pd.energy_kwh - 100.0) < 0.1

    def test_energy_zero_at_start(self):
        pd = PowerDistribution()
        pd.enable()
        assert pd.energy_kwh == 0.0
