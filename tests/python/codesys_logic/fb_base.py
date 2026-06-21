"""
FB_Base — Python Reference Implementation
===========================================
Mirrors the CODESYS FB_Base lifecycle state machine.
All function blocks EXTEND FB_Base for lifecycle management.

States: DISABLED → INIT → RUNNING → FAULT
"""

from dataclasses import dataclass, field
from enum import IntEnum


class Lifecycle(IntEnum):
    DISABLED = 0
    INIT = 1
    RUNNING = 2
    FAULT = 3


@dataclass
class FBBase:
    """Python equivalent of FB_Base (CODESYS Structured Text)."""

    # --- State (internal) ---
    _state: Lifecycle = field(default=Lifecycle.DISABLED, init=False)
    _heartbeat: int = field(default=0, init=False)
    _fault_code: int = field(default=0, init=False)
    _fault_message: str = field(default="", init=False)
    _initialized: bool = field(default=False, init=False)
    _safe_state_called: bool = field(default=False, init=False)

    # --- Outputs ---
    state: Lifecycle = field(default=Lifecycle.DISABLED, init=False)
    heartbeat: int = field(default=0, init=False)
    fault_active: bool = field(default=False, init=False)
    fault_code: int = field(default=0, init=False)

    def enable(self):
        """Enable the function block — transitions to INIT."""
        if self._state == Lifecycle.DISABLED:
            self._state = Lifecycle.INIT
            self._safe_state_called = False

    def disable(self):
        """Disable the function block — transitions to DISABLED, calls safe-state."""
        self._state = Lifecycle.DISABLED
        self._initialized = False
        self._call_safe_state()

    def reset(self):
        """Reset fault — clears fault and transitions to INIT."""
        if self._state == Lifecycle.FAULT:
            self._state = Lifecycle.INIT
            self._fault_code = 0
            self._fault_message = ""
            self._initialized = False
            self._safe_state_called = False

    def set_fault(self, code: int = 1, message: str = ""):
        """Latch a fault condition."""
        self._state = Lifecycle.FAULT
        self._fault_code = code
        self._fault_message = message
        self._call_safe_state()

    def execute(self):
        """Execute one lifecycle cycle."""
        if self._state == Lifecycle.DISABLED:
            self._call_safe_state()
            self._update_outputs()
            return

        if self._state == Lifecycle.FAULT:
            self._call_safe_state()
            self._update_outputs()
            return

        if self._state == Lifecycle.INIT:
            success = self._initialize()
            if success:
                self._state = Lifecycle.RUNNING
                self._initialized = True

        if self._state == Lifecycle.RUNNING:
            self._heartbeat += 1
            self._run()

        self._update_outputs()

    def _initialize(self) -> bool:
        """Override in subclass for init logic. Returns True when init complete."""
        return True

    def _run(self):
        """Override in subclass for main execution logic."""
        pass

    def _call_safe_state(self):
        """Call safe-state outputs (override in subclass)."""
        self._safe_state_called = True
        self._safe_state()

    def _safe_state(self):
        """Override in subclass for safe-state outputs."""
        pass

    def _update_outputs(self):
        """Sync internal state to outputs."""
        self.state = self._state
        self.heartbeat = self._heartbeat
        self.fault_active = self._state == Lifecycle.FAULT
        self.fault_code = self._fault_code
