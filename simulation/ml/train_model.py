"""
ML Training — Predictive Cooling Model
=========================================
Trains a Random Forest model to predict supply temperature 60 seconds
in the future based on current plant state.

Input features:
  - GPU total power (kW)
  - Ambient temperature (°C)
  - Current pump speed (%)
  - Current valve position (%)

Target:
  - Supply temperature 60 seconds in the future

Training data is generated from multiple closed-loop simulation scenarios.

Usage:
  python simulation/ml/train_model.py

Output:
  simulation/ml/models/cooling_predictor.pkl
"""

import json
import os
import sys
import pickle
import numpy as np
from typing import Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tests', 'python'))


def generate_training_data(scenarios: list[str] = None,
                           duration_s: float = 180.0) -> tuple:
    """
    Generate training data by running closed-loop simulations.
    
    Returns:
        (X, y) — feature matrix and target vector
    """
    from simulation.plant_model.simulator import PlantSimulator, SimulatorConfig
    from codesys_logic.fb_pid import PIDController
    from codesys_logic.fb_sensor_validator import SensorValidator

    if scenarios is None:
        scenarios = ['training_ramp', 'burst', 'steady']

    all_records = []

    for scenario in scenarios:
        print(f"  Generating data for scenario: {scenario}...")

        config = SimulatorConfig(
            dt=0.01, num_racks=4, num_cdus=2,
            ambient_temp_c=25.0, wet_bulb_temp_c=20.0,
        )
        plant = PlantSimulator(config)
        for cdu in plant.cdus:
            cdu.max_flow_lpm = 800.0
            cdu.effectiveness = 0.90

        # Controller
        pid_pump = PIDController(
            kp=3.0, ti=20.0, td=0.0,
            output_min=20.0, output_max=100.0,
            rate_limit=10.0, deadband=0.3,
            cycle_time_s=0.05, safe_output=50.0,
        )
        pid_pump.enable()

        pid_valve = PIDController(
            kp=5.0, ti=15.0, td=2.0,
            output_min=10.0, output_max=100.0,
            rate_limit=20.0, deadband=0.5,
            cycle_time_s=0.05, safe_output=80.0,
        )
        pid_valve.enable()

        sv_supply = SensorValidator(
            range_low=-10, range_high=80, max_rate_of_change=5.0,
            fallback_value=35.0, filter_time_const=0.5, cycle_time_s=0.05,
        )
        sv_supply.enable()

        supply_temp_sp = 35.0
        ff_gain = 0.08
        ff_baseline_kw = 50.0
        pump_cmd = 50.0
        valve_cmd = 50.0

        steps = int(duration_s / config.dt)
        control_interval = 5
        records = []

        for step in range(steps):
            t = step * config.dt
            plant._apply_scenario(scenario, t, duration_s)
            plant.step()

            if step % control_interval == 0:
                sensors = plant.get_sensor_data(0)
                validated_supply = sv_supply.execute(sensors['supply_temp'])

                gpu_power = sensors['gpu_total_power_kw']
                ff_output = max(0.0, min(60.0, (gpu_power - ff_baseline_kw) * ff_gain))
                pump_error = validated_supply - supply_temp_sp if sv_supply.valid else 0.0
                pump_pid_out = pid_pump.execute(setpoint=0.0, process_value=-pump_error)
                pump_cmd = min(100.0, max(20.0, pump_pid_out + ff_output))
                valve_error = validated_supply - supply_temp_sp if sv_supply.valid else 0.0
                valve_cmd = pid_valve.execute(setpoint=0.0, process_value=-valve_error)

                plant.set_control_output(0, pump_cmd, valve_cmd)
                plant.set_control_output(1, pump_cmd, valve_cmd)

            # Record every 1 second (every 100 steps)
            if step % 100 == 0:
                sensors = plant.get_sensor_data(0)
                records.append({
                    'time_s': round(t, 2),
                    'gpu_power_kw': sensors['gpu_total_power_kw'],
                    'ambient_temp_c': config.ambient_temp_c,
                    'pump_speed_pct': round(pump_cmd, 1),
                    'valve_position_pct': round(valve_cmd, 1),
                    'supply_temp_c': sensors['supply_temp'],
                })

        all_records.extend(records)

    # Build feature/target pairs
    # Target: supply temp 60 seconds in the future
    prediction_horizon_s = 60.0
    sample_interval_s = 1.0  # We record every 1s
    horizon_steps = int(prediction_horizon_s / sample_interval_s)

    X_list = []
    y_list = []

    for i in range(len(all_records) - horizon_steps):
        current = all_records[i]
        future = all_records[i + horizon_steps]

        # Only pair records from the same scenario run
        # (check time continuity)
        if future['time_s'] - current['time_s'] > prediction_horizon_s + 5:
            continue

        features = [
            current['gpu_power_kw'],
            current['ambient_temp_c'],
            current['pump_speed_pct'],
            current['valve_position_pct'],
        ]
        target = future['supply_temp_c']

        # Skip if supply temp is invalid sensor reading
        if target < -900 or current['supply_temp_c'] < -900:
            continue

        X_list.append(features)
        y_list.append(target)

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.float64)

    print(f"  Generated {len(X)} training samples from {len(all_records)} records")
    return X, y


def train_model(X: np.ndarray, y: np.ndarray, model_path: str) -> dict:
    """
    Train a Random Forest model and save to disk.
    
    Returns training metrics.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"  Training set: {len(X_train)} samples")
    print(f"  Test set:     {len(X_test)} samples")

    # Train Random Forest
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    metrics = {
        'train_mae': round(mean_absolute_error(y_train, y_pred_train), 4),
        'test_mae': round(mean_absolute_error(y_test, y_pred_test), 4),
        'train_r2': round(r2_score(y_train, y_pred_train), 4),
        'test_r2': round(r2_score(y_test, y_pred_test), 4),
        'feature_importance': {
            'gpu_power_kw': round(model.feature_importances_[0], 4),
            'ambient_temp_c': round(model.feature_importances_[1], 4),
            'pump_speed_pct': round(model.feature_importances_[2], 4),
            'valve_position_pct': round(model.feature_importances_[3], 4),
        },
        'n_samples': len(X),
        'prediction_horizon_s': 60,
    }

    # Save model
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    # Save metadata alongside
    meta_path = model_path.replace('.pkl', '_metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  Model saved to: {model_path}")
    print(f"  Metadata saved to: {meta_path}")

    return metrics


def main():
    """Train the predictive cooling model."""
    print("=" * 60)
    print("  Predictive Cooling Model — Training")
    print("=" * 60)
    print()

    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
    model_path = os.path.join(model_dir, 'cooling_predictor.pkl')

    # Generate training data
    print("Step 1: Generating training data from simulations...")
    X, y = generate_training_data(
        scenarios=['training_ramp', 'burst', 'steady'],
        duration_s=180.0,
    )

    if len(X) < 10:
        print("ERROR: Not enough training data generated")
        sys.exit(1)

    # Train model
    print("\nStep 2: Training Random Forest model...")
    metrics = train_model(X, y, model_path)

    # Print results
    print("\n" + "=" * 60)
    print("  Training Results")
    print("=" * 60)
    print(f"  Test MAE:  {metrics['test_mae']:.4f} °C")
    print(f"  Test R²:   {metrics['test_r2']:.4f}")
    print(f"  Train MAE: {metrics['train_mae']:.4f} °C")
    print(f"  Train R²:  {metrics['train_r2']:.4f}")
    print()
    print("  Feature Importance:")
    for feat, imp in metrics['feature_importance'].items():
        bar = "█" * int(imp * 40)
        print(f"    {feat:<20} {imp:.3f} {bar}")
    print()


if __name__ == "__main__":
    main()
