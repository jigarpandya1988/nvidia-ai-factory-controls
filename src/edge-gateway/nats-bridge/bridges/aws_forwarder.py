"""
NATS → AWS Forwarder
======================
Subscribes to NATS telemetry/alarms and forwards to AWS services.

Replaces the old MQTT Sparkplug bridge with a simpler, faster path:
  NATS JetStream → [this service] → AWS IoT Core MQTT

Also can write directly to Timestream (bypassing IoT Core for efficiency):
  NATS JetStream → [this service] → AWS Timestream (direct SDK call)

Store-and-Forward:
  If AWS is unreachable, NATS JetStream buffers messages automatically.
  When connection restores, JetStream replays from last acknowledged message.
  No data loss, no custom buffering code needed.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any

import nats
from nats.js import JetStreamContext
import boto3

logger = logging.getLogger(__name__)

# Configuration
NATS_URL = os.environ.get("NATS_URL", "nats://nats:4222")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
SITE_ID = os.environ.get("SITE_ID", "us-west-01")
TIMESTREAM_DB = os.environ.get("TIMESTREAM_DB", f"aifactory-{SITE_ID}")
TIMESTREAM_TABLE = os.environ.get("TIMESTREAM_TABLE", "telemetry")

# AWS Clients
timestream = boto3.client("timestream-write", region_name=AWS_REGION)
iot_data = boto3.client("iot-data", region_name=AWS_REGION)


class AWSForwarder:
    """Subscribes to NATS and forwards to AWS."""

    def __init__(self):
        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None
        self._running = False
        self._batch: list[dict] = []
        self._pending_msgs: list = []
        self._batch_size = 100  # Timestream max records per write
        self._flush_interval = 5.0  # Seconds

    async def start(self):
        """Connect and start consuming."""
        self._running = True

        # Connect to NATS
        self.nc = await nats.connect(
            servers=[NATS_URL],
            name="aws-forwarder",
            max_reconnect_attempts=-1,
        )
        self.js = self.nc.jetstream()
        logger.info(f"Connected to NATS: {NATS_URL}")

        # Create durable consumers on JetStream streams
        # Durable = survives restart, resumes from last ack
        telemetry_sub = await self.js.subscribe(
            subject=f"aifactory.{SITE_ID}.*.telemetry.>",
            stream="TELEMETRY",
            durable="aws-forwarder-telemetry",
            manual_ack=True,
        )

        alarm_sub = await self.js.subscribe(
            subject=f"aifactory.{SITE_ID}.*.alarms.>",
            stream="ALARMS",
            durable="aws-forwarder-alarms",
            manual_ack=True,
        )

        # Process messages concurrently
        await asyncio.gather(
            self._consume_telemetry(telemetry_sub),
            self._consume_alarms(alarm_sub),
            self._flush_loop(),
        )

    async def _consume_telemetry(self, sub):
        """Process telemetry messages → batch → Timestream.
        
        Messages are accumulated without acking. After a successful flush to
        Timestream, all messages in the batch are acked. On failure, messages
        stay unacked and JetStream will redeliver them.
        """
        async for msg in sub.messages:
            if not self._running:
                break
            try:
                # Parse NATS subject: aifactory.us-west-01.cooling.telemetry.CDU_01.SupplyTemp
                parts = msg.subject.split(".")
                ipc = parts[2]       # cooling
                tag = ".".join(parts[4:])  # CDU_01.SupplyTemp

                data = json.loads(msg.data)
                value = data["v"]
                timestamp = data["t"]  # milliseconds

                # Add to batch
                self._batch.append({
                    "Dimensions": [
                        {"Name": "site", "Value": SITE_ID},
                        {"Name": "ipc", "Value": ipc},
                        {"Name": "tag", "Value": tag},
                    ],
                    "MeasureName": tag,
                    "MeasureValue": str(value),
                    "MeasureValueType": "DOUBLE",
                    "Time": str(timestamp),
                    "TimeUnit": "MILLISECONDS",
                })
                self._pending_msgs.append(msg)

                # Flush if batch full
                if len(self._batch) >= self._batch_size:
                    await self._flush_to_timestream()

            except Exception as e:
                logger.error(f"Telemetry processing error: {e}")
                await msg.nak(delay=5)  # Retry in 5 seconds

    async def _consume_alarms(self, sub):
        """Process alarm messages → IoT Core (triggers Lambda)."""
        async for msg in sub.messages:
            if not self._running:
                break
            try:
                parts = msg.subject.split(".")
                ipc = parts[2]
                severity = int(parts[4]) if len(parts) > 4 else 0

                alarm = json.loads(msg.data)
                alarm["ipc"] = ipc
                alarm["site"] = SITE_ID
                alarm["severity"] = severity

                # Publish to AWS IoT Core (triggers IoT Rule → Lambda → SNS)
                iot_data.publish(
                    topic=f"aifactory/{SITE_ID}/{ipc}/alarms",
                    qos=1,
                    payload=json.dumps(alarm).encode(),
                )

                await msg.ack()
                logger.info(f"Alarm forwarded to AWS: {ipc} severity={severity}")

            except Exception as e:
                logger.error(f"Alarm forwarding error: {e}")
                await msg.nak(delay=2)

    async def _flush_loop(self):
        """Periodic flush of telemetry batch to Timestream."""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            if self._batch:
                await self._flush_to_timestream()

    async def _flush_to_timestream(self):
        """Write batch to Timestream. Ack pending messages only on success."""
        if not self._batch:
            return

        records = self._batch[:self._batch_size]
        self._batch = self._batch[self._batch_size:]
        msgs_to_ack = self._pending_msgs[:self._batch_size]
        self._pending_msgs = self._pending_msgs[self._batch_size:]

        try:
            timestream.write_records(
                DatabaseName=TIMESTREAM_DB,
                TableName=TIMESTREAM_TABLE,
                Records=records,
                CommonAttributes={},
            )
            # Ack all messages after successful write
            for msg in msgs_to_ack:
                await msg.ack()
            logger.debug(f"Flushed {len(records)} records to Timestream")
        except Exception as e:
            logger.error(f"Timestream write failed: {e}")
            # Put records and messages back for retry
            self._batch = records + self._batch
            self._pending_msgs = msgs_to_ack + self._pending_msgs

    async def stop(self):
        """Graceful shutdown — flush remaining data."""
        self._running = False
        if self._batch:
            await self._flush_to_timestream()
        if self.nc:
            await self.nc.close()
        logger.info("AWS Forwarder stopped")


async def main():
    logging.basicConfig(level=logging.INFO)
    forwarder = AWSForwarder()
    await forwarder.start()


if __name__ == "__main__":
    asyncio.run(main())
