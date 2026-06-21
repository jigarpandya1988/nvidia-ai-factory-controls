"""
FB_PID — Python Reference Implementation
==========================================
Mirrors the CODESYS FB_PID exactly. Same algorithm, same variable names.
Used to validate control logic without CODESYS runtime.

The ST code and this Python code implement the SAME algorithm.
If pytest passes here, the ST code is validated.
"""

from dataclasses import dataclass, field


@dataclass
class PIDController:
    """Python equivalent of FB_PID (CODESYS Structured Text)."""

    # --- Configuration (matches VAR_INPUT) ---
    kp: float = 1.0
    ti: float = 60.0        # Integral time [s]; 0 = disabled
    td: float = 0.0         # Derivative time [s]; 0 = disabled
    output_min: float = 0.0
    output_max: float = 100.0
    deadband: float = 0.0
    rate_limit: float = 0.0  # units/s; 0 = off
    sp_weight: float = 1.0   # Setpoint weight for P-term
    deriv_filter_n: float = 10.0
    safe_output: float = 0.0
    cycle_time_s: float = 0.005

    # --- State (matches VAR) ---
    _integral: float = field(default=0.0, init=False)
    _deriv_state: float = field(default=0.0, init=False)
    _pv_prev: float = field(default=0.0, init=False)
    _output_prev: float = field(default=0.0, init=False)
    _windup_high: bool = field(default=False, init=False)
    _windup_low: bool = field(default=False, init=False)
    _initialized: bool = field(default=False, init=False)
    _enabled: bool = field(default=False, init=False)
    _faulted: bool = field(default=False, init=False)

    # --- Outputs (matches VAR_OUTPUT) ---
    output: float = field(default=0.0, init=False)
    error: float = field(default=0.0, init=False)
    p_term: float = field(default=0.0, init=False)
    i_term: float = field(default=0.0, init=False)
    d_term: float = field(default=0.0, init=False)
    at_upper_limit: bool = field(default=False, init=False)
    at_lower_limit: bool = field(default=False, init=False)

    def enable(self):
        self._enabled = True
        self._faulted = False

    def disable(self):
        self._enabled = False
        self.output = self.safe_output
        self._integral = 0.0
        self._deriv_state = 0.0

    def reset(self):
        self._integral = 0.0
        self._deriv_state = 0.0
        self._initialized = False
        self._faulted = False
        self.output = self.safe_output

    def execute(self, setpoint: float, process_value: float, manual_mode: bool = False, manual_output: float = 0.0) -> float:
        """
        Execute one PID cycle. Returns output value.
        This matches FB_PID.M_Execute() exactly.
        """
        # --- Input validation ---
        if self.cycle_time_s <= 0.0:
            self._faulted = True
            self.output = self.safe_output
            return self.output

        if self.output_min >= self.output_max:
            self._faulted = True
            self.output = self.safe_output
            return self.output

        if not self._enabled:
            self.output = self.safe_output
            return self.output

        # --- First-scan init ---
        if not self._initialized:
            self._pv_prev = process_value
            self._output_prev = self.safe_output
            self._initialized = True

        # --- Manual mode (bumpless transfer) ---
        if manual_mode:
            self.output = max(self.output_min, min(manual_output, self.output_max))
            prop_input = self.kp * (setpoint * self.sp_weight - process_value)
            self._integral = self.output - prop_input - self._deriv_state
            self._output_prev = self.output
            self._pv_prev = process_value
            self.error = setpoint - process_value
            self.p_term = prop_input
            self.i_term = self._integral
            self.d_term = self._deriv_state
            return self.output

        # --- Error calculation ---
        error_local = setpoint - process_value
        if abs(error_local) < self.deadband:
            error_local = 0.0
        self.error = error_local

        # --- Proportional ---
        self.p_term = self.kp * (setpoint * self.sp_weight - process_value)

        # --- Integral (with anti-windup) ---
        if self.ti > 0.0:
            if not (self._windup_high and error_local > 0.0) and \
               not (self._windup_low and error_local < 0.0):
                self._integral += (self.kp / self.ti) * error_local * self.cycle_time_s
            self.i_term = self._integral
        else:
            self.i_term = 0.0
            self._integral = 0.0

        # --- Derivative (filtered, on PV) ---
        if self.td > 0.0 and self.cycle_time_s > 0.0:
            n = max(2.0, min(self.deriv_filter_n, 50.0))
            deriv_input = -(process_value - self._pv_prev) / self.cycle_time_s
            self._deriv_state = (
                self._deriv_state * self.td + self.kp * self.td * deriv_input * self.cycle_time_s
            ) / (self.td + self.cycle_time_s * n)
            self.d_term = self._deriv_state
        else:
            self.d_term = 0.0
            self._deriv_state = 0.0

        # --- Sum ---
        output_raw = self.p_term + self.i_term + self.d_term

        # --- Windup detection ---
        self._windup_high = output_raw > self.output_max
        self._windup_low = output_raw < self.output_min

        # --- Limit ---
        output_limited = max(self.output_min, min(output_raw, self.output_max))
        self.at_upper_limit = output_limited >= self.output_max
        self.at_lower_limit = output_limited <= self.output_min

        # --- Rate limit ---
        if self.rate_limit > 0.0:
            max_change = self.rate_limit * self.cycle_time_s
            if output_limited - self._output_prev > max_change:
                output_limited = self._output_prev + max_change
            elif output_limited - self._output_prev < -max_change:
                output_limited = self._output_prev - max_change

        # --- Store ---
        self.output = output_limited
        self._output_prev = self.output
        self._pv_prev = process_value

        return self.output
