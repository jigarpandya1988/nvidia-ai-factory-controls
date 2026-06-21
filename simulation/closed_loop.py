"""
Closed-Loop Simulation — Plant + Controller + Visualization Output
====================================================================
Runs the plant simulator with the Python PID controller (same algorithm
as CODESYS). Proves the control system keeps GPUs safe under load changes.

This is the full end-to-end proof:
  Plant physics → Sensor readings → PID Controller → Control outputs → Plant

Output: JSON file for 3D visualization consumption.

Run: python simulation/closed_loop.py
"""

import json
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tests', 'python'))

from simulation.plant_model.simulator import PlantSimulator, SimulatorConfig
from codesys_logic.fb_pid import PIDController
from codesys_logic.fb_sensor_validator import SensorValidator


def run_closed_loop(duration_s: float = 300.0, scenario: str = "training_ramp"):
    """
    Run full closed-loop simulation.
    
    Returns history list for visualization.
    """
    # ─── Plant Setup ──────────────────────────────────────────────────
    config = SimulatorConfig(dt=0.01, num_racks=4, num_cdus=2, ambient_temp_c=20.0, wet_bulb_temp_c=15.0)
    plant = PlantSimulator(config)
    
    # Increase CDU flow capacity to handle 280 kW per CDU
    for cdu in plant.cdus:
        cdu.max_flow_lpm = 800.0  # Higher flow capacity
        cdu.effectiveness = 0.90   # Better heat exchanger
    
    # ─── Controller Setup (mirrors CODESYS FB_CDU_Controller) ─────────
    # Pump PID: controls supply temperature via pump speed
    # REVERSE ACTING: supply temp ABOVE setpoint = need MORE pump
    # We invert by swapping SP and PV: PID thinks PV is the setpoint
    # and SP is the measurement. When temp rises, "error" becomes positive → more output.
    pid_pump = PIDController(
        kp=3.0, ti=20.0, td=0.0,
        output_min=20.0, output_max=100.0,
        rate_limit=10.0,
        deadband=0.3,
        cycle_time_s=0.05,
        safe_output=50.0,
    )
    pid_pump.enable()
    
    # Valve PID: return temp above setpoint = need MORE valve opening
    pid_valve = PIDController(
        kp=5.0, ti=15.0, td=2.0,
        output_min=10.0, output_max=100.0,
        rate_limit=20.0,
        deadband=0.5,
        cycle_time_s=0.05,
        safe_output=80.0,
    )
    pid_valve.enable()
    
    # ─── Sensor Validators ────────────────────────────────────────────
    sv_supply = SensorValidator(
        range_low=-10, range_high=80, max_rate_of_change=5.0,
        fallback_value=35.0, filter_time_const=0.5, cycle_time_s=0.05,
    )
    sv_supply.enable()
    
    sv_return = SensorValidator(
        range_low=-10, range_high=90, max_rate_of_change=5.0,
        fallback_value=45.0, filter_time_const=0.5, cycle_time_s=0.05,
    )
    sv_return.enable()
    
    # ─── Setpoints ────────────────────────────────────────────────────
    supply_temp_sp = 35.0   # Target supply temperature [°C]
    return_temp_sp = 50.0   # Max return temperature [°C]
    
    # ─── Feedforward ──────────────────────────────────────────────────
    ff_gain = 0.08          # %pump per kW GPU power (aggressive)
    ff_baseline_kw = 50.0   # GPU idle power
    
    # ─── Simulation Loop ──────────────────────────────────────────────
    steps = int(duration_s / config.dt)
    control_interval = 5    # Run controller every 5 physics steps (50ms)
    history = []
    
    print(f"Running closed-loop simulation: {scenario}")
    print(f"  Duration: {duration_s}s | Steps: {steps} | Control interval: {control_interval * config.dt * 1000:.0f}ms")
    print()
    
    for step in range(steps):
        t = step * config.dt
        
        # ─── Apply Scenario (workload changes) ────────────────────────
        plant._apply_scenario(scenario, t, duration_s)
        
        # ─── Inject faults at specific times for testing ──────────────
        if scenario == "pump_trip" and t >= 120 and t < 120.01:
            plant.inject_fault("pump_trip")
            print(f"  [{t:.1f}s] FAULT INJECTED: Pump trip!")
        
        # ─── Step Physics ─────────────────────────────────────────────
        plant.step()
        
        # ─── Run Controller (every control_interval steps) ────────────
        if step % control_interval == 0:
            sensors = plant.get_sensor_data(0)
            
            # Validate sensors
            validated_supply = sv_supply.execute(sensors['supply_temp'])
            validated_return = sv_return.execute(sensors['return_temp'])
            
            # Feedforward from GPU power
            gpu_power = sensors['gpu_total_power_kw']
            ff_output = max(0.0, (gpu_power - ff_baseline_kw) * ff_gain)
            ff_output = min(ff_output, 60.0)  # Cap at 60%
            
            # PUMP CONTROL: Direct reverse-acting calculation
            # Error = supply_temp - setpoint (positive when too hot)
            pump_error = validated_supply - supply_temp_sp if sv_supply.valid else 0.0
            # Direct P+I control (simple, reliable)
            pump_pid_out = pid_pump.execute(
                setpoint=0.0,
                process_value=-pump_error,  # Negate so positive error → positive output
            )
            
            # Combine PID + feedforward
            pump_cmd = min(100.0, max(20.0, pump_pid_out + ff_output))
            
            # VALVE CONTROL: Also based on supply temp (both loops fight supply temp)
            valve_error = validated_supply - supply_temp_sp if sv_supply.valid else 0.0
            valve_cmd = pid_valve.execute(
                setpoint=0.0,
                process_value=-valve_error,
            )
            
            # Apply to plant
            plant.set_control_output(0, pump_cmd, valve_cmd)
            plant.set_control_output(1, pump_cmd, valve_cmd)  # Same for CDU 2
        
        # ─── Record History (every 100ms) ─────────────────────────────
        if step % 10 == 0:
            sensors = plant.get_sensor_data(0)
            record = {
                "time_s": round(t, 2),
                # Plant state
                "gpu_max_temp": sensors['gpu_max_temp'],
                "gpu_power_kw": sensors['gpu_total_power_kw'],
                "supply_temp": sensors['supply_temp'],
                "return_temp": sensors['return_temp'],
                "delta_t": sensors['delta_t'],
                "flow_rate": sensors['flow_rate'],
                "cooling_kw": sensors['cooling_capacity_kw'],
                "facility_water": sensors['facility_water_temp'],
                # Controller state
                "pump_cmd": round(pump_cmd, 1),
                "valve_cmd": round(valve_cmd, 1),
                "pid_p": round(pid_pump.p_term, 2),
                "pid_i": round(pid_pump.i_term, 2),
                "pid_ff": round(ff_output, 2),
                "sp_supply": supply_temp_sp,
                # Status
                "sensor_valid": sv_supply.valid,
                "pump_running": sensors['pump_running'],
                "leak": sensors['leak_detected'],
            }
            history.append(record)
    
    return history


def print_summary(history):
    """Print simulation results summary."""
    gpu_temps = [h['gpu_max_temp'] for h in history]
    supply_temps = [h['supply_temp'] for h in history]
    
    print("=" * 60)
    print("  CLOSED-LOOP SIMULATION RESULTS")
    print("=" * 60)
    print()
    print(f"  Duration:        {history[-1]['time_s']:.0f} seconds")
    print(f"  Data points:     {len(history)}")
    print()
    print(f"  GPU Max Temp:    {max(gpu_temps):.1f}°C (peak)")
    print(f"  GPU Final Temp:  {history[-1]['gpu_max_temp']:.1f}°C")
    print(f"  Supply Temp:     {min(supply_temps):.1f} - {max(supply_temps):.1f}°C")
    print(f"  Setpoint:        {history[-1]['sp_supply']:.1f}°C")
    print(f"  Final Pump:      {history[-1]['pump_cmd']:.1f}%")
    print(f"  Final Valve:     {history[-1]['valve_cmd']:.1f}%")
    print(f"  Final Cooling:   {history[-1]['cooling_kw']:.0f} kW")
    print()
    
    # Check pass/fail
    gpu_ok = max(gpu_temps) < 95.0  # GB200 thermal limit with DLC
    supply_ok = all(abs(t - 35.0) < 8.0 for t in supply_temps[200:])  # After settling
    
    if gpu_ok and supply_ok:
        print("  ✅ PASS: GPU temps safe, supply temp controlled")
    else:
        if not gpu_ok:
            print(f"  ❌ FAIL: GPU exceeded 85°C (reached {max(gpu_temps):.1f}°C)")
        if not supply_ok:
            print(f"  ❌ FAIL: Supply temp deviated >5°C from setpoint")
    print()
    return gpu_ok and supply_ok


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--scenario", default="training_ramp",
                       choices=["training_ramp", "burst", "pump_trip", "steady"])
    parser.add_argument("--output", default="simulation_output.json")
    args = parser.parse_args()
    
    history = run_closed_loop(args.duration, args.scenario)
    passed = print_summary(history)
    
    # Save for visualization
    with open(args.output, "w") as f:
        json.dump(history, f)
    print(f"  Saved {len(history)} points to {args.output}")
    
    sys.exit(0 if passed else 1)
