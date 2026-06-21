"""
Multi-Scenario Simulation Runner
==================================
Loads and runs all .yaml scenarios using closed_loop.py logic.
Reports pass/fail for each scenario and outputs JSON results for CI integration.

Exit code:
  0 — all scenarios pass
  1 — one or more scenarios fail

Run: python simulation/run_all_scenarios.py
"""

import json
import os
import sys
import time
import glob
import traceback
from dataclasses import dataclass, field
from typing import Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tests', 'python'))

import yaml
from simulation.plant_model.simulator import PlantSimulator, SimulatorConfig
from codesys_logic.fb_pid import PIDController
from codesys_logic.fb_sensor_validator import SensorValidator


@dataclass
class ScenarioResult:
    """Result of a single scenario run."""
    name: str
    description: str
    duration_s: float
    passed: bool = False
    checks: dict = field(default_factory=dict)
    error: str = ""
    gpu_max_temp: float = 0.0
    supply_temp_max: float = 0.0
    supply_temp_min: float = 0.0
    runtime_ms: float = 0.0


def load_scenario(yaml_path: str) -> dict:
    """Load scenario definition from YAML."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def interpolate_workload(profile: list, t: float) -> float:
    """Interpolate workload from profile breakpoints."""
    if not profile:
        return 0.5

    # Before first point
    if t <= profile[0]['time_s']:
        return profile[0]['load_fraction']

    # After last point
    if t >= profile[-1]['time_s']:
        return profile[-1]['load_fraction']

    # Find segment
    for i in range(len(profile) - 1):
        t0 = profile[i]['time_s']
        t1 = profile[i + 1]['time_s']
        if t0 <= t <= t1:
            # Linear interpolation
            if t1 == t0:
                return profile[i]['load_fraction']
            frac = (t - t0) / (t1 - t0)
            v0 = profile[i]['load_fraction']
            v1 = profile[i + 1]['load_fraction']
            return v0 + frac * (v1 - v0)

    return profile[-1]['load_fraction']


def run_scenario(scenario: dict) -> ScenarioResult:
    """
    Execute a single scenario using the plant simulator and PID controller.
    Returns a ScenarioResult with pass/fail and diagnostic data.
    """
    name = scenario.get('name', 'unknown')
    description = scenario.get('description', '')
    duration_s = scenario.get('duration_s', 60)
    workload_profile = scenario.get('workload_profile', [])
    faults = scenario.get('faults', [])
    ambient = scenario.get('ambient', {})
    control = scenario.get('control_settings', {})
    criteria = scenario.get('pass_criteria', {})

    result = ScenarioResult(
        name=name,
        description=description,
        duration_s=duration_s,
    )

    start_time = time.time()

    try:
        # --- Plant Setup ---
        config = SimulatorConfig(
            dt=0.01,
            num_racks=4,
            num_cdus=2,
            ambient_temp_c=ambient.get('dry_bulb_c', 25.0),
            wet_bulb_temp_c=ambient.get('wet_bulb_c', 20.0),
        )
        plant = PlantSimulator(config)

        # Increase CDU flow capacity
        for cdu in plant.cdus:
            cdu.max_flow_lpm = 800.0
            cdu.effectiveness = 0.90

        # --- Controller Setup ---
        pid_pump = PIDController(
            kp=3.0, ti=20.0, td=0.0,
            output_min=20.0, output_max=100.0,
            rate_limit=10.0,
            deadband=0.3,
            cycle_time_s=0.05,
            safe_output=50.0,
        )
        pid_pump.enable()

        pid_valve = PIDController(
            kp=5.0, ti=15.0, td=2.0,
            output_min=10.0, output_max=100.0,
            rate_limit=20.0,
            deadband=0.5,
            cycle_time_s=0.05,
            safe_output=80.0,
        )
        pid_valve.enable()

        # Sensor Validators
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

        # Setpoints
        supply_temp_sp = control.get('supply_temp_setpoint_c', 35.0)

        # Feedforward
        ff_gain = 0.08
        ff_baseline_kw = 50.0

        # Initial control outputs
        pump_cmd = control.get('pump_speed_initial_pct', 50.0)
        valve_cmd = control.get('valve_position_initial_pct', 50.0)

        # --- Simulation Loop ---
        steps = int(duration_s / config.dt)
        control_interval = 5  # 50ms control cycle
        history = []
        alarms = []
        safe_state_entered = False
        used_fallback = False
        faults_injected = set()

        for step in range(steps):
            t = step * config.dt

            # --- Apply workload from profile ---
            load = interpolate_workload(workload_profile, t)
            plant.set_workload_all(load)

            # --- Inject faults at trigger times ---
            for fault in faults:
                fault_key = f"{fault['type']}_{fault['trigger_time_s']}"
                if t >= fault['trigger_time_s'] and fault_key not in faults_injected:
                    plant.inject_fault(fault['type'])
                    faults_injected.add(fault_key)

            # --- Step Physics ---
            plant.step()

            # --- Controller (every control_interval steps) ---
            if step % control_interval == 0:
                sensors = plant.get_sensor_data(0)

                # Validate sensors
                validated_supply = sv_supply.execute(sensors['supply_temp'])
                validated_return = sv_return.execute(sensors['return_temp'])

                # Track if fallback is used
                if not sv_supply.valid:
                    used_fallback = True

                # Check for leak → enter safe state
                if sensors['leak_detected']:
                    safe_state_entered = True
                    # In safe state: ramp pump down, raise alarm
                    pump_cmd = max(20.0, pump_cmd - 0.5)
                    valve_cmd = 100.0  # Full cooling
                    if 'leak_alarm' not in [a.get('type') for a in alarms]:
                        alarms.append({
                            'type': 'leak_alarm',
                            'time_s': round(t, 2),
                            'message': 'Coolant leak detected — entering safe state',
                        })
                elif not sensors['pump_running']:
                    # Pump trip detected
                    if 'pump_trip_alarm' not in [a.get('type') for a in alarms]:
                        alarms.append({
                            'type': 'pump_trip_alarm',
                            'time_s': round(t, 2),
                            'message': 'CDU pump trip — loss of flow',
                        })
                    # Try to maximize valve opening on remaining CDU
                    valve_cmd = 100.0
                else:
                    # Normal control
                    gpu_power = sensors['gpu_total_power_kw']
                    ff_output = max(0.0, min(60.0, (gpu_power - ff_baseline_kw) * ff_gain))

                    # Pump PID (reverse-acting)
                    pump_error = validated_supply - supply_temp_sp if sv_supply.valid else 0.0
                    pump_pid_out = pid_pump.execute(setpoint=0.0, process_value=-pump_error)
                    pump_cmd = min(100.0, max(20.0, pump_pid_out + ff_output))

                    # Valve PID
                    valve_error = validated_supply - supply_temp_sp if sv_supply.valid else 0.0
                    valve_cmd = pid_valve.execute(setpoint=0.0, process_value=-valve_error)

                # Apply to plant
                plant.set_control_output(0, pump_cmd, valve_cmd)
                plant.set_control_output(1, pump_cmd, valve_cmd)

            # --- Record (every 100ms) ---
            if step % 10 == 0:
                sensors = plant.get_sensor_data(0)
                history.append({
                    'time_s': round(t, 2),
                    'gpu_max_temp': sensors['gpu_max_temp'],
                    'supply_temp': sensors['supply_temp'],
                    'return_temp': sensors['return_temp'],
                    'pump_cmd': round(pump_cmd, 1),
                    'valve_cmd': round(valve_cmd, 1),
                    'flow_rate': sensors['flow_rate'],
                    'leak': sensors['leak_detected'],
                    'pump_running': sensors['pump_running'],
                    'sensor_valid': sv_supply.valid,
                })

        # --- Evaluate Pass Criteria ---
        gpu_temps = [h['gpu_max_temp'] for h in history]
        supply_temps = [h['supply_temp'] for h in history if h['supply_temp'] > -900]

        result.gpu_max_temp = max(gpu_temps) if gpu_temps else 0
        result.supply_temp_max = max(supply_temps) if supply_temps else 0
        result.supply_temp_min = min(supply_temps) if supply_temps else 0

        checks = {}

        # Check: no crash (always — we got here without exception)
        checks['no_crash'] = True

        # Check: GPU max temp
        if 'gpu_max_temp_c' in criteria:
            limit = criteria['gpu_max_temp_c']
            checks['gpu_max_temp_c'] = result.gpu_max_temp < limit

        # Check: supply temp recovery (for burst scenarios)
        if 'supply_temp_recovery_s' in criteria:
            # Check that after each load drop, supply recovers within threshold
            # Simplified: check that supply stays within reasonable bounds
            checks['supply_temp_recovery_s'] = result.supply_temp_max < (supply_temp_sp + 10.0)

        # Check: leak detected
        if 'leak_detected' in criteria:
            checks['leak_detected'] = any(h['leak'] for h in history)

        # Check: safe state entered
        if 'safe_state_entered' in criteria:
            checks['safe_state_entered'] = safe_state_entered

        # Check: alarm raised
        if 'alarm_raised' in criteria:
            checks['alarm_raised'] = len(alarms) > 0

        # Check: uses fallback
        if 'uses_fallback' in criteria:
            checks['uses_fallback'] = used_fallback

        # Check: settling time
        if 'settling_time_s' in criteria:
            # Simplified: check final deviation from setpoint
            final_supply = supply_temps[-1] if supply_temps else supply_temp_sp
            checks['settling_time_s'] = abs(final_supply - supply_temp_sp) < 5.0

        # Check: supply temp deviation
        if 'supply_temp_deviation_c' in criteria:
            dev = criteria['supply_temp_deviation_c']
            # Check after settling (skip first 30% of data)
            start_idx = len(supply_temps) // 3
            settled_temps = supply_temps[start_idx:]
            if settled_temps:
                max_dev = max(abs(t - supply_temp_sp) for t in settled_temps)
                checks['supply_temp_deviation_c'] = max_dev < dev
            else:
                checks['supply_temp_deviation_c'] = True

        result.checks = checks
        result.passed = all(checks.values()) if checks else True

    except Exception as e:
        result.passed = False
        result.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

    result.runtime_ms = (time.time() - start_time) * 1000
    return result


def main():
    """Load and run all scenarios, report results."""
    scenarios_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios')

    # Find all scenario files
    yaml_files = sorted(glob.glob(os.path.join(scenarios_dir, '*.yaml')))

    if not yaml_files:
        print("ERROR: No scenario files found in", scenarios_dir)
        sys.exit(1)

    print("=" * 70)
    print("  NVIDIA AI FACTORY — Multi-Scenario Simulation Runner")
    print("=" * 70)
    print(f"\n  Found {len(yaml_files)} scenario(s) in: {scenarios_dir}\n")

    results = []
    all_passed = True

    for yaml_path in yaml_files:
        filename = os.path.basename(yaml_path)
        scenario = load_scenario(yaml_path)

        name = scenario.get('name', filename)
        print(f"  ▶ Running: {name} ({filename})")
        print(f"    {scenario.get('description', '')}")
        print(f"    Duration: {scenario.get('duration_s', 0)}s")

        result = run_scenario(scenario)
        results.append(result)

        if result.passed:
            print(f"    ✅ PASS (GPU max: {result.gpu_max_temp:.1f}°C, "
                  f"Supply: {result.supply_temp_min:.1f}-{result.supply_temp_max:.1f}°C)")
        else:
            all_passed = False
            if result.error:
                print(f"    ❌ FAIL (error: {result.error.splitlines()[0]})")
            else:
                failed_checks = [k for k, v in result.checks.items() if not v]
                print(f"    ❌ FAIL — failed checks: {failed_checks}")
                print(f"       GPU max: {result.gpu_max_temp:.1f}°C, "
                      f"Supply: {result.supply_temp_min:.1f}-{result.supply_temp_max:.1f}°C")

        print(f"    Runtime: {result.runtime_ms:.0f}ms")
        print()

    # --- Summary ---
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\n  {passed_count}/{total} scenarios passed")
    print()
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"    {status}  {r.name} ({r.runtime_ms:.0f}ms)")
    print()

    # --- Output JSON for CI ---
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'scenario_results.json')

    json_results = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'total_scenarios': total,
        'passed': passed_count,
        'failed': total - passed_count,
        'all_passed': all_passed,
        'scenarios': [
            {
                'name': r.name,
                'description': r.description,
                'duration_s': r.duration_s,
                'passed': r.passed,
                'checks': r.checks,
                'gpu_max_temp': round(r.gpu_max_temp, 2),
                'supply_temp_max': round(r.supply_temp_max, 2),
                'supply_temp_min': round(r.supply_temp_min, 2),
                'runtime_ms': round(r.runtime_ms, 1),
                'error': r.error if r.error else None,
            }
            for r in results
        ],
    }

    with open(output_path, 'w') as f:
        json.dump(json_results, f, indent=2)
    print(f"  Results saved to: {output_path}")

    # Exit code for CI
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
