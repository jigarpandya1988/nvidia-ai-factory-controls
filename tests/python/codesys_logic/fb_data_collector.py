"""
FB_DataCollector — Python Reference Implementation
====================================================
Mirrors the CODESYS FB_DataCollector.
Register data points with publish mode: CYCLIC, ON_CHANGE, HYBRID.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional


class PublishMode(IntEnum):
    CYCLIC = 0
    ON_CHANGE = 1
    HYBRID = 2


@dataclass
class DataPoint:
    """Registered data point configuration and state."""
    name: str = ""
    mode: PublishMode = PublishMode.CYCLIC
    interval_scans: int = 100      # Cyclic publish interval
    deadband: float = 0.1          # On-change threshold
    heartbeat_scans: int = 1000    # Hybrid max time between publishes
    # Internal state
    last_value: float = 0.0
    timer: int = 0
    last_publish_timer: int = 0
    published: bool = False


@dataclass
class DataCollector:
    """Python equivalent of FB_DataCollector."""

    MAX_POINTS: int = 64

    # --- State ---
    _points: Dict[str, DataPoint] = field(default_factory=dict, init=False)
    _scan_count: int = field(default=0, init=False)
    _enabled: bool = field(default=False, init=False)

    # --- Outputs ---
    published_points: List[str] = field(default_factory=list, init=False)
    registered_count: int = field(default=0, init=False)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def register_point(
        self,
        name: str,
        mode: PublishMode = PublishMode.CYCLIC,
        interval_scans: int = 100,
        deadband: float = 0.1,
        heartbeat_scans: int = 1000,
    ) -> bool:
        """Register a data point. Returns False if at capacity."""
        if len(self._points) >= self.MAX_POINTS:
            return False
        self._points[name] = DataPoint(
            name=name,
            mode=mode,
            interval_scans=interval_scans,
            deadband=deadband,
            heartbeat_scans=heartbeat_scans,
        )
        self.registered_count = len(self._points)
        return True

    def execute(self, values: Dict[str, float] = None):
        """Execute one collection cycle. Returns list of published point names."""
        if values is None:
            values = {}

        self.published_points = []

        if not self._enabled:
            return

        self._scan_count += 1

        for name, point in self._points.items():
            current_value = values.get(name, point.last_value)
            point.timer += 1
            should_publish = False

            if point.mode == PublishMode.CYCLIC:
                if point.timer >= point.interval_scans:
                    should_publish = True
                    point.timer = 0

            elif point.mode == PublishMode.ON_CHANGE:
                if abs(current_value - point.last_value) > point.deadband:
                    should_publish = True

            elif point.mode == PublishMode.HYBRID:
                # Publish on change OR when heartbeat expires
                if abs(current_value - point.last_value) > point.deadband:
                    should_publish = True
                elif point.timer >= point.heartbeat_scans:
                    should_publish = True
                    point.timer = 0

            if should_publish:
                self.published_points.append(name)
                point.last_value = current_value
                point.published = True
                if point.mode == PublishMode.HYBRID:
                    point.timer = 0
            else:
                point.published = False
