"""
Thermal Physics Models — CDU, GPU Racks, Cooling Tower
========================================================
First-principles thermal simulation for AI factory cooling.

Physics:
  Q = m_dot * Cp * delta_T  (heat transfer)
  T_new = T_old + (Q_in - Q_out) / (m * Cp) * dt  (thermal mass)
  m_dot = k * speed^2  (pump affinity law — approximate)
  
Units: SI (°C, kg/s, kW, kPa)
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GPURack:
    """
    Simulates one GPU rack (e.g., NVIDIA GB200 NVL72).
    
    Heat generation varies with workload:
      Idle: ~15 kW
      Training: ~120 kW
      Inference: ~80 kW
      Burst: ~140 kW
    """
    rack_id: int = 1
    max_power_kw: float = 140.0
    idle_power_kw: float = 15.0
    
    # Thermal properties
    thermal_mass_kj_per_c: float = 50.0  # Rack thermal capacity (metal + coolant)
    
    # State
    power_kw: float = field(default=15.0, init=False)
    junction_temp_c: float = field(default=45.0, init=False)
    inlet_coolant_temp_c: float = field(default=35.0, init=False)
    outlet_coolant_temp_c: float = field(default=45.0, init=False)
    
    # GPU thermal resistance: junction to coolant [°C/kW]
    thermal_resistance: float = 0.35
    
    def set_workload(self, fraction: float):
        """Set workload as fraction (0.0 = idle, 1.0 = full power)."""
        fraction = max(0.0, min(1.0, fraction))
        self.power_kw = self.idle_power_kw + (self.max_power_kw - self.idle_power_kw) * fraction

    def update(self, coolant_supply_temp: float, coolant_flow_lpm: float, dt: float):
        """
        Update rack thermal state for one timestep.
        
        Args:
            coolant_supply_temp: CDU supply temperature [°C]
            coolant_flow_lpm: Coolant flow through this rack [L/min]
            dt: Timestep [seconds]
        """
        self.inlet_coolant_temp_c = coolant_supply_temp
        
        # Coolant mass flow [kg/s] (density ~1030 kg/m³ for glycol mix)
        flow_kg_s = coolant_flow_lpm * 1.03 / 60.0
        
        # Specific heat of propylene glycol/water mix [kJ/(kg·°C)]
        cp = 3.8
        
        # Heat absorbed by coolant [kW]
        if flow_kg_s > 0.01:
            # Delta-T across rack = Q / (m_dot * Cp)
            delta_t = self.power_kw / (flow_kg_s * cp)
            self.outlet_coolant_temp_c = coolant_supply_temp + delta_t
        else:
            # No flow — temperature rises uncontrolled
            delta_t = 0.0
            self.outlet_coolant_temp_c = coolant_supply_temp
            # Thermal mass absorbs heat
            self.junction_temp_c += (self.power_kw / self.thermal_mass_kj_per_c) * dt
            return
        
        # GPU junction temperature = coolant avg + thermal resistance * power
        coolant_avg = (self.inlet_coolant_temp_c + self.outlet_coolant_temp_c) / 2.0
        target_junction = coolant_avg + self.thermal_resistance * self.power_kw
        
        # First-order lag on junction temperature (thermal inertia)
        tau = self.thermal_mass_kj_per_c / (flow_kg_s * cp) if flow_kg_s > 0.01 else 60.0
        alpha = dt / (tau + dt)
        self.junction_temp_c += alpha * (target_junction - self.junction_temp_c)


@dataclass 
class CDUModel:
    """
    Coolant Distribution Unit — heat exchanger + pump + valve.
    
    Primary side: facility water (from cooling tower)
    Secondary side: rack coolant (propylene glycol/water)
    
    The 3-way valve controls how much heat is rejected to facility water.
    The pump controls flow rate through the racks.
    """
    cdu_id: int = 1
    
    # Heat exchanger properties
    max_capacity_kw: float = 500.0
    effectiveness: float = 0.85  # Heat exchanger effectiveness (0-1)
    
    # Pump properties
    max_flow_lpm: float = 600.0
    min_flow_lpm: float = 60.0  # Minimum at 20% speed
    
    # Thermal mass (coolant volume in pipes)
    coolant_volume_liters: float = 200.0
    thermal_mass_kj_per_c: float = 600.0  # 200L * ~3.0 kJ/(L·°C)
    
    # State
    supply_temp_c: float = field(default=35.0, init=False)
    return_temp_c: float = field(default=45.0, init=False)
    flow_lpm: float = field(default=300.0, init=False)
    diff_pressure_bar: float = field(default=3.0, init=False)
    pump_speed_pct: float = field(default=50.0, init=False)
    valve_position_pct: float = field(default=50.0, init=False)
    facility_water_temp: float = field(default=28.0, init=False)
    
    # Calculated
    cooling_power_kw: float = field(default=0.0, init=False)
    delta_t: float = field(default=10.0, init=False)
    
    def set_pump_speed(self, speed_pct: float):
        """Set pump speed command (0-100%). Flow follows affinity law."""
        self.pump_speed_pct = max(0.0, min(100.0, speed_pct))
        # Affinity law: flow ∝ speed (approximately linear for this range)
        self.flow_lpm = self.min_flow_lpm + (self.max_flow_lpm - self.min_flow_lpm) * (self.pump_speed_pct / 100.0)
        # Pressure ∝ speed² (affinity law)
        self.diff_pressure_bar = 1.0 + 5.0 * (self.pump_speed_pct / 100.0) ** 2

    def set_valve_position(self, position_pct: float):
        """Set 3-way valve position (0% = full bypass, 100% = full process)."""
        self.valve_position_pct = max(0.0, min(100.0, position_pct))

    def update(self, rack_return_temp: float, facility_water_temp: float, dt: float):
        """
        Update CDU thermal state for one timestep.
        
        Args:
            rack_return_temp: Average return temperature from racks [°C]
            facility_water_temp: Facility water supply temperature [°C]
            dt: Timestep [seconds]
        """
        self.facility_water_temp = facility_water_temp
        self.return_temp_c = rack_return_temp
        
        # Heat exchanger: supply temp depends on valve position
        # At 100% valve: full heat rejection to facility water
        # At 0% valve: bypass (supply = return, no cooling)
        valve_fraction = self.valve_position_pct / 100.0
        
        # Effectiveness-NTU model (simplified)
        max_cooling = self.effectiveness * (rack_return_temp - facility_water_temp) * valve_fraction
        
        # Target supply temperature
        target_supply = rack_return_temp - max_cooling
        target_supply = max(facility_water_temp, target_supply)  # Can't go below facility water
        
        # Thermal inertia on supply temperature
        tau = self.thermal_mass_kj_per_c / (self.flow_lpm * 1.03 * 3.8 / 60.0) if self.flow_lpm > 1 else 30.0
        alpha = dt / (tau + dt)
        self.supply_temp_c += alpha * (target_supply - self.supply_temp_c)
        
        # Calculate actual cooling power
        flow_kg_s = self.flow_lpm * 1.03 / 60.0
        self.delta_t = self.return_temp_c - self.supply_temp_c
        self.cooling_power_kw = flow_kg_s * 3.8 * max(0, self.delta_t)


@dataclass
class CoolingTower:
    """
    Cooling tower / dry cooler — rejects heat to atmosphere.
    Provides facility water at a temperature dependent on ambient.
    """
    max_capacity_kw: float = 2000.0
    fan_speed_pct: float = 50.0
    
    # Ambient conditions
    ambient_temp_c: float = 25.0
    wet_bulb_temp_c: float = 20.0
    
    # Output
    supply_temp_c: float = field(default=28.0, init=False)
    
    def set_ambient(self, dry_bulb: float, wet_bulb: float):
        """Set ambient conditions."""
        self.ambient_temp_c = dry_bulb
        self.wet_bulb_temp_c = wet_bulb
    
    def update(self, heat_load_kw: float, dt: float):
        """Update facility water temperature based on heat load and ambient."""
        # Approach temperature: how close supply gets to wet bulb
        # At 100% fan: approach = 3°C. At 0% fan: approach = 15°C
        fan_fraction = self.fan_speed_pct / 100.0
        approach = 15.0 - 12.0 * fan_fraction  # 3-15°C range
        
        target_supply = self.wet_bulb_temp_c + approach
        
        # If heat load exceeds capacity, temperature rises
        if heat_load_kw > self.max_capacity_kw * fan_fraction:
            overload = (heat_load_kw - self.max_capacity_kw * fan_fraction) / 100.0
            target_supply += overload
        
        # Lag (large water volume)
        tau = 60.0  # 60 second time constant
        alpha = dt / (tau + dt)
        self.supply_temp_c += alpha * (target_supply - self.supply_temp_c)
