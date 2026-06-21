"""
PUE & Compliance Reporter
===========================
Calculates Power Usage Effectiveness and ASHRAE compliance metrics
from simulation output or production Timestream data.

Outputs:
  - reports/pue_report.json
  - reports/pue_report.html

Usage:
  python simulation/reporting/pue_reporter.py [--input simulation_output.json]
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


# ASHRAE thermal guidelines (Class A1 — typical data center)
ASHRAE_A1_LIMITS = {
    'temp_min_c': 15.0,       # Recommended minimum supply air/liquid temp
    'temp_max_c': 32.0,       # Recommended maximum supply air/liquid temp
    'humidity_min_pct': 20.0, # Minimum relative humidity
    'humidity_max_pct': 80.0, # Maximum relative humidity
    'dew_point_max_c': 17.0,  # Maximum dew point
}

# ASHRAE liquid cooling guidelines (W32 class)
ASHRAE_W32_LIMITS = {
    'supply_temp_min_c': 2.0,
    'supply_temp_max_c': 45.0,
    'supply_temp_recommended_max_c': 40.0,
}


@dataclass
class HourlyMetrics:
    """Metrics aggregated per hour."""
    hour: int
    it_power_kw: float = 0.0
    cooling_power_kw: float = 0.0
    overhead_power_kw: float = 0.0
    total_power_kw: float = 0.0
    pue: float = 1.0
    avg_supply_temp_c: float = 0.0
    max_gpu_temp_c: float = 0.0
    samples: int = 0


@dataclass
class ComplianceCheck:
    """ASHRAE compliance status."""
    parameter: str
    value: float
    limit: float
    unit: str
    compliant: bool
    severity: str = "info"  # info, warning, critical


class PUEReporter:
    """
    Calculates PUE and generates compliance reports from simulation data.
    """

    def __init__(self, cooling_overhead_fraction: float = 0.08,
                 lighting_ups_fraction: float = 0.02):
        """
        Args:
            cooling_overhead_fraction: Fraction of IT load used for cooling pumps/fans
            lighting_ups_fraction: Fraction of IT load for lighting, UPS losses, etc.
        """
        self.cooling_overhead_fraction = cooling_overhead_fraction
        self.lighting_ups_fraction = lighting_ups_fraction
        self.hourly_data: list[HourlyMetrics] = []
        self.compliance_checks: list[ComplianceCheck] = []
        self.raw_data: list[dict] = []

    def load_simulation_data(self, filepath: str):
        """Load simulation output JSON."""
        with open(filepath, 'r') as f:
            self.raw_data = json.load(f)

    def load_from_records(self, records: list[dict]):
        """Load data from in-memory records (list of dicts)."""
        self.raw_data = records

    def calculate_pue(self) -> dict:
        """
        Calculate PUE metrics from loaded data.
        
        PUE = Total Facility Power / IT Equipment Power
            = (IT + Cooling + Overhead) / IT
        """
        if not self.raw_data:
            return {'error': 'No data loaded'}

        # Group data into hourly buckets (simulation time)
        # Each simulation second maps to ~1 data point at 100ms intervals
        duration_s = self.raw_data[-1].get('time_s', 0)
        hours = max(1, int(duration_s / 3600) + 1)

        self.hourly_data = []
        for h in range(hours):
            self.hourly_data.append(HourlyMetrics(hour=h))

        # Aggregate per hour
        for record in self.raw_data:
            t = record.get('time_s', 0)
            hour_idx = min(int(t / 3600), hours - 1)
            hm = self.hourly_data[hour_idx]

            gpu_power = record.get('gpu_power_kw', record.get('gpu_total_power_kw', 0))
            cooling_kw = record.get('cooling_kw', record.get('cooling_capacity_kw', 0))
            supply_temp = record.get('supply_temp', 35.0)
            gpu_temp = record.get('gpu_max_temp', 0)

            hm.it_power_kw += gpu_power
            hm.cooling_power_kw += cooling_kw * self.cooling_overhead_fraction
            hm.avg_supply_temp_c += supply_temp
            hm.max_gpu_temp_c = max(hm.max_gpu_temp_c, gpu_temp)
            hm.samples += 1

        # Finalize averages and calculate PUE per hour
        for hm in self.hourly_data:
            if hm.samples > 0:
                hm.it_power_kw /= hm.samples
                hm.cooling_power_kw /= hm.samples
                hm.avg_supply_temp_c /= hm.samples
                hm.overhead_power_kw = hm.it_power_kw * self.lighting_ups_fraction
                hm.total_power_kw = hm.it_power_kw + hm.cooling_power_kw + hm.overhead_power_kw
                hm.pue = hm.total_power_kw / hm.it_power_kw if hm.it_power_kw > 0 else 1.0

        # Overall metrics
        total_it = sum(hm.it_power_kw for hm in self.hourly_data)
        total_cooling = sum(hm.cooling_power_kw for hm in self.hourly_data)
        total_overhead = sum(hm.overhead_power_kw for hm in self.hourly_data)
        total_all = total_it + total_cooling + total_overhead
        avg_pue = total_all / total_it if total_it > 0 else 1.0

        return {
            'average_pue': round(avg_pue, 4),
            'hourly_pue': [round(hm.pue, 4) for hm in self.hourly_data],
            'energy_breakdown': {
                'it_power_kw': round(total_it / max(1, len(self.hourly_data)), 1),
                'cooling_power_kw': round(total_cooling / max(1, len(self.hourly_data)), 1),
                'overhead_power_kw': round(total_overhead / max(1, len(self.hourly_data)), 1),
                'total_power_kw': round(total_all / max(1, len(self.hourly_data)), 1),
            },
            'peak_gpu_temp_c': max(hm.max_gpu_temp_c for hm in self.hourly_data),
            'avg_supply_temp_c': round(
                sum(hm.avg_supply_temp_c for hm in self.hourly_data) / max(1, len(self.hourly_data)), 1
            ),
        }

    def check_ashrae_compliance(self) -> list[ComplianceCheck]:
        """Check ASHRAE thermal guideline compliance."""
        self.compliance_checks = []

        if not self.raw_data:
            return self.compliance_checks

        supply_temps = [r.get('supply_temp', 35.0) for r in self.raw_data if r.get('supply_temp', 0) > -900]
        gpu_temps = [r.get('gpu_max_temp', 0) for r in self.raw_data]

        avg_supply = sum(supply_temps) / len(supply_temps) if supply_temps else 35.0
        max_supply = max(supply_temps) if supply_temps else 35.0
        min_supply = min(supply_temps) if supply_temps else 35.0
        max_gpu = max(gpu_temps) if gpu_temps else 0

        # W32 liquid cooling checks
        self.compliance_checks.append(ComplianceCheck(
            parameter="Supply Temp (max)",
            value=round(max_supply, 1),
            limit=ASHRAE_W32_LIMITS['supply_temp_max_c'],
            unit="°C",
            compliant=max_supply <= ASHRAE_W32_LIMITS['supply_temp_max_c'],
            severity="critical" if max_supply > ASHRAE_W32_LIMITS['supply_temp_max_c'] else "info",
        ))

        self.compliance_checks.append(ComplianceCheck(
            parameter="Supply Temp (recommended max)",
            value=round(max_supply, 1),
            limit=ASHRAE_W32_LIMITS['supply_temp_recommended_max_c'],
            unit="°C",
            compliant=max_supply <= ASHRAE_W32_LIMITS['supply_temp_recommended_max_c'],
            severity="warning" if max_supply > ASHRAE_W32_LIMITS['supply_temp_recommended_max_c'] else "info",
        ))

        self.compliance_checks.append(ComplianceCheck(
            parameter="Supply Temp (min)",
            value=round(min_supply, 1),
            limit=ASHRAE_W32_LIMITS['supply_temp_min_c'],
            unit="°C",
            compliant=min_supply >= ASHRAE_W32_LIMITS['supply_temp_min_c'],
            severity="critical" if min_supply < ASHRAE_W32_LIMITS['supply_temp_min_c'] else "info",
        ))

        self.compliance_checks.append(ComplianceCheck(
            parameter="GPU Junction Temp (max)",
            value=round(max_gpu, 1),
            limit=83.0,  # GB200 thermal limit with DLC
            unit="°C",
            compliant=max_gpu <= 83.0,
            severity="critical" if max_gpu > 83.0 else "info",
        ))

        return self.compliance_checks

    def generate_json_report(self, output_path: str) -> dict:
        """Generate JSON report file."""
        pue_data = self.calculate_pue()
        compliance = self.check_ashrae_compliance()

        report = {
            'report_type': 'PUE & Compliance Report',
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'data_points': len(self.raw_data),
            'duration_s': self.raw_data[-1].get('time_s', 0) if self.raw_data else 0,
            'pue': pue_data,
            'compliance': {
                'standard': 'ASHRAE W32 (Liquid Cooling)',
                'all_compliant': all(c.compliant for c in compliance),
                'checks': [
                    {
                        'parameter': c.parameter,
                        'value': c.value,
                        'limit': c.limit,
                        'unit': c.unit,
                        'compliant': c.compliant,
                        'severity': c.severity,
                    }
                    for c in compliance
                ],
            },
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def generate_html_report(self, output_path: str, report_data: Optional[dict] = None):
        """Generate a simple HTML report."""
        if report_data is None:
            report_data = self.generate_json_report(output_path.replace('.html', '.json'))

        pue = report_data['pue']
        compliance = report_data['compliance']

        pue_color = '#4ade80' if pue['average_pue'] < 1.2 else (
            '#fbbf24' if pue['average_pue'] < 1.4 else '#ef4444')

        compliance_rows = ""
        for check in compliance['checks']:
            status = "✅" if check['compliant'] else "❌"
            row_class = "" if check['compliant'] else "background:#3b1111;"
            compliance_rows += f"""
            <tr style="{row_class}">
              <td>{status}</td>
              <td>{check['parameter']}</td>
              <td>{check['value']} {check['unit']}</td>
              <td>{check['limit']} {check['unit']}</td>
              <td>{check['severity']}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PUE &amp; Compliance Report</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 2rem; }}
    h1 {{ color: #76b900; }}
    h2 {{ color: #a0a0a0; border-bottom: 1px solid #333; padding-bottom: 0.5rem; }}
    .pue-gauge {{ font-size: 3rem; font-weight: bold; color: {pue_color}; }}
    .card {{ background: #16213e; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
    th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #333; }}
    th {{ color: #76b900; }}
    .energy-bar {{ height: 20px; border-radius: 4px; margin: 2px 0; }}
    .meta {{ color: #666; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>NVIDIA AI Factory — PUE &amp; Compliance Report</h1>
  <p class="meta">Generated: {report_data['generated_at']} | Data points: {report_data['data_points']}</p>

  <div class="card">
    <h2>Power Usage Effectiveness (PUE)</h2>
    <div class="pue-gauge">{pue['average_pue']:.3f}</div>
    <p>Average over reporting period</p>
  </div>

  <div class="card">
    <h2>Energy Breakdown</h2>
    <table>
      <tr><th>Category</th><th>Power (kW)</th><th>% of Total</th></tr>
      <tr>
        <td>IT Equipment</td>
        <td>{pue['energy_breakdown']['it_power_kw']}</td>
        <td>{pue['energy_breakdown']['it_power_kw']/max(0.1,pue['energy_breakdown']['total_power_kw'])*100:.1f}%</td>
      </tr>
      <tr>
        <td>Cooling Infrastructure</td>
        <td>{pue['energy_breakdown']['cooling_power_kw']}</td>
        <td>{pue['energy_breakdown']['cooling_power_kw']/max(0.1,pue['energy_breakdown']['total_power_kw'])*100:.1f}%</td>
      </tr>
      <tr>
        <td>Overhead (UPS, Lighting)</td>
        <td>{pue['energy_breakdown']['overhead_power_kw']}</td>
        <td>{pue['energy_breakdown']['overhead_power_kw']/max(0.1,pue['energy_breakdown']['total_power_kw'])*100:.1f}%</td>
      </tr>
      <tr style="font-weight:bold;">
        <td>Total Facility</td>
        <td>{pue['energy_breakdown']['total_power_kw']}</td>
        <td>100%</td>
      </tr>
    </table>
  </div>

  <div class="card">
    <h2>ASHRAE Compliance — {compliance['standard']}</h2>
    <p>Overall: {"✅ COMPLIANT" if compliance['all_compliant'] else "❌ NON-COMPLIANT"}</p>
    <table>
      <tr><th></th><th>Parameter</th><th>Value</th><th>Limit</th><th>Severity</th></tr>
      {compliance_rows}
    </table>
  </div>

  <div class="card">
    <h2>Thermal Summary</h2>
    <table>
      <tr><td>Peak GPU Temperature</td><td>{pue['peak_gpu_temp_c']:.1f} °C</td></tr>
      <tr><td>Average Supply Temperature</td><td>{pue['avg_supply_temp_c']:.1f} °C</td></tr>
    </table>
  </div>
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)


    def generate_reports(self, output_dir: str = None) -> dict:
        """Generate both JSON and HTML reports. Returns JSON report data."""
        if output_dir is None:
            output_dir = os.path.join(project_root, 'simulation', 'reports')

        json_path = os.path.join(output_dir, 'pue_report.json')
        html_path = os.path.join(output_dir, 'pue_report.html')

        report = self.generate_json_report(json_path)
        self.generate_html_report(html_path, report)

        print(f"  JSON report: {json_path}")
        print(f"  HTML report: {html_path}")
        return report


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Generate PUE report from simulation data."""
    import argparse

    parser = argparse.ArgumentParser(description="PUE & Compliance Reporter")
    parser.add_argument("--input", default=None,
                       help="Path to simulation_output.json")
    parser.add_argument("--output-dir", default=None,
                       help="Output directory for reports")
    args = parser.parse_args()

    reporter = PUEReporter()

    if args.input and os.path.exists(args.input):
        reporter.load_simulation_data(args.input)
    else:
        # Generate sample data from a quick simulation
        print("No input file — running quick simulation for report data...")
        from simulation.plant_model.simulator import PlantSimulator, SimulatorConfig
        config = SimulatorConfig(dt=0.01, num_racks=4, num_cdus=2)
        plant = PlantSimulator(config)
        for cdu in plant.cdus:
            cdu.max_flow_lpm = 800.0
            cdu.effectiveness = 0.90
        plant.set_workload_all(0.7)
        history = plant.run_standalone(duration_s=60.0, scenario="steady")
        reporter.load_from_records(history)

    report = reporter.generate_reports(args.output_dir)

    print()
    print(f"  PUE: {report['pue']['average_pue']:.3f}")
    compliant = report['compliance']['all_compliant']
    print(f"  ASHRAE Compliance: {'PASS' if compliant else 'FAIL'}")


if __name__ == "__main__":
    main()
