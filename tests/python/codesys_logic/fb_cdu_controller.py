"""
FB_CDU_Controller — Python Reference Implementation
=====================================================
Mirrors the CODESYS FB_CDU_Controller state machine.
States: IDLE → PRE_CHECK → STARTING → RUNNING → STOPPING → FAULT → EMERGENCY_STOP
Uses PIDController for pump/valve control with GPU power feedforward.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from .fb_pid import PIDController


class CDUState(IntEnum):
    IDLE = 0
    PRE_CHECK = 1
    STARTING = 2
    RUNNING = 3
    STOPPING = 4
    FAULT = 5
    EMERGENCY_STOP = 6


@dataclass
class CDUController:
    """Python equivalent of FB_CDU_Controller."""

    # Configuration
    pump_kp: float = 2.0
    pump_ti: float = 30.0
    valve_kp: float = 1.5
    valve_ti: float = 20.0
    feedforward_gain: float = 0.5  # % output per kW GPU
    pre_check_scans: int = 500     # 1s at 2ms cycle
    start_ramp_scans: int = 2500   # 5s at 2ms cycle
    stop_ramp_scans: int = 2500    # 5s at 2ms cycle
    cycle_time_s: float = 0.002

    # State
    _state: CDUState = field(default=CDUState.IDLE, init=False)
    _state_timer: int = field(default=0, init=False)
    _enabled: bool = field(default=False, init=False)
    _pump_pid: PIDController = field(default=None, init=False)
    _valve_pid: PIDController = field(default=None, init=False)

    # Outputs
    state: CDUState = field(default=CDUState.IDLE, init=False)
    pump_output: float = field(default=0.0, init=False)
    valve_output: float = field(default=0.0, init=False)
    fault_code: int = field(default=0, init=False)
    ready: bool = field(default=False, init=False)

    def __post_init__(self):
        self._pump_pid = PIDController(
            kp=self.pump_kp, ti=self.pump_ti, td=0.0,
            output_min=0.0, output_max=100.0, cycle_time_s=self.cycle_time_s
        )
        self._valve_pid = PIDController(
            kp=self.valve_kp, ti=self.valve_ti, td=0.0,
            output_min=0.0, output_max=100.0, cycle_time_s=self.cycle_time_s
        )

    def enable(self):
        """Enable CDU — starts transition to RUNNING."""
        self._enabled = True
        if self._state == CDUState.IDLE:
            self._state = CDUState.PRE_CHECK
            self._state_timer = 0

    def disable(self):
        """Disable CDU — stops gracefully."""
        self._enabled = False
        if self._state in (CDUState.RUNNING, CDUState.STARTING, CDUState.PRE_CHECK):
            self._state = CDUState.STOPPING
            self._state_timer = 0

    def emergency_stop(self):
        """Emergency stop — immediate safe outputs."""
        self._state = CDUState.EMERGENCY_STOP
        self._safe_outputs()
        self._update_outputs()

    def execute(
        self,
        temp_supply: float = 20.0,
        temp_return: float = 30.0,
        temp_setpoint: float = 25.0,
        flow_rate: float = 0.0,
        flow_setpoint: float = 50.0,
        gpu_power_kw: float = 0.0,
        leak_detected: bool = False,
        safety_permit: bool = True,
    ):
        """Execute one CDU control cycle."""
        # Safety checks (unconditional)
        if not safety_permit:
            self._state = CDUState.EMERGENCY_STOP
            self._safe_outputs()
            self._update_outputs()
            return

        if leak_detected:
            self._state = CDUState.FAULT
            self.fault_code = 10  # Leak fault
            self._safe_outputs()
            self._update_outputs()
            return

        # State machine
        if self._state == CDUState.IDLE:
            self._safe_outputs()

        elif self._state == CDUState.PRE_CHECK:
            self._state_timer += 1
            if self._state_timer >= self.pre_check_scans:
                self._state = CDUState.STARTING
                self._state_timer = 0
                self._pump_pid.enable()
                self._valve_pid.enable()

        elif self._state == CDUState.STARTING:
            self._state_timer += 1
            # Ramp setpoints up gradually
            ramp_frac = min(1.0, self._state_timer / self.start_ramp_scans)
            ramped_flow_sp = flow_setpoint * ramp_frac
            self._run_pids(temp_supply, temp_setpoint, flow_rate, ramped_flow_sp, gpu_power_kw)
            if self._state_timer >= self.start_ramp_scans:
                self._state = CDUState.RUNNING
                self._state_timer = 0

        elif self._state == CDUState.RUNNING:
            self._run_pids(temp_supply, temp_setpoint, flow_rate, flow_setpoint, gpu_power_kw)

        elif self._state == CDUState.STOPPING:
            self._state_timer += 1
            ramp_frac = max(0.0, 1.0 - self._state_timer / self.stop_ramp_scans)
            self.pump_output *= ramp_frac
            self.valve_output *= ramp_frac
            if self._state_timer >= self.stop_ramp_scans:
                self._state = CDUState.IDLE
                self._safe_outputs()
                self._pump_pid.disable()
                self._valve_pid.disable()

        elif self._state == CDUState.FAULT:
            self._safe_outputs()

        elif self._state == CDUState.EMERGENCY_STOP:
            self._safe_outputs()

        self._update_outputs()

    def reset(self):
        """Reset from fault — returns to IDLE."""
        if self._state == CDUState.FAULT:
            self._state = CDUState.IDLE
            self.fault_code = 0
            self._update_outputs()

    def _run_pids(self, temp_supply, temp_setpoint, flow_rate, flow_setpoint, gpu_power_kw):
        """Run PID loops with feedforward."""
        feedforward = gpu_power_kw * self.feedforward_gain
        pump_out = self._pump_pid.execute(setpoint=flow_setpoint, process_value=flow_rate)
        valve_out = self._valve_pid.execute(setpoint=temp_setpoint, process_value=temp_supply)
        self.pump_output = min(100.0, pump_out + feedforward)
        self.valve_output = valve_out

    def _safe_outputs(self):
        """Set all outputs to safe (zero)."""
        self.pump_output = 0.0
        self.valve_output = 0.0

    def _update_outputs(self):
        """Sync state to output."""
        self.state = self._state
        self.ready = self._state == CDUState.RUNNING
