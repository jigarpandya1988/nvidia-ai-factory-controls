"""Quick test of the plant simulator."""
import sys
sys.path.insert(0, '.')

from simulation.plant_model.simulator import PlantSimulator, SimulatorConfig

config = SimulatorConfig(dt=0.01, num_racks=8, num_cdus=2)
sim = PlantSimulator(config)

# Run 60 seconds of training ramp
history = sim.run_standalone(duration_s=60.0, scenario='training_ramp')

print(f"Steps simulated: {len(history)}")
print()
print("=== t=0s (idle) ===")
h = history[0]
print(f"  GPU max temp:  {h['gpu_max_temp']} C")
print(f"  Supply temp:   {h['supply_temp']} C")
print(f"  GPU power:     {h['gpu_total_power_kw']} kW")
print()
print("=== t=30s (full load) ===")
h = history[300]
print(f"  GPU max temp:  {h['gpu_max_temp']} C")
print(f"  Supply temp:   {h['supply_temp']} C")
print(f"  GPU power:     {h['gpu_total_power_kw']} kW")
print(f"  Cooling:       {h['cooling_capacity_kw']} kW")
print(f"  Delta-T:       {h['delta_t']} C")
print()
print("=== t=60s (steady state) ===")
h = history[-1]
print(f"  GPU max temp:  {h['gpu_max_temp']} C")
print(f"  Supply temp:   {h['supply_temp']} C")
print(f"  GPU power:     {h['gpu_total_power_kw']} kW")
print(f"  Cooling:       {h['cooling_capacity_kw']} kW")
print(f"  Flow rate:     {h['flow_rate']} LPM")
print()

# Validate physics make sense
assert history[-1]['gpu_max_temp'] > 50, "GPU should heat up under full load"
assert history[-1]['gpu_max_temp'] < 120, "GPU should not overheat unrealistically"
assert history[-1]['supply_temp'] > 30, "Supply temp should be above ambient"
assert history[-1]['cooling_capacity_kw'] > 100, "Should be generating significant cooling"
print("ALL PHYSICS VALIDATIONS PASSED")
