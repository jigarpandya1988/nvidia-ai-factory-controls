"""
Multi-Site Fleet Simulation
=============================
Spawns multiple plant simulators, each representing a different AI Factory site.
Each site publishes to unique NATS subject prefixes and has distinct ambient
conditions and load profiles — demonstrating multi-site scaling via NATS subjects.

Sites:
  - us-west-01: Hot/dry climate, high GPU density, burst workloads
  - us-east-01: Moderate climate, mixed workloads
  - eu-west-01: Cool/humid climate, steady training workloads

Run:
  python -m simulation.fleet.multi_site --nats nats://localhost:4222
  python -m simulation.fleet.multi_site --standalone --duration 120
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from simulation.plant_model.simulator import PlantSimulator, SimulatorConfig

logger = logging.getLogger(__name__)


@dataclass
class SiteProfile:
    """Configuration for a simulated AI Factory site."""
    site_id: str
    name: str
    ambient_temp_c: float
    wet_bulb_temp_c: float
    num_racks: int
    num_cdus: int
    workload_pattern: str  # "burst", "steady", "training_ramp", "mixed"
    load_offset: float = 0.0  # Phase offset for varied timing


# ─── Site Definitions ─────────────────────────────────────────────────────────

FLEET_SITES = [
    SiteProfile(
        site_id="us-west-01",
        name="US West (Phoenix, AZ)",
        ambient_temp_c=38.0,     # Hot desert climate
        wet_bulb_temp_c=22.0,
        num_racks=8,
        num_cdus=2,
        workload_pattern="burst",
        load_offset=0.0,
    ),
    SiteProfile(
        site_id="us-east-01",
        name="US East (Virginia)",
        ambient_temp_c=28.0,     # Moderate humid climate
        wet_bulb_temp_c=24.0,
        num_racks=8,
        num_cdus=2,
        workload_pattern="mixed",
        load_offset=5.0,
    ),
    SiteProfile(
        site_id="eu-west-01",
        name="EU West (Dublin, IE)",
        ambient_temp_c=15.0,     # Cool oceanic climate
        wet_bulb_temp_c=12.0,
        num_racks=8,
        num_cdus=2,
        workload_pattern="training_ramp",
        load_offset=10.0,
    ),
]


def compute_workload(pattern: str, t: float, offset: float = 0.0) -> float:
    """
    Compute workload fraction (0-1) for a given pattern and time.

    Patterns:
      burst         — periodic high/low cycles (inference serving)
      steady        — constant 70% load (always-on training)
      training_ramp — ramp from idle to full (large model training)
      mixed         — combination of ramp + periodic bursts
    """
    t_adj = t + offset  # Phase offset for site variation

    if pattern == "burst":
        # 15s at 85%, 10s at 25% — simulating inference request bursts
        cycle = t_adj % 25.0
        return 0.85 if cycle < 15.0 else 0.25

    elif pattern == "steady":
        # Constant 70% with small sinusoidal variation (±5%)
        import math
        return 0.70 + 0.05 * math.sin(t_adj * 0.1)

    elif pattern == "training_ramp":
        # 0-20s: idle (checkpoint load), 20-60s: ramp to 95%, 60+: hold
        if t_adj < 20.0:
            return 0.10
        elif t_adj < 60.0:
            frac = (t_adj - 20.0) / 40.0
            return 0.10 + 0.85 * frac
        else:
            return 0.95

    elif pattern == "mixed":
        # Ramp for first 30s, then alternate between high and medium
        if t_adj < 30.0:
            frac = t_adj / 30.0
            return 0.1 + 0.6 * frac
        else:
            cycle = (t_adj - 30.0) % 20.0
            return 0.80 if cycle < 12.0 else 0.50

    return 0.5  # fallback


class FleetSimulator:
    """
    Manages multiple PlantSimulator instances, each representing a site.
    Publishes all telemetry to NATS with site-specific subject prefixes.
    """

    def __init__(self, sites: list[SiteProfile], nats_url: str = ""):
        self.sites = sites
        self.nats_url = nats_url
        self.simulators: dict[str, PlantSimulator] = {}
        self._running = False

        # Create a simulator per site
        for site in sites:
            config = SimulatorConfig(
                nats_url=nats_url,
                site_id=site.site_id,
                num_racks=site.num_racks,
                num_cdus=site.num_cdus,
                ambient_temp_c=site.ambient_temp_c,
                wet_bulb_temp_c=site.wet_bulb_temp_c,
                publish_rate_hz=10.0,
            )
            self.simulators[site.site_id] = PlantSimulator(config)

        logger.info(f"Fleet initialized with {len(sites)} sites: "
                    f"{[s.site_id for s in sites]}")

    async def run_with_nats(self, duration_s: float = 0.0):
        """
        Run all sites concurrently, publishing to NATS.
        Each site uses its own NATS subject prefix: aifactory.{site_id}.sim.telemetry.*

        If duration_s == 0, runs indefinitely.
        """
        try:
            import nats as nats_lib
        except ImportError:
            logger.error("nats-py not installed. Run: pip install nats-py")
            return

        self._running = True
        nc = await nats_lib.connect(self.nats_url, name="fleet-simulator")
        logger.info(f"Fleet connected to NATS: {self.nats_url}")

        start_time = time.time()
        publish_interval = 0.1  # 10 Hz

        try:
            while self._running:
                elapsed = time.time() - start_time

                if duration_s > 0 and elapsed >= duration_s:
                    break

                # Step all simulators with their site-specific workloads
                for site in self.sites:
                    sim = self.simulators[site.site_id]
                    workload = compute_workload(
                        site.workload_pattern, elapsed, site.load_offset
                    )
                    sim.set_workload_all(workload)
                    sim.step()

                # Publish telemetry for each site
                for site in self.sites:
                    sim = self.simulators[site.site_id]
                    for cdu_idx in range(site.num_cdus):
                        data = sim.get_sensor_data(cdu_idx)
                        data["site_id"] = site.site_id
                        data["cdu_id"] = f"CDU_{cdu_idx + 1:02d}"
                        subject = (
                            f"aifactory.{site.site_id}.sim.telemetry.CDU_{cdu_idx + 1:02d}"
                        )
                        await nc.publish(subject, json.dumps(data).encode())

                await asyncio.sleep(publish_interval)

        finally:
            await nc.close()
            logger.info("Fleet simulation stopped.")

    def run_standalone(self, duration_s: float = 60.0) -> dict[str, list[dict]]:
        """
        Run all sites without NATS (for testing/analysis).
        Returns history per site.
        """
        dt = 0.01
        steps = int(duration_s / dt)
        record_interval = 10  # Every 100ms
        histories: dict[str, list[dict]] = {site.site_id: [] for site in self.sites}

        for step in range(steps):
            t = step * dt

            for site in self.sites:
                sim = self.simulators[site.site_id]
                workload = compute_workload(
                    site.workload_pattern, t, site.load_offset
                )
                sim.set_workload_all(workload)
                sim.step()

                if step % record_interval == 0:
                    data = sim.get_sensor_data(0)
                    data["time_s"] = round(t, 2)
                    data["site_id"] = site.site_id
                    data["workload"] = round(workload, 3)
                    histories[site.site_id].append(data)

        return histories

    def stop(self):
        """Signal all simulations to stop."""
        self._running = False


def print_fleet_summary(histories: dict[str, list[dict]]):
    """Print a summary of the fleet simulation results."""
    print("\n" + "=" * 70)
    print("  FLEET SIMULATION SUMMARY")
    print("=" * 70)

    for site_id, history in histories.items():
        if not history:
            continue

        gpu_temps = [h["gpu_max_temp"] for h in history]
        supply_temps = [h["supply_temp"] for h in history if h["supply_temp"] > -900]

        print(f"\n  Site: {site_id}")
        print(f"    Data points:     {len(history)}")
        print(f"    GPU max temp:    {max(gpu_temps):.1f}°C")
        print(f"    GPU avg temp:    {sum(gpu_temps)/len(gpu_temps):.1f}°C")
        print(f"    Supply temp:     {min(supply_temps):.1f} — {max(supply_temps):.1f}°C")
        print(f"    Final workload:  {history[-1].get('workload', 0):.1%}")

    print("\n" + "=" * 70)


async def async_main():
    parser = argparse.ArgumentParser(description="AI Factory Fleet Simulator")
    parser.add_argument(
        "--nats", default=os.environ.get("NATS_URL", ""),
        help="NATS URL (empty = standalone mode)"
    )
    parser.add_argument(
        "--duration", type=float, default=120.0,
        help="Simulation duration in seconds (0 = indefinite in NATS mode)"
    )
    parser.add_argument(
        "--standalone", action="store_true",
        help="Run without NATS (fast simulation, output summary)"
    )
    args = parser.parse_args()

    fleet = FleetSimulator(FLEET_SITES, nats_url=args.nats)

    if args.standalone or not args.nats:
        logger.info(f"Running fleet standalone for {args.duration}s...")
        histories = fleet.run_standalone(args.duration)
        print_fleet_summary(histories)

        # Save results
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "reports", "fleet_results.json"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(
                {site_id: hist[-5:] for site_id, hist in histories.items()},
                f, indent=2
            )
        print(f"\n  Results saved to: {output_path}")
    else:
        logger.info(f"Running fleet with NATS: {args.nats}")
        await fleet.run_with_nats(args.duration)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
