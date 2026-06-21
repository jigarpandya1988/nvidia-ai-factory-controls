"""
Chiller Plant Staging Optimizer
=================================
Optimizes which chillers to run and at what capacity to minimize
total electrical input for a given cooling demand.

Algorithm:
  1. Sort available chillers by COP at current load fraction
  2. Stage chillers in order of highest efficiency
  3. Enforce minimum run time to prevent short-cycling
  4. Rotate lead/lag for even wear distribution

Usage:
  optimizer = ChillerOptimizer(chillers=[...])
  result = optimizer.optimize(heat_load_kw=500, ambient_temp_c=30)
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChillerSpec:
    """Specification for a single chiller unit."""
    chiller_id: str
    capacity_kw: float          # Nominal cooling capacity [kW]
    min_load_fraction: float = 0.2  # Minimum load (below this = inefficient/off)
    max_load_fraction: float = 1.0  # Maximum overload fraction

    # COP curve: COP as function of load fraction
    # Typical centrifugal chiller has peak COP around 60-80% load
    cop_at_25pct: float = 4.0
    cop_at_50pct: float = 5.5
    cop_at_75pct: float = 6.0   # Peak efficiency
    cop_at_100pct: float = 5.2

    # Ambient temperature derating (COP drops ~2% per °C above 35°C)
    cop_ambient_derating: float = 0.02  # per °C above reference
    cop_reference_ambient_c: float = 35.0

    # Runtime tracking
    total_run_hours: float = 0.0
    starts: int = 0


@dataclass
class ChillerState:
    """Runtime state of a chiller."""
    chiller_id: str
    is_running: bool = False
    current_load_fraction: float = 0.0
    run_start_time: float = 0.0     # Unix timestamp when started
    stop_time: float = 0.0          # Unix timestamp when stopped
    total_run_hours: float = 0.0
    starts: int = 0


@dataclass
class OptimizationResult:
    """Result of chiller staging optimization."""
    total_cooling_kw: float         # Total cooling output [kW]
    total_power_kw: float           # Total electrical input [kW]
    system_cop: float               # Overall COP (cooling/power)
    assignments: list               # Per-chiller assignments
    chillers_running: int
    heat_load_kw: float
    satisfied: bool                 # Can the load be met?


class ChillerOptimizer:
    """
    Chiller plant optimizer with staging, lead/lag rotation,
    and minimum run-time constraints.
    """

    def __init__(
        self,
        chillers: list[ChillerSpec],
        min_run_time_s: float = 300.0,      # 5 minutes minimum run
        min_off_time_s: float = 300.0,      # 5 minutes minimum off
        staging_deadband_kw: float = 20.0,  # Deadband before staging on/off
        rotation_interval_hours: float = 500.0,  # Rotate lead every 500 hrs
    ):
        self.chillers = chillers
        self.min_run_time_s = min_run_time_s
        self.min_off_time_s = min_off_time_s
        self.staging_deadband_kw = staging_deadband_kw
        self.rotation_interval_hours = rotation_interval_hours

        # Initialize states
        self.states: dict[str, ChillerState] = {
            ch.chiller_id: ChillerState(chiller_id=ch.chiller_id)
            for ch in chillers
        }

        # Lead/lag order (initially by ID, will rotate for even wear)
        self._lead_order: list[str] = [ch.chiller_id for ch in chillers]
        self._last_rotation_time: float = time.time()

    def get_cop(self, spec: ChillerSpec, load_fraction: float, ambient_temp_c: float = 35.0) -> float:
        """
        Interpolate COP from the chiller's efficiency curve at a given load.
        Applies ambient temperature derating.
        """
        # Clamp load fraction
        lf = max(0.0, min(1.0, load_fraction))

        # Piecewise linear interpolation of COP curve
        if lf <= 0.25:
            cop = spec.cop_at_25pct * (lf / 0.25) if lf > 0 else 0.0
        elif lf <= 0.50:
            t = (lf - 0.25) / 0.25
            cop = spec.cop_at_25pct + t * (spec.cop_at_50pct - spec.cop_at_25pct)
        elif lf <= 0.75:
            t = (lf - 0.50) / 0.25
            cop = spec.cop_at_50pct + t * (spec.cop_at_75pct - spec.cop_at_50pct)
        else:
            t = (lf - 0.75) / 0.25
            cop = spec.cop_at_75pct + t * (spec.cop_at_100pct - spec.cop_at_75pct)

        # Ambient derating
        if ambient_temp_c > spec.cop_reference_ambient_c:
            derating = 1.0 - spec.cop_ambient_derating * (ambient_temp_c - spec.cop_reference_ambient_c)
            cop *= max(0.5, derating)  # Floor at 50% of nominal COP

        return max(0.1, cop)

    def _check_lead_rotation(self):
        """Rotate lead/lag order based on runtime for even wear."""
        now = time.time()
        elapsed_hours = (now - self._last_rotation_time) / 3600.0

        if elapsed_hours >= self.rotation_interval_hours:
            # Sort by total runtime (least runtime becomes lead)
            self._lead_order.sort(key=lambda cid: self.states[cid].total_run_hours)
            self._last_rotation_time = now

    def _can_start(self, chiller_id: str, now: float) -> bool:
        """Check if a chiller can be started (min off-time respected)."""
        state = self.states[chiller_id]
        if state.is_running:
            return True  # Already running
        if state.stop_time == 0:
            return True  # Never been stopped
        return (now - state.stop_time) >= self.min_off_time_s

    def _can_stop(self, chiller_id: str, now: float) -> bool:
        """Check if a chiller can be stopped (min run-time respected)."""
        state = self.states[chiller_id]
        if not state.is_running:
            return True  # Already stopped
        return (now - state.run_start_time) >= self.min_run_time_s

    def _get_spec(self, chiller_id: str) -> ChillerSpec:
        """Get spec for a chiller by ID."""
        for ch in self.chillers:
            if ch.chiller_id == chiller_id:
                return ch
        raise ValueError(f"Unknown chiller: {chiller_id}")

    def optimize(
        self,
        heat_load_kw: float,
        ambient_temp_c: float = 35.0,
        now: Optional[float] = None,
    ) -> OptimizationResult:
        """
        Determine optimal chiller staging for the current heat load.

        Args:
            heat_load_kw: Required cooling output [kW]
            ambient_temp_c: Current ambient/condenser water temp [°C]
            now: Current time (unix timestamp). Uses time.time() if None.

        Returns:
            OptimizationResult with per-chiller assignments.
        """
        if now is None:
            now = time.time()

        # Check if lead/lag rotation is needed
        self._check_lead_rotation()

        # --- Step 1: Determine how many chillers needed ---
        # Sort chillers by lead/lag order
        ordered_ids = list(self._lead_order)

        # Calculate COP for each chiller at various load fractions
        # to find the most efficient staging
        total_capacity = sum(self._get_spec(cid).capacity_kw for cid in ordered_ids)

        if heat_load_kw <= 0:
            # No load — shut everything down (respecting min run time)
            assignments = []
            for cid in ordered_ids:
                state = self.states[cid]
                if state.is_running and self._can_stop(cid, now):
                    state.is_running = False
                    state.stop_time = now
                    state.current_load_fraction = 0.0
                assignments.append({
                    'chiller_id': cid,
                    'running': state.is_running,
                    'load_fraction': state.current_load_fraction,
                    'cooling_kw': 0.0,
                    'power_kw': 0.0,
                    'cop': 0.0,
                })
            return OptimizationResult(
                total_cooling_kw=0.0,
                total_power_kw=0.0,
                system_cop=0.0,
                assignments=assignments,
                chillers_running=sum(1 for a in assignments if a['running']),
                heat_load_kw=heat_load_kw,
                satisfied=True,
            )

        # --- Step 2: Find optimal number of chillers ---
        # Strategy: Try each count (1, 2, ..., N) and pick the one
        # that minimizes total power input
        best_power = float('inf')
        best_assignment = None

        for n_chillers in range(1, len(ordered_ids) + 1):
            # Use the first N chillers in lead/lag order
            candidates = ordered_ids[:n_chillers]

            # Check if they can provide enough capacity
            available_capacity = sum(
                self._get_spec(cid).capacity_kw * self._get_spec(cid).max_load_fraction
                for cid in candidates
            )
            if available_capacity < heat_load_kw - self.staging_deadband_kw:
                continue  # Not enough capacity, need more chillers

            # Check if all can start (respect min off-time)
            all_can_start = all(self._can_start(cid, now) for cid in candidates)
            if not all_can_start:
                # Try alternative: keep currently running ones, add what we can
                candidates = [cid for cid in candidates if self._can_start(cid, now)]
                available_capacity = sum(
                    self._get_spec(cid).capacity_kw * self._get_spec(cid).max_load_fraction
                    for cid in candidates
                )
                if available_capacity < heat_load_kw - self.staging_deadband_kw:
                    continue

            # Distribute load evenly, then adjust for COP optimization
            if len(candidates) == 0:
                continue

            # Equal distribution first
            load_per_chiller = heat_load_kw / len(candidates)

            # Check minimum load constraint
            all_above_min = all(
                load_per_chiller / self._get_spec(cid).capacity_kw >= self._get_spec(cid).min_load_fraction
                for cid in candidates
            )

            if not all_above_min and n_chillers > 1:
                continue  # Would be below minimum load, try fewer chillers

            # Calculate total power for this staging
            total_power = 0.0
            assignment = []
            remaining_load = heat_load_kw

            for i, cid in enumerate(candidates):
                spec = self._get_spec(cid)
                # Distribute proportionally to capacity
                if i == len(candidates) - 1:
                    chiller_load = remaining_load
                else:
                    chiller_load = heat_load_kw * (spec.capacity_kw / available_capacity)
                    remaining_load -= chiller_load

                load_fraction = chiller_load / spec.capacity_kw
                load_fraction = max(spec.min_load_fraction, min(spec.max_load_fraction, load_fraction))
                actual_cooling = load_fraction * spec.capacity_kw

                cop = self.get_cop(spec, load_fraction, ambient_temp_c)
                power = actual_cooling / cop if cop > 0 else actual_cooling

                total_power += power
                assignment.append({
                    'chiller_id': cid,
                    'running': True,
                    'load_fraction': round(load_fraction, 3),
                    'cooling_kw': round(actual_cooling, 1),
                    'power_kw': round(power, 1),
                    'cop': round(cop, 2),
                })

            if total_power < best_power:
                best_power = total_power
                best_assignment = assignment

        # --- Step 3: Apply the best staging ---
        if best_assignment is None:
            # Cannot satisfy load — run everything at max
            best_assignment = []
            total_power = 0.0
            total_cooling = 0.0
            for cid in ordered_ids:
                spec = self._get_spec(cid)
                cop = self.get_cop(spec, 1.0, ambient_temp_c)
                power = spec.capacity_kw / cop
                total_power += power
                total_cooling += spec.capacity_kw
                best_assignment.append({
                    'chiller_id': cid,
                    'running': True,
                    'load_fraction': 1.0,
                    'cooling_kw': spec.capacity_kw,
                    'power_kw': round(power, 1),
                    'cop': round(cop, 2),
                })
            best_power = total_power

        # Update states
        running_ids = {a['chiller_id'] for a in best_assignment if a['running']}
        for cid in ordered_ids:
            state = self.states[cid]
            if cid in running_ids:
                if not state.is_running:
                    state.is_running = True
                    state.run_start_time = now
                    state.starts += 1
                # Update load fraction
                for a in best_assignment:
                    if a['chiller_id'] == cid:
                        state.current_load_fraction = a['load_fraction']
            else:
                if state.is_running and self._can_stop(cid, now):
                    state.is_running = False
                    state.stop_time = now
                    state.current_load_fraction = 0.0

        # Add non-running chillers to assignment list
        running_assignment_ids = {a['chiller_id'] for a in best_assignment}
        for cid in ordered_ids:
            if cid not in running_assignment_ids:
                best_assignment.append({
                    'chiller_id': cid,
                    'running': False,
                    'load_fraction': 0.0,
                    'cooling_kw': 0.0,
                    'power_kw': 0.0,
                    'cop': 0.0,
                })

        total_cooling = sum(a['cooling_kw'] for a in best_assignment)
        system_cop = total_cooling / best_power if best_power > 0 else 0.0

        return OptimizationResult(
            total_cooling_kw=round(total_cooling, 1),
            total_power_kw=round(best_power, 1),
            system_cop=round(system_cop, 2),
            assignments=best_assignment,
            chillers_running=sum(1 for a in best_assignment if a['running']),
            heat_load_kw=heat_load_kw,
            satisfied=total_cooling >= heat_load_kw * 0.95,
        )

    def update_runtime(self, dt_s: float):
        """Update runtime counters (call periodically)."""
        for state in self.states.values():
            if state.is_running:
                state.total_run_hours += dt_s / 3600.0

    def get_lead_order(self) -> list[str]:
        """Get current lead/lag priority order."""
        return list(self._lead_order)

    def force_rotation(self):
        """Force a lead/lag rotation now (for testing or manual override)."""
        self._lead_order.sort(key=lambda cid: self.states[cid].total_run_hours)
        self._last_rotation_time = time.time()


# =============================================================================
# Example / Self-test
# =============================================================================

if __name__ == "__main__":
    # Create a 3-chiller plant
    chillers = [
        ChillerSpec(chiller_id="CH-01", capacity_kw=500, cop_at_75pct=6.2),
        ChillerSpec(chiller_id="CH-02", capacity_kw=500, cop_at_75pct=5.8),
        ChillerSpec(chiller_id="CH-03", capacity_kw=350, cop_at_75pct=5.5),
    ]

    optimizer = ChillerOptimizer(chillers)

    # Test different load points
    loads = [100, 250, 400, 600, 800, 1000, 1200]
    print("Chiller Plant Optimization Results")
    print("=" * 70)
    print(f"{'Load (kW)':<12}{'# Running':<12}{'Power (kW)':<12}{'System COP':<12}{'Satisfied'}")
    print("-" * 70)

    for load in loads:
        result = optimizer.optimize(heat_load_kw=load, ambient_temp_c=30.0)
        print(f"{load:<12}{result.chillers_running:<12}{result.total_power_kw:<12.1f}"
              f"{result.system_cop:<12.2f}{result.satisfied}")

    print()
    print("Detail for 600 kW load:")
    result = optimizer.optimize(heat_load_kw=600, ambient_temp_c=30.0)
    for a in result.assignments:
        if a['running']:
            print(f"  {a['chiller_id']}: {a['load_fraction']*100:.0f}% load, "
                  f"{a['cooling_kw']:.0f} kW cooling, {a['power_kw']:.0f} kW input, COP={a['cop']}")
