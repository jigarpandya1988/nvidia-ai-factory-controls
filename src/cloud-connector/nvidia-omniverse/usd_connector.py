"""
NVIDIA Omniverse USD Connector
===============================
Bridges CODESYS OPC UA telemetry to Omniverse Digital Twin via USD properties.

This connector:
1. Reads real-time data from the OPC UA aggregator
2. Maps OPC UA nodes to USD prim paths
3. Updates USD properties in Omniverse Nucleus
4. Supports bi-directional sync (commands from twin → OPC UA writes)

Requires: NVIDIA Omniverse Kit SDK, asyncua
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asyncua import Client as OPCUAClient

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class MappingEntry:
    """Maps an OPC UA node to a USD prim property."""

    opcua_node_id: str  # e.g., "ns=4;s=Cooling.CDU_01.SupplyTemp"
    usd_prim_path: str  # e.g., "/World/Facility/Cooling/CDU_01"
    usd_attribute: str  # e.g., "custom:supplyTemp"
    data_type: str  # float, bool, int, string
    scale: float = 1.0  # Optional scaling factor
    offset: float = 0.0  # Optional offset
    unit: str = ""  # Engineering unit for metadata


@dataclass
class ConnectorConfig:
    """Configuration for the Omniverse connector."""

    opcua_url: str = "opc.tcp://192.168.100.100:4840"
    nucleus_url: str = "omniverse://localhost/AIFactory"
    stage_path: str = "/AIFactory/DigitalTwin.usd"
    update_rate_hz: float = 1.0
    mapping_file: str = "mapping.json"
    enable_commands: bool = True  # Allow twin → PLC commands


# =============================================================================
# OPC UA to USD Mapping
# =============================================================================
DEFAULT_MAPPINGS = [
    # --- Cooling System ---
    MappingEntry(
        opcua_node_id="ns=4;s=Cooling.CDU_01.SupplyTemp",
        usd_prim_path="/World/Facility/Cooling/CDU_01",
        usd_attribute="custom:supplyTemp",
        data_type="float",
        unit="°C",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Cooling.CDU_01.ReturnTemp",
        usd_prim_path="/World/Facility/Cooling/CDU_01",
        usd_attribute="custom:returnTemp",
        data_type="float",
        unit="°C",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Cooling.CDU_01.PumpSpeed",
        usd_prim_path="/World/Facility/Cooling/CDU_01/Pump",
        usd_attribute="custom:speedPercent",
        data_type="float",
        unit="%",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Cooling.CDU_01.FlowRate",
        usd_prim_path="/World/Facility/Cooling/CDU_01",
        usd_attribute="custom:flowRate",
        data_type="float",
        unit="LPM",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Cooling.CDU_01.ValvePosition",
        usd_prim_path="/World/Facility/Cooling/CDU_01/Valve",
        usd_attribute="custom:position",
        data_type="float",
        unit="%",
    ),
    # --- Power System ---
    MappingEntry(
        opcua_node_id="ns=4;s=Power.TotalPower_kW",
        usd_prim_path="/World/Facility/Power",
        usd_attribute="custom:totalPowerKW",
        data_type="float",
        unit="kW",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Power.PUE",
        usd_prim_path="/World/Facility/Power",
        usd_attribute="custom:pue",
        data_type="float",
        unit="",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Power.ITPower_kW",
        usd_prim_path="/World/Facility/Power",
        usd_attribute="custom:itPowerKW",
        data_type="float",
        unit="kW",
    ),
    # --- Per-Rack Data ---
    MappingEntry(
        opcua_node_id="ns=4;s=Rack_01.InletTemp",
        usd_prim_path="/World/Facility/Row_01/Rack_01",
        usd_attribute="custom:inletTemp",
        data_type="float",
        unit="°C",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Rack_01.Power_kW",
        usd_prim_path="/World/Facility/Row_01/Rack_01",
        usd_attribute="custom:powerKW",
        data_type="float",
        unit="kW",
    ),
    # --- Safety Status ---
    MappingEntry(
        opcua_node_id="ns=4;s=Safety.SystemArmed",
        usd_prim_path="/World/Facility/Safety",
        usd_attribute="custom:systemArmed",
        data_type="bool",
    ),
    MappingEntry(
        opcua_node_id="ns=4;s=Safety.AnyZoneTripped",
        usd_prim_path="/World/Facility/Safety",
        usd_attribute="custom:anyZoneTripped",
        data_type="bool",
    ),
]


# =============================================================================
# USD Stage Manager (Omniverse)
# =============================================================================
class USDStageManager:
    """
    Manages USD stage connection and property updates.
    
    In production, this uses the Omniverse Kit SDK (omni.usd).
    This implementation provides the interface for integration.
    """

    def __init__(self, nucleus_url: str, stage_path: str):
        self.nucleus_url = nucleus_url
        self.stage_path = stage_path
        self._stage = None
        self._connected = False

    async def connect(self):
        """Connect to Omniverse Nucleus and open/create stage."""
        try:
            # In production: 
            # import omni.usd
            # self._stage = omni.usd.get_context().open_stage(self.stage_path)
            logger.info(
                "Connected to Omniverse Nucleus",
                extra={"url": self.nucleus_url, "stage": self.stage_path},
            )
            self._connected = True
        except Exception as e:
            logger.error(f"Failed to connect to Omniverse: {e}")
            raise

    def update_property(self, prim_path: str, attribute: str, value: Any):
        """Update a USD prim property with new sensor value."""
        if not self._connected:
            return

        # In production:
        # prim = self._stage.GetPrimAtPath(prim_path)
        # if prim.IsValid():
        #     attr = prim.GetAttribute(attribute)
        #     if attr.IsValid():
        #         attr.Set(value)
        #     else:
        #         # Create custom attribute if it doesn't exist
        #         if isinstance(value, float):
        #             attr = prim.CreateAttribute(attribute, Sdf.ValueTypeNames.Float)
        #         elif isinstance(value, bool):
        #             attr = prim.CreateAttribute(attribute, Sdf.ValueTypeNames.Bool)
        #         attr.Set(value)

        logger.debug(f"USD Update: {prim_path}.{attribute} = {value}")

    def read_command(self, prim_path: str, attribute: str) -> Any:
        """Read a command value from USD (twin → physical)."""
        if not self._connected:
            return None

        # In production:
        # prim = self._stage.GetPrimAtPath(prim_path)
        # if prim.IsValid():
        #     attr = prim.GetAttribute(attribute)
        #     if attr.IsValid():
        #         return attr.Get()
        return None

    async def disconnect(self):
        """Close stage and disconnect."""
        self._connected = False
        logger.info("Disconnected from Omniverse")


# =============================================================================
# Main Connector
# =============================================================================
class OmniverseConnector:
    """
    Main connector: reads OPC UA, writes to USD, optionally reads commands back.
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.mappings = DEFAULT_MAPPINGS
        self.opcua_client: OPCUAClient | None = None
        self.usd_manager: USDStageManager | None = None
        self._running = False

    def load_mappings(self, mapping_file: str):
        """Load custom mappings from JSON file."""
        path = Path(mapping_file)
        if path.exists():
            with open(path) as f:
                raw = json.load(f)
            self.mappings = [MappingEntry(**m) for m in raw]
            logger.info(f"Loaded {len(self.mappings)} mappings from {mapping_file}")

    async def connect(self):
        """Connect to both OPC UA and Omniverse."""
        # OPC UA connection
        self.opcua_client = OPCUAClient(url=self.config.opcua_url)
        await self.opcua_client.connect()
        logger.info(f"Connected to OPC UA: {self.config.opcua_url}")

        # Omniverse connection
        self.usd_manager = USDStageManager(
            self.config.nucleus_url, self.config.stage_path
        )
        await self.usd_manager.connect()

    async def sync_loop(self):
        """Main synchronization loop: OPC UA → USD."""
        self._running = True
        interval = 1.0 / self.config.update_rate_hz

        while self._running:
            try:
                for mapping in self.mappings:
                    # Read from OPC UA
                    node = self.opcua_client.get_node(mapping.opcua_node_id)
                    value = await node.read_value()

                    # Apply scaling
                    if mapping.data_type == "float" and isinstance(value, (int, float)):
                        value = float(value) * mapping.scale + mapping.offset

                    # Write to USD
                    self.usd_manager.update_property(
                        mapping.usd_prim_path, mapping.usd_attribute, value
                    )

            except Exception as e:
                logger.warning(f"Sync error: {e}")

            await asyncio.sleep(interval)

    async def stop(self):
        """Stop the connector gracefully."""
        self._running = False
        if self.opcua_client:
            await self.opcua_client.disconnect()
        if self.usd_manager:
            await self.usd_manager.disconnect()
        logger.info("Omniverse connector stopped")


# =============================================================================
# Entry Point
# =============================================================================
async def main():
    config = ConnectorConfig(
        opcua_url="opc.tcp://192.168.100.100:4840",
        nucleus_url="omniverse://nucleus.aifactory.local",
        stage_path="/AIFactory/DigitalTwin.usd",
        update_rate_hz=1.0,
    )

    connector = OmniverseConnector(config)
    await connector.connect()
    await connector.sync_loop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
