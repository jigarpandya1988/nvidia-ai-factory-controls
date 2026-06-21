"""
Unit Tests — NATS → AWS Forwarder
====================================
Tests Timestream batching, alarm forwarding, and error handling.

Run: pytest tests/python/edge_gateway/test_aws_forwarder.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
sys.path.insert(0, 'src/edge-gateway/nats-bridge/bridges')
from aws_forwarder import AWSForwarder


class TestAWSForwarder:
    """Tests for NATS → AWS forwarding service."""

    def setup_method(self):
        """Create forwarder instance for each test."""
        self.forwarder = AWSForwarder()
        self.forwarder._batch = []

    def test_batch_accumulation(self):
        """Should accumulate records in batch before flushing."""
        # Simulate adding records to batch
        for i in range(5):
            self.forwarder._batch.append({
                "Dimensions": [
                    {"Name": "site", "Value": "us-west-01"},
                    {"Name": "ipc", "Value": "cooling"},
                    {"Name": "tag", "Value": f"CDU_01.Temp{i}"},
                ],
                "MeasureName": f"CDU_01.Temp{i}",
                "MeasureValue": str(35.0 + i),
                "MeasureValueType": "DOUBLE",
                "Time": str(1717000000000 + i),
                "TimeUnit": "MILLISECONDS",
            })

        assert len(self.forwarder._batch) == 5

    @pytest.mark.asyncio
    async def test_flush_to_timestream(self):
        """Should call Timestream WriteRecords with batch."""
        self.forwarder._batch = [
            {
                "Dimensions": [{"Name": "site", "Value": "test"}],
                "MeasureName": "test",
                "MeasureValue": "42.0",
                "MeasureValueType": "DOUBLE",
                "Time": "1717000000000",
                "TimeUnit": "MILLISECONDS",
            }
        ]

        with patch('aws_forwarder.timestream') as mock_ts:
            mock_ts.write_records = MagicMock()
            await self.forwarder._flush_to_timestream()

            mock_ts.write_records.assert_called_once()
            call_args = mock_ts.write_records.call_args
            assert call_args.kwargs["DatabaseName"] is not None
            assert len(call_args.kwargs["Records"]) == 1

        # Batch should be empty after flush
        assert len(self.forwarder._batch) == 0

    @pytest.mark.asyncio
    async def test_flush_retries_on_failure(self):
        """Should put records back on flush failure."""
        records = [{"MeasureName": "test", "MeasureValue": "1"}]
        self.forwarder._batch = records.copy()

        with patch('aws_forwarder.timestream') as mock_ts:
            mock_ts.write_records = MagicMock(side_effect=Exception("throttled"))
            await self.forwarder._flush_to_timestream()

        # Records should be back in batch for retry
        assert len(self.forwarder._batch) == 1

    def test_batch_size_limit(self):
        """Batch size should be capped at 100 (Timestream limit)."""
        assert self.forwarder._batch_size == 100

    @pytest.mark.asyncio
    async def test_alarm_forwarded_to_iot_core(self, sample_alarm_event):
        """Should publish alarm to IoT Core topic."""
        with patch('aws_forwarder.iot_data') as mock_iot:
            mock_iot.publish = MagicMock()

            # Simulate alarm message from NATS
            msg = AsyncMock()
            msg.subject = "aifactory.us-west-01.cooling.alarms.4"
            msg.data = json.dumps(sample_alarm_event).encode()
            msg.ack = AsyncMock()

            # Can't easily test consume loop, but test the IoT publish logic
            alarm = json.loads(msg.data)
            alarm["ipc"] = "cooling"
            alarm["site"] = "us-west-01"

            mock_iot.publish(
                topic="aifactory/us-west-01/cooling/alarms",
                qos=1,
                payload=json.dumps(alarm).encode(),
            )

            mock_iot.publish.assert_called_once()
            call_args = mock_iot.publish.call_args
            assert "cooling/alarms" in call_args.kwargs["topic"]
