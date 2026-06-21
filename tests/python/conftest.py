"""
Pytest Configuration & Shared Fixtures
========================================
NVIDIA AI Factory Controls — Python Tests

Run: pytest tests/python/ -v
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_opcua_client():
    """Mock asyncua OPC UA client."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_node = MagicMock()

    # Mock node that returns a value
    node = AsyncMock()
    node.read_value = AsyncMock(return_value=35.0)
    client.get_node.return_value = node

    return client


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    nc = AsyncMock()
    nc.publish = AsyncMock()
    nc.subscribe = AsyncMock()
    nc.close = AsyncMock()
    nc.is_connected = True

    # Mock JetStream context
    js = AsyncMock()
    js.publish = AsyncMock()
    js.subscribe = AsyncMock()
    nc.jetstream = MagicMock(return_value=js)

    return nc, js


@pytest.fixture
def sample_bridge_config():
    """Sample bridge configuration for testing."""
    return {
        "ipc_name": "cooling",
        "site_id": "us-west-01",
        "opcua_url": "opc.tcp://localhost:4840",
        "nats_url": "nats://localhost:4222",
        "nats_creds": "",
        "poll_interval_ms": 100,
        "peer_interval_ms": 5,
        "publish_nodes": [
            {"node_id": "ns=4;s=Test.SupplyTemp", "tag": "CDU_01.SupplyTemp"},
            {"node_id": "ns=4;s=Test.PumpSpeed", "tag": "CDU_01.PumpSpeed"},
        ],
        "command_nodes": [
            {"node_id": "ns=4;s=Test.Cmd_SP", "tag": "CDU_01.SupplyTempSP"},
        ],
        "subscribe_subjects": ["aifactory.us-west-01.safety.peer"],
    }


@pytest.fixture
def sample_telemetry_message():
    """Sample NATS telemetry message payload."""
    return json.dumps({
        "v": 35.2,
        "q": 0,
        "t": 1717000000000,
    }).encode()


@pytest.fixture
def sample_alarm_event():
    """Sample alarm event for AWS forwarder."""
    return {
        "ipc": "cooling",
        "severity": 4,
        "source": "CDU_01",
        "message": "Supply temperature exceeded 40°C",
        "timestamp": 1717000000000,
        "value": 41.3,
        "threshold": 40.0,
    }
