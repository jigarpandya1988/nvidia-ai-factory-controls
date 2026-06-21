"""
Unit Tests — Data Collector (Python Reference Model)
"""

import pytest
from .fb_data_collector import DataCollector, PublishMode


class TestDataCollectorCyclic:
    def test_publishes_at_interval(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("temp1", mode=PublishMode.CYCLIC, interval_scans=10)
        # Should not publish before interval
        for _ in range(9):
            dc.execute({"temp1": 25.0})
        assert "temp1" not in dc.published_points
        # Should publish at interval
        dc.execute({"temp1": 25.0})
        assert "temp1" in dc.published_points

    def test_publishes_repeatedly(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("temp1", mode=PublishMode.CYCLIC, interval_scans=5)
        publish_count = 0
        for _ in range(20):
            dc.execute({"temp1": 25.0})
            if "temp1" in dc.published_points:
                publish_count += 1
        assert publish_count == 4  # 20 / 5 = 4


class TestDataCollectorOnChange:
    def test_publishes_on_deadband_exceeded(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("pressure", mode=PublishMode.ON_CHANGE, deadband=1.0)
        dc.execute({"pressure": 100.0})  # Initial (no last_value to compare)
        # Large change → publish
        dc.execute({"pressure": 100.0})
        assert "pressure" not in dc.published_points  # No change
        dc.execute({"pressure": 102.0})  # Change > deadband
        assert "pressure" in dc.published_points

    def test_does_not_publish_within_deadband(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("level", mode=PublishMode.ON_CHANGE, deadband=5.0)
        dc.execute({"level": 50.0})  # Init
        dc.execute({"level": 50.0})  # Set last_value
        dc.execute({"level": 52.0})  # Within deadband
        assert "level" not in dc.published_points


class TestDataCollectorHybrid:
    def test_publishes_on_change(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("flow", mode=PublishMode.HYBRID, deadband=2.0, heartbeat_scans=100)
        dc.execute({"flow": 30.0})  # Init
        dc.execute({"flow": 30.0})  # Set last_value (timer increments)
        dc.execute({"flow": 35.0})  # Change > deadband
        assert "flow" in dc.published_points

    def test_publishes_on_heartbeat(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("flow", mode=PublishMode.HYBRID, deadband=2.0, heartbeat_scans=10)
        # First execute triggers on-change (0→50), resets timer
        dc.execute({"flow": 50.0})
        assert "flow" in dc.published_points  # Initial on-change publish
        # Now value stays stable — wait for heartbeat (10 scans)
        for _ in range(9):
            dc.execute({"flow": 50.0})
        assert "flow" not in dc.published_points
        dc.execute({"flow": 50.0})  # 10th scan after last publish → heartbeat
        assert "flow" in dc.published_points

    def test_publishes_on_either_condition(self):
        dc = DataCollector()
        dc.enable()
        dc.register_point("valve", mode=PublishMode.HYBRID, deadband=1.0, heartbeat_scans=50)
        dc.execute({"valve": 40.0})  # Init
        dc.execute({"valve": 40.0})  # No change, not at heartbeat
        assert "valve" not in dc.published_points
        dc.execute({"valve": 45.0})  # Change > deadband
        assert "valve" in dc.published_points


class TestDataCollectorCapacity:
    def test_max_capacity_respected(self):
        dc = DataCollector()
        dc.MAX_POINTS = 5
        dc.enable()
        for i in range(5):
            assert dc.register_point(f"pt{i}") is True
        # 6th should fail
        assert dc.register_point("overflow") is False
        assert dc.registered_count == 5


class TestDataCollectorDisabled:
    def test_disabled_no_publish(self):
        dc = DataCollector()
        dc.register_point("x", mode=PublishMode.CYCLIC, interval_scans=1)
        dc.disable()
        for _ in range(10):
            dc.execute({"x": 99.0})
        assert dc.published_points == []
