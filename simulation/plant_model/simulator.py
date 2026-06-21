"""
Full Plant Simulator — Orchestrates All Physics Models
========================================================
Connects thermal models together and interfaces with NATS for
real-time data exchange with the control system.

Run standalone: python -m simulation.plant_model.simulator
Or with NATS: python -m simulation.plant_model.simulator --nats nats://localhost:4222

The simulator:
  1. Steps physics at 10ms (100 Hz)
  2. Publishes sensor values to NATS (simulating OPC UA bridge)
  3. Subscribes to control outputs from NATS (pump speed, valve pos)
  4. Supports fault injection (sensor fail, pump trip, leak)
  5. Supports workload scenarios (idle → ramp → training → burst)
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from .thermal import GPURack, CDUModel, CoolingTower

logger = logging.getLogger(__name__)


@dataclass
class SimulatorConfig:
    """Simulator configuration."""
    dt: float = 0.01              # Physics timestep [seconds] (100 Hz)
    nats_url: str = ""            # Empty = standalone (no NATS)
    site_id: str = "us-west-01"
    num_racks: int = 8            # GPU racks per CDU
    num_cdus: int = 2             # CDU units
    publish_rate_hz: float = 10.0 # NATS publish rate
    ambient_temp_c: float = 25.0
    wet_bulb_temp_c: float = 20.0


@dataclass
class FaultState:
    """Active fault injection state."""
    sensor_supply_temp_failed: bool = False
    sensor_return_temp_failed: bool = False
    sensor_flow_failed: bool = False
    pump_tripped: bool = False
    leak_active: bool = False
    leak_zone: int = 0
    power_loss: bool = False


class PlantSimulator:
    """
    Full plant simulation: GPU racks → CDU → Cooling Tower.
    
    Interfaces with control system via NATS (same subjects as real bridges).
    """

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.faults = FaultState()
        self._running = False
        self._sim_time = 0.0
        self._step_count = 0
        
        # Create physical models
        self.racks = [GPURack(rack_id=i+1) for i in range(config.num_racks)]
        self.cdus = [CDUModel(cdu_id=i+1) for i in range(config.num_cdus)]
        self.cooling_tower = CoolingTower(
            ambient_temp_c=config.ambient_temp_c,
            wet_bulb_temp_c=config.wet_bulb_temp_c,
        )
        
        # Control inputs (from NATS or manual)
        self._pump_speed = [50.0] * config.num_cdus
        self._valve_position = [50.0] * config.num_cdus
        self._workload = [0.3] * config.num_racks  # Start at 30% load
        
        # NATS connection
        self._nc = None
        self._js = None

    def step(self):
        """Advance simulation by one timestep."""
        dt = self.config.dt
        self._sim_time += dt
        self._step_count += 1
        
        # --- Apply control inputs to CDUs ---
        for i, cdu in enumerate(self.cdus):
            if self.faults.pump_tripped and i == 0:
                cdu.set_pump_speed(0.0)  # Pump tripped
            else:
                cdu.set_pump_speed(self._pump_speed[i])
            cdu.set_valve_position(self._valve_position[i])
        
        # --- Update GPU rack workloads ---
        for i, rack in enumerate(self.racks):
            rack.set_workload(self._workload[i])
        
        # --- Calculate rack return temperature (average of all racks per CDU) ---
        racks_per_cdu = self.config.num_racks // self.config.num_cdus
        
        for cdu_idx, cdu in enumerate(self.cdus):
            # Get racks served by this CDU
            start = cdu_idx * racks_per_cdu
            end = start + racks_per_cdu
            my_racks = self.racks[start:end]
            
            # Update each rack with CDU supply temperature
            flow_per_rack = cdu.flow_lpm / racks_per_cdu if racks_per_cdu > 0 else 0
            for rack in my_racks:
                rack.update(cdu.supply_temp_c, flow_per_rack, dt)
            
            # Average return temperature from racks
            if my_racks:
                avg_return = sum(r.outlet_coolant_temp_c for r in my_racks) / len(my_racks)
            else:
                avg_return = cdu.supply_temp_c
            
            # Update CDU with rack return and facility water
            cdu.update(avg_return, self.cooling_tower.supply_temp_c, dt)
        
        # --- Update cooling tower with total heat load ---
        total_heat = sum(cdu.cooling_power_kw for cdu in self.cdus)
        self.cooling_tower.update(total_heat, dt)

    def get_sensor_data(self, cdu_idx: int = 0) -> dict:
        """Get current sensor values (what the OPC UA bridge would read)."""
        cdu = self.cdus[cdu_idx]
        racks_per_cdu = self.config.num_racks // self.config.num_cdus
        start = cdu_idx * racks_per_cdu
        my_racks = self.racks[start:start + racks_per_cdu]
        
        supply_temp = cdu.supply_temp_c
        return_temp = cdu.return_temp_c
        flow_rate = cdu.flow_lpm
        pressure = cdu.diff_pressure_bar
        
        # Apply sensor faults
        if self.faults.sensor_supply_temp_failed:
            supply_temp = -999.0  # Out of range (sensor failure)
        if self.faults.sensor_return_temp_failed:
            return_temp = -999.0
        if self.faults.sensor_flow_failed:
            flow_rate = -999.0
        
        # Add realistic noise
        import random
        noise = lambda scale: random.gauss(0, scale)
        if supply_temp > -900:
            supply_temp += noise(0.1)
        if return_temp > -900:
            return_temp += noise(0.1)
        if flow_rate > -900:
            flow_rate += noise(2.0)
        pressure += noise(0.05)
        
        gpu_max_temp = max(r.junction_temp_c for r in my_racks) if my_racks else 0
        gpu_total_power = sum(r.power_kw for r in my_racks)
        
        return {
            "supply_temp": round(supply_temp, 2),
            "return_temp": round(return_temp, 2),
            "flow_rate": round(flow_rate, 1),
            "diff_pressure": round(pressure, 3),
            "delta_t": round(cdu.delta_t, 2),
            "cooling_capacity_kw": round(cdu.cooling_power_kw, 1),
            "pump_speed": round(cdu.pump_speed_pct, 1),
            "valve_position": round(cdu.valve_position_pct, 1),
            "gpu_max_temp": round(gpu_max_temp, 1),
            "gpu_total_power_kw": round(gpu_total_power, 1),
            "facility_water_temp": round(self.cooling_tower.supply_temp_c, 1),
            "leak_detected": self.faults.leak_active,
            "pump_running": not self.faults.pump_tripped and self._pump_speed[cdu_idx] > 5,
            "sim_time_s": round(self._sim_time, 2),
        }

    def set_control_output(self, cdu_idx: int, pump_speed: float, valve_position: float):
        """Apply control outputs (from NATS command or manual)."""
        if 0 <= cdu_idx < self.config.num_cdus:
            self._pump_speed[cdu_idx] = pump_speed
            self._valve_position[cdu_idx] = valve_position

    def set_workload_all(self, fraction: float):
        """Set all racks to same workload fraction (0-1)."""
        self._workload = [fraction] * self.config.num_racks

    def set_workload_profile(self, profile: list[float]):
        """Set individual rack workloads (list of fractions)."""
        for i, w in enumerate(profile[:self.config.num_racks]):
            self._workload[i] = w

    def inject_fault(self, fault_type: str, **kwargs):
        """Inject a fault for testing."""
        if fault_type == "sensor_supply":
            self.faults.sensor_supply_temp_failed = True
        elif fault_type == "sensor_return":
            self.faults.sensor_return_temp_failed = True
        elif fault_type == "sensor_flow":
            self.faults.sensor_flow_failed = True
        elif fault_type == "pump_trip":
            self.faults.pump_tripped = True
        elif fault_type == "leak":
            self.faults.leak_active = True
            self.faults.leak_zone = kwargs.get("zone", 1)
        elif fault_type == "power_loss":
            self.faults.power_loss = True
        elif fault_type == "clear_all":
            self.faults = FaultState()

    async def run_with_nats(self):
        """Run simulator with NATS connectivity (full loop)."""
        import nats as nats_lib
        
        self._running = True
        self._nc = await nats_lib.connect(self.config.nats_url, name="plant-simulator")
        logger.info(f"Plant simulator connected to NATS: {self.config.nats_url}")
        
        # Subscribe to control outputs
        await self._nc.subscribe(
            f"aifactory.{self.config.site_id}.cooling.peer",
            cb=self._on_control_output,
        )
        
        publish_interval = 1.0 / self.config.publish_rate_hz
        last_publish = 0.0
        
        while self._running:
            # Step physics
            self.step()
            
            # Publish at configured rate
            if self._sim_time - last_publish >= publish_interval:
                last_publish = self._sim_time
                await self._publish_sensors()
            
            # Real-time pacing (1:1 with wall clock)
            await asyncio.sleep(self.config.dt)

    async def _publish_sensors(self):
        """Publish sensor data to NATS (simulates what OPC UA bridge would do)."""
        for i in range(self.config.num_cdus):
            data = self.get_sensor_data(i)
            subject = f"aifactory.{self.config.site_id}.sim.telemetry.CDU_{i+1:02d}"
            await self._nc.publish(subject, json.dumps(data).encode())

    async def _on_control_output(self, msg):
        """Receive control outputs from NATS (from control system)."""
        try:
            data = json.loads(msg.data)
            # Extract pump speed and valve position from peer data
            values = data.get("values", {})
            # Map to simulator inputs
            for key, val in values.items():
                if "PumpSpeed" in key:
                    self.set_control_output(0, val, self._valve_position[0])
                elif "ValvePos" in key:
                    self.set_control_output(0, self._pump_speed[0], val)
        except Exception as e:
            logger.warning(f"Control output parse error: {e}")

    async def stop(self):
        self._running = False
        if self._nc:
            await self._nc.close()

    def run_standalone(self, duration_s: float = 60.0, scenario: str = "training_ramp"):
        """Run simulation without NATS (for testing/plotting)."""
        steps = int(duration_s / self.config.dt)
        history = []
        
        for step in range(steps):
            # Apply scenario
            t = step * self.config.dt
            self._apply_scenario(scenario, t, duration_s)
            
            # Step physics
            self.step()
            
            # Record every 100ms (every 10 steps at 10ms dt)
            if step % 10 == 0:
                data = self.get_sensor_data(0)
                data["time_s"] = t
                history.append(data)
        
        return history

    def _apply_scenario(self, scenario: str, t: float, duration: float):
        """Apply workload scenario based on time."""
        if scenario == "training_ramp":
            # 0-10s: idle, 10-30s: ramp to 100%, 30+: hold at 100%
            if t < 10:
                self.set_workload_all(0.1)
            elif t < 30:
                frac = (t - 10) / 20.0
                self.set_workload_all(0.1 + 0.9 * frac)
            else:
                self.set_workload_all(1.0)
        
        elif scenario == "burst":
            # Periodic bursts: 80% for 10s, then 30% for 10s
            cycle = t % 20.0
            if cycle < 10:
                self.set_workload_all(0.8)
            else:
                self.set_workload_all(0.3)
        
        elif scenario == "pump_trip":
            # Normal for 20s, then pump trips
            if t < 20:
                self.set_workload_all(0.7)
            else:
                self.inject_fault("pump_trip")
        
        elif scenario == "steady":
            self.set_workload_all(0.7)


# =============================================================================
# Entry Point
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Factory Plant Simulator")
    parser.add_argument("--nats", default="", help="NATS URL (empty = standalone)")
    parser.add_argument("--duration", type=float, default=120.0, help="Simulation duration [s]")
    parser.add_argument("--scenario", default="training_ramp", 
                       choices=["training_ramp", "burst", "pump_trip", "steady"],
                       help="Workload scenario")
    args = parser.parse_args()
    
    config = SimulatorConfig(nats_url=args.nats)
    sim = PlantSimulator(config)
    
    if args.nats:
        # Real-time with NATS
        logger.info("Starting real-time simulation with NATS...")
        await sim.run_with_nats()
    else:
        # Standalone (runs fast, outputs history)
        logger.info(f"Running standalone simulation: {args.scenario} for {args.duration}s")
        history = sim.run_standalone(args.duration, args.scenario)
        
        # Print summary
        print(f"\nSimulation complete: {len(history)} data points")
        print(f"  Final GPU max temp: {history[-1]['gpu_max_temp']}°C")
        print(f"  Final supply temp:  {history[-1]['supply_temp']}°C")
        print(f"  Final delta-T:      {history[-1]['delta_t']}°C")
        print(f"  Final capacity:     {history[-1]['cooling_capacity_kw']} kW")
        
        # Save to JSON for visualization
        import json
        with open("simulation_output.json", "w") as f:
            json.dump(history, f, indent=2)
        print(f"\nSaved to simulation_output.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
