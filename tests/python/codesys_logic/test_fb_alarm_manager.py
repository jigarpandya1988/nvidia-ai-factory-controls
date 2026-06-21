"""
Unit Tests — Alarm Manager (Python Reference Model)
"""

import pytest
from .fb_alarm_manager import AlarmManager, AlarmSeverity


class TestAlarmRaise:
    def test_raise_creates_record(self):
        am = AlarmManager()
        am.raise_alarm(alarm_id=1, severity=AlarmSeverity.WARNING, source="CDU1", message="High temp")
        record = am.get_alarm(1)
        assert record is not None
        assert record.alarm_id == 1
        assert record.severity == AlarmSeverity.WARNING
        assert record.source == "CDU1"
        assert record.active is True
        assert record.acknowledged is False

    def test_raise_increments_counts(self):
        am = AlarmManager()
        am.raise_alarm(alarm_id=1, severity=AlarmSeverity.INFO)
        am.raise_alarm(alarm_id=2, severity=AlarmSeverity.CRITICAL)
        assert am.active_count == 2
        assert am.unacknowledged_count == 2
        assert am.total_alarms == 2


class TestAlarmClear:
    def test_clear_marks_inactive(self):
        am = AlarmManager()
        am.raise_alarm(alarm_id=5, severity=AlarmSeverity.WARNING)
        assert am.active_count == 1
        am.clear_alarm(5)
        record = am.get_alarm(5)
        assert record.active is False
        assert am.active_count == 0

    def test_clear_nonexistent_is_safe(self):
        am = AlarmManager()
        am.clear_alarm(999)  # Should not raise exception
        assert am.active_count == 0


class TestAlarmAcknowledge:
    def test_acknowledge_marks_acked(self):
        am = AlarmManager()
        am.raise_alarm(alarm_id=10, severity=AlarmSeverity.EMERGENCY)
        assert am.unacknowledged_count == 1
        am.acknowledge(10)
        record = am.get_alarm(10)
        assert record.acknowledged is True
        assert am.unacknowledged_count == 0

    def test_acknowledge_does_not_clear(self):
        am = AlarmManager()
        am.raise_alarm(alarm_id=10, severity=AlarmSeverity.CRITICAL)
        am.acknowledge(10)
        record = am.get_alarm(10)
        assert record.active is True  # Still active
        assert record.acknowledged is True


class TestAlarmBuffer:
    def test_buffer_wraps_at_capacity(self):
        am = AlarmManager()
        # Fill buffer and overflow
        for i in range(120):
            am.raise_alarm(alarm_id=i, severity=AlarmSeverity.INFO)
        # Buffer is 100, total raised is 120
        assert am.total_alarms == 120
        # Oldest alarms (0-19) should be overwritten
        # Newest (20-119) should exist
        record = am.get_alarm(119)
        assert record is not None
        assert record.alarm_id == 119

    def test_active_count_after_wrap(self):
        am = AlarmManager()
        for i in range(100):
            am.raise_alarm(alarm_id=i, severity=AlarmSeverity.INFO)
        assert am.active_count == 100
        # Wrap: new alarm overwrites slot 0
        am.raise_alarm(alarm_id=100, severity=AlarmSeverity.WARNING)
        # Slot 0 was overwritten — old alarm gone, new one active
        assert am.active_count == 100  # Still 100 (one overwritten)


class TestAlarmCounts:
    def test_mixed_states_counted_correctly(self):
        am = AlarmManager()
        am.raise_alarm(alarm_id=1, severity=AlarmSeverity.INFO)
        am.raise_alarm(alarm_id=2, severity=AlarmSeverity.WARNING)
        am.raise_alarm(alarm_id=3, severity=AlarmSeverity.CRITICAL)
        am.acknowledge(1)
        am.clear_alarm(2)
        # 1: active=True, acked=True
        # 2: active=False, acked=False
        # 3: active=True, acked=False
        assert am.active_count == 2
        assert am.unacknowledged_count == 2  # 2 and 3 are unacknowledged
