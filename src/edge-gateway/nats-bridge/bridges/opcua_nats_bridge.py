"""
OPC UA ↔ NATS Bridge — Per-IPC Service
=========================================
NVIDIA AI Factory Controls

One instance per IPC. Bridges CODESYS OPC UA server to NATS broker.

DATA FLOWS:
  CODESYS → OPC UA → [this bridge] → NATS → Cloud / Other IPCs
  Cloud / Other IPCs → NATS → [this bridge] → OPC UA → CODESYS

RESPONSIBILITIES:
  1. PUBLISH: Read OPC UA tags → publish to NATS subjects (telemetry)
  2. SUBSCRIBE: Receive NATS messages → write to OPC UA (commands, peer data)
  3. PEER: Publish peer data at high frequency (safety permit, coordination)
  4. HEALTH: Report bridge health, detect OPC UA disconnection

SUBJECT MAPPING:
  OPC UA Node: GVL_OPCUA_Publish.Cooling_CDU_01_SupplyTemp
  NATS Subject: aifactory.us-west-01.cooling.telemetry.CDU_01.SupplyTemp

  OPC UA Node: GVL_OPCUA_Publish.Cmd_CDU_01_SupplyTempSP (writable)
  NATS Subject: aifactory.us-west-01.cooling.commands.CDU_01.SupplyTempSP
"""

import asyncio
import json
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import nats
from nats.js import JetStreamContext
from asyncua import Client as OPCUAClient
from asyncua import ua
import yaml

import structlog

logger = structlog.get_logger()


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class BridgeConfig:
    """Per-IPC bridge configuration."""
    ipc_name: str = "cooling"
    site_id: str = "us-west-01"
    opcua_url: str = "opc.tcp://192.168.100.20:4840"
    nats_url: str = "nats://localhost:4222"
    nats_creds: str = ""
    poll_interval_ms: int = 100       # Telemetry polling rate
    peer_interval_ms: int = 5         # Peer exchange rate (fast!)
    publish_nodes: list = field(default_factory=list)   # OPC UA nodes to publish
    subscribe_subjects: list = field(default_factory=list)  # NATS subjects to write back
    command_nodes: list = field(default_factory=list)    # OPC UA nodes writable from NATS


def load_config() -> BridgeConfig:
    """Load config from environment + YAML file."""
    config = BridgeConfig(
        ipc_name=os.environ.get("IPC_NAME", "cooling"),
        site_id=os.environ.get("SITE_ID", "us-west-01"),
        opcua_url=os.environ.get("IPC_OPCUA_URL", "opc.tcp://192.168.100.20:4840"),
        nats_url=os.environ.get("NATS_URL", "nats://localhost:4222"),
        nats_creds=os.environ.get("NATS_CREDS", ""),
        poll_interval_ms=int(os.environ.get("POLL_INTERVAL_MS", "100")),
        peer_interval_ms=int(os.environ.get("PEER_PUBLISH_INTERVAL_MS", "5")),
    )

    # Load node lists from YAML config file
    config_path = Path("/app/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f)
        config.publish_nodes = yaml_config.get("publish_nodes", [])
        config.subscribe_subjects = yaml_config.get("subscribe_subjects", [])
        config.command_nodes = yaml_config.get("command_nodes", [])

    return config


# =============================================================================
# OPC UA Client Manager
# =============================================================================
class OPCUAManager:
    """Manages OPC UA connection to one IPC."""

    def __init__(self, url: str, ipc_name: str):
        self.url = url
        self.ipc_name = ipc_name
        self.client: OPCUAClient | None = None
        self.connected = False
        self._node_cache: dict[str, Any] = {}

    async def connect(self):
        """Connect with retry logic."""
        max_retries = 10
        for attempt in range(max_retries):
            try:
                self.client = OPCUAClient(url=self.url, timeout=5)
                await self.client.connect()
                self.connected = True
                logger.info("OPC UA connected", ipc=self.ipc_name, url=self.url)
                return
            except Exception as e:
                wait = min(2 ** attempt, 30)
                logger.warning("OPC UA connect failed, retrying",
                             ipc=self.ipc_name, attempt=attempt+1, wait=wait, error=str(e))
                await asyncio.sleep(wait)
        raise ConnectionError(f"Failed to connect to {self.ipc_name} after {max_retries} attempts")

    async def read_node(self, node_id: str) -> Any:
        """Read a single OPC UA node value."""
        if not self.connected:
            return None
        try:
            if node_id not in self._node_cache:
                self._node_cache[node_id] = self.client.get_node(node_id)
            return await self._node_cache[node_id].read_value()
        except Exception as e:
            logger.warning("OPC UA read failed", node=node_id, error=str(e))
            return None

    async def write_node(self, node_id: str, value: Any, datatype=None):
        """Write a value to an OPC UA node (for commands)."""
        if not self.connected:
            return False
        try:
            if node_id not in self._node_cache:
                self._node_cache[node_id] = self.client.get_node(node_id)
            node = self._node_cache[node_id]
            if datatype:
                await node.write_value(ua.DataValue(ua.Variant(value, datatype)))
            else:
                await node.write_value(value)
            return True
        except Exception as e:
            logger.warning("OPC UA write failed", node=node_id, error=str(e))
            return False

    async def read_all(self, node_ids: list[str]) -> dict[str, Any]:
        """Batch read multiple nodes."""
        results = {}
        for node_id in node_ids:
            val = await self.read_node(node_id)
            if val is not None:
                results[node_id] = val
        return results

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.connected = False


# =============================================================================
# NATS Publisher/Subscriber
# =============================================================================
class NATSManager:
    """Manages NATS connection, publishing, and subscriptions."""

    def __init__(self, url: str, ipc_name: str, site_id: str, creds: str = ""):
        self.url = url
        self.ipc_name = ipc_name
        self.site_id = site_id
        self.creds = creds
        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None
        self.connected = False
        self._subscriptions = []

    async def connect(self):
        """Connect to NATS with auto-reconnect."""
        options = {
            "servers": [self.url],
            "name": f"bridge-{self.ipc_name}",
            "reconnect_time_wait": 1,
            "max_reconnect_attempts": -1,  # Infinite reconnect
            "disconnected_cb": self._on_disconnect,
            "reconnected_cb": self._on_reconnect,
            "error_cb": self._on_error,
        }
        if self.creds:
            options["user_credentials"] = self.creds

        self.nc = await nats.connect(**options)
        self.js = self.nc.jetstream()
        self.connected = True
        logger.info("NATS connected", ipc=self.ipc_name, url=self.url)

    async def publish_telemetry(self, tag: str, value: Any, quality: int = 0):
        """Publish a telemetry value to NATS subject."""
        subject = f"aifactory.{self.site_id}.{self.ipc_name}.telemetry.{tag}"
        payload = json.dumps({
            "v": value,
            "q": quality,
            "t": int(time.time() * 1000),
        }).encode()

        try:
            # Use JetStream for persistent publishing (store-and-forward)
            await self.js.publish(subject, payload)
        except Exception:
            # Fallback to core NATS if JetStream stream not configured
            await self.nc.publish(subject, payload)

    async def publish_peer(self, data: dict):
        """Publish peer exchange data (high frequency, no persistence needed)."""
        subject = f"aifactory.{self.site_id}.{self.ipc_name}.peer"
        payload = json.dumps(data).encode()
        # Core NATS publish (no JetStream — speed over persistence for peer data)
        await self.nc.publish(subject, payload)

    async def publish_alarm(self, alarm: dict):
        """Publish alarm event (persisted via JetStream)."""
        subject = f"aifactory.{self.site_id}.{self.ipc_name}.alarms.{alarm.get('severity', 0)}"
        payload = json.dumps(alarm).encode()
        await self.js.publish(subject, payload)

    async def subscribe_commands(self, callback):
        """Subscribe to command subjects for this IPC."""
        subject = f"aifactory.{self.site_id}.{self.ipc_name}.commands.>"
        sub = await self.nc.subscribe(subject, cb=callback)
        self._subscriptions.append(sub)
        logger.info("Subscribed to commands", subject=subject)

    async def subscribe_peer(self, peer_names: list[str], callback):
        """Subscribe to peer data from other IPCs."""
        for peer in peer_names:
            if peer != self.ipc_name:
                subject = f"aifactory.{self.site_id}.{peer}.peer"
                sub = await self.nc.subscribe(subject, cb=callback)
                self._subscriptions.append(sub)
                logger.info("Subscribed to peer", peer=peer, subject=subject)

    async def request_reply(self, subject: str, payload: bytes, timeout: float = 2.0):
        """Send request and wait for reply (for command acknowledgment)."""
        try:
            msg = await self.nc.request(subject, payload, timeout=timeout)
            return json.loads(msg.data)
        except Exception as e:
            logger.warning("Request/reply failed", subject=subject, error=str(e))
            return None

    async def _on_disconnect(self):
        self.connected = False
        logger.warning("NATS disconnected", ipc=self.ipc_name)

    async def _on_reconnect(self):
        self.connected = True
        logger.info("NATS reconnected", ipc=self.ipc_name)

    async def _on_error(self, e):
        logger.error("NATS error", ipc=self.ipc_name, error=str(e))

    async def close(self):
        for sub in self._subscriptions:
            await sub.unsubscribe()
        if self.nc:
            await self.nc.close()
        self.connected = False


# =============================================================================
# Main Bridge Logic
# =============================================================================
class OPCUANATSBridge:
    """
    Bridges one IPC's OPC UA server to the NATS broker.
    
    Runs three concurrent loops:
      1. Telemetry loop (100ms) — reads OPC UA, publishes to NATS
      2. Peer loop (5ms) — reads safety/coordination, publishes to NATS
      3. Command loop (event-driven) — receives NATS commands, writes OPC UA
    """

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.opcua = OPCUAManager(config.opcua_url, config.ipc_name)
        self.nats = NATSManager(config.nats_url, config.ipc_name, config.site_id, config.nats_creds)
        self._running = False
        self._peer_data: dict[str, dict] = {}  # Received peer data

    async def start(self):
        """Start the bridge."""
        self._running = True
        logger.info("Bridge starting", ipc=self.config.ipc_name)

        # Connect to both
        await self.opcua.connect()
        await self.nats.connect()

        # Subscribe to commands and peer data
        await self.nats.subscribe_commands(self._on_command)
        await self.nats.subscribe_peer(
            ["power", "cooling", "environment", "safety"],
            self._on_peer_data,
        )

        # Run concurrent loops
        await asyncio.gather(
            self._telemetry_loop(),
            self._peer_publish_loop(),
            self._peer_write_loop(),
            self._health_loop(),
        )

    async def _telemetry_loop(self):
        """Read OPC UA tags, publish to NATS at configured interval."""
        interval = self.config.poll_interval_ms / 1000.0

        while self._running:
            try:
                if self.opcua.connected and self.nats.connected:
                    values = await self.opcua.read_all(
                        [n["node_id"] for n in self.config.publish_nodes]
                    )
                    for node_cfg in self.config.publish_nodes:
                        node_id = node_cfg["node_id"]
                        tag = node_cfg["tag"]
                        if node_id in values:
                            await self.nats.publish_telemetry(tag, values[node_id])
            except Exception as e:
                logger.error("Telemetry loop error", error=str(e))

            await asyncio.sleep(interval)

    async def _peer_publish_loop(self):
        """Publish peer exchange data at high frequency."""
        interval = self.config.peer_interval_ms / 1000.0

        # Peer nodes are the safety-critical ones (permit, emergency, health)
        peer_nodes = [
            "ns=4;s=GVL_OPCUA_Publish.Safety_Permit",
            "ns=4;s=GVL_OPCUA_Publish.Cooling_CDU_01_Healthy",
        ]

        while self._running:
            try:
                if self.opcua.connected and self.nats.connected:
                    values = await self.opcua.read_all(peer_nodes)
                    peer_data = {
                        "ipc": self.config.ipc_name,
                        "t": int(time.time() * 1000),
                        "healthy": True,
                        "values": {str(k): v for k, v in values.items()},
                    }
                    await self.nats.publish_peer(peer_data)
            except Exception as e:
                logger.warning("Peer publish error", error=str(e))

            await asyncio.sleep(interval)

    async def _peer_write_loop(self):
        """Write received peer data back to CODESYS via OPC UA."""
        while self._running:
            try:
                # Write safety permit from safety IPC to this IPC's input
                if "safety" in self._peer_data:
                    safety = self._peer_data["safety"]
                    permit = safety.get("values", {}).get(
                        "ns=4;s=GVL_OPCUA_Publish.Safety_Permit", True
                    )
                    await self.opcua.write_node(
                        "ns=4;s=GVL_CrossTask.bSafetyPermit_Global",
                        permit,
                    )
            except Exception as e:
                logger.warning("Peer write error", error=str(e))

            await asyncio.sleep(0.01)  # 10ms — fast enough for safety

    async def _on_command(self, msg):
        """Handle incoming command from NATS (cloud/SCADA → IPC)."""
        try:
            subject = msg.subject
            data = json.loads(msg.data)

            # Extract command target from subject:
            # aifactory.us-west-01.cooling.commands.CDU_01.SupplyTempSP
            parts = subject.split(".")
            tag = ".".join(parts[4:])  # CDU_01.SupplyTempSP

            # Find matching command node and write to OPC UA
            for cmd_node in self.config.command_nodes:
                if cmd_node["tag"] == tag:
                    value = data.get("value")
                    if value is not None:
                        success = await self.opcua.write_node(cmd_node["node_id"], value)
                        logger.info("Command executed",
                                   tag=tag, value=value, success=success)

                        # Reply if request/reply pattern
                        if msg.reply:
                            reply = json.dumps({"success": success, "tag": tag}).encode()
                            await self.nats.nc.publish(msg.reply, reply)
                    break

        except Exception as e:
            logger.error("Command handling error", error=str(e), subject=msg.subject)

    async def _on_peer_data(self, msg):
        """Handle incoming peer data from another IPC."""
        try:
            data = json.loads(msg.data)
            ipc = data.get("ipc", "unknown")
            self._peer_data[ipc] = data
        except Exception as e:
            logger.warning("Peer data parse error", error=str(e))

    async def _health_loop(self):
        """Periodic health reporting."""
        while self._running:
            status = {
                "bridge": self.config.ipc_name,
                "opcua_connected": self.opcua.connected,
                "nats_connected": self.nats.connected,
                "peers_known": list(self._peer_data.keys()),
                "t": int(time.time() * 1000),
            }
            subject = f"aifactory.{self.config.site_id}.{self.config.ipc_name}.status"
            if self.nats.connected:
                await self.nats.nc.publish(subject, json.dumps(status).encode())

            await asyncio.sleep(5.0)

    async def stop(self):
        """Graceful shutdown."""
        self._running = False
        await self.opcua.disconnect()
        await self.nats.close()
        logger.info("Bridge stopped", ipc=self.config.ipc_name)


# =============================================================================
# Entry Point
# =============================================================================
async def main():
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer(),
        ],
    )

    config = load_config()
    bridge = OPCUANATSBridge(config)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bridge.stop()))

    await bridge.start()


if __name__ == "__main__":
    import uvloop
    uvloop.install()
    asyncio.run(main())
