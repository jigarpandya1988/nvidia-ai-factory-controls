"""
Unit Tests — OPC UA ↔ NATS Bridge
====================================
Tests the core bridge logic: reading OPC UA, publishing to NATS,
handling commands, and peer exchange.

Run: pytest tests/python/edge_gateway/test_opcua_nats_bridge.py -v
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Import from source (adjust path if needed)
import sys
sys.path.insert(0, 'src/edge-gateway/nats-bridge/bridges')
from opcua_nats_bridge import (
    BridgeConfig,
    OPCUAManager,
    NATSManager,
    OPCUANATSBridge,
    load_config,
)


# =============================================================================
# OPCUAManager Tests
# =============================================================================

class TestOPCUAManager:
    """Tests for OPC UA client manager."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_opcua_client):
        """Should connect to OPC UA server."""
        with patch('opcua_nats_bridge.OPCUAClient', return_value=mock_opcua_client):
            manager = OPCUAManager("opc.tcp://localhost:4840", "test-ipc")
            await manager.connect()

            assert manager.connected is True
            mock_opcua_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_retry_on_failure(self, mock_opcua_client):
        """Should retry connection on failure."""
        mock_opcua_client.connect = AsyncMock(
            side_effect=[ConnectionError("refused"), None]  # Fail first, succeed second
        )

        with patch('opcua_nats_bridge.OPCUAClient', return_value=mock_opcua_client):
            manager = OPCUAManager("opc.tcp://localhost:4840", "test-ipc")
            await manager.connect()

            assert manager.connected is True
            assert mock_opcua_client.connect.call_count == 2

    @pytest.mark.asyncio
    async def test_read_node_returns_value(self, mock_opcua_client):
        """Should read a value from OPC UA node."""
        with patch('opcua_nats_bridge.OPCUAClient', return_value=mock_opcua_client):
            manager = OPCUAManager("opc.tcp://localhost:4840", "test-ipc")
            await manager.connect()

            value = await manager.read_node("ns=4;s=Test.Temp")

            assert value == 35.0

    @pytest.mark.asyncio
    async def test_read_node_returns_none_when_disconnected(self):
        """Should return None if not connected."""
        manager = OPCUAManager("opc.tcp://localhost:4840", "test-ipc")
        manager.connected = False

        value = await manager.read_node("ns=4;s=Test.Temp")

        assert value is None

    @pytest.mark.asyncio
    async def test_read_all_batch(self, mock_opcua_client):
        """Should batch-read multiple nodes."""
        with patch('opcua_nats_bridge.OPCUAClient', return_value=mock_opcua_client):
            manager = OPCUAManager("opc.tcp://localhost:4840", "test-ipc")
            await manager.connect()

            nodes = ["ns=4;s=Test.Temp1", "ns=4;s=Test.Temp2"]
            results = await manager.read_all(nodes)

            assert len(results) == 2
            assert all(v == 35.0 for v in results.values())

    @pytest.mark.asyncio
    async def test_write_node_success(self, mock_opcua_client):
        """Should write value to OPC UA node."""
        node_mock = AsyncMock()
        node_mock.write_value = AsyncMock()
        mock_opcua_client.get_node.return_value = node_mock

        with patch('opcua_nats_bridge.OPCUAClient', return_value=mock_opcua_client):
            manager = OPCUAManager("opc.tcp://localhost:4840", "test-ipc")
            await manager.connect()

            success = await manager.write_node("ns=4;s=Test.SP", 42.0)

            assert success is True
            node_mock.write_value.assert_called_once_with(42.0)


# =============================================================================
# NATSManager Tests
# =============================================================================

class TestNATSManager:
    """Tests for NATS publish/subscribe manager."""

    @pytest.mark.asyncio
    async def test_publish_telemetry_format(self, mock_nats_client):
        """Should publish telemetry with correct subject and payload."""
        nc, js = mock_nats_client

        with patch('nats.connect', return_value=nc):
            manager = NATSManager("nats://localhost:4222", "cooling", "us-west-01")
            manager.nc = nc
            manager.js = js
            manager.connected = True

            await manager.publish_telemetry("CDU_01.SupplyTemp", 35.2, quality=0)

            js.publish.assert_called_once()
            call_args = js.publish.call_args
            subject = call_args[0][0]
            payload = json.loads(call_args[0][1])

            assert subject == "aifactory.us-west-01.cooling.telemetry.CDU_01.SupplyTemp"
            assert payload["v"] == 35.2
            assert payload["q"] == 0
            assert "t" in payload  # Timestamp present

    @pytest.mark.asyncio
    async def test_publish_peer_uses_core_nats(self, mock_nats_client):
        """Peer exchange should use core NATS (not JetStream) for speed."""
        nc, js = mock_nats_client

        manager = NATSManager("nats://localhost:4222", "cooling", "us-west-01")
        manager.nc = nc
        manager.js = js
        manager.connected = True

        await manager.publish_peer({"ipc": "cooling", "healthy": True})

        # Should use nc.publish (core), not js.publish (JetStream)
        nc.publish.assert_called_once()
        subject = nc.publish.call_args[0][0]
        assert subject == "aifactory.us-west-01.cooling.peer"

    @pytest.mark.asyncio
    async def test_publish_alarm_uses_jetstream(self, mock_nats_client):
        """Alarms should use JetStream for guaranteed delivery."""
        nc, js = mock_nats_client

        manager = NATSManager("nats://localhost:4222", "cooling", "us-west-01")
        manager.nc = nc
        manager.js = js
        manager.connected = True

        await manager.publish_alarm({"severity": 4, "message": "test"})

        js.publish.assert_called_once()
        subject = js.publish.call_args[0][0]
        assert "alarms.4" in subject

    @pytest.mark.asyncio
    async def test_subscribe_commands(self, mock_nats_client):
        """Should subscribe to command subjects for this IPC."""
        nc, js = mock_nats_client

        manager = NATSManager("nats://localhost:4222", "cooling", "us-west-01")
        manager.nc = nc
        manager.connected = True

        callback = AsyncMock()
        await manager.subscribe_commands(callback)

        nc.subscribe.assert_called_once()
        subject = nc.subscribe.call_args[0][0]
        assert subject == "aifactory.us-west-01.cooling.commands.>"


# =============================================================================
# Bridge Integration Tests
# =============================================================================

class TestOPCUANATSBridge:
    """Integration tests for the full bridge."""

    def test_load_config_from_env(self, monkeypatch):
        """Should load config from environment variables."""
        monkeypatch.setenv("IPC_NAME", "safety")
        monkeypatch.setenv("SITE_ID", "eu-west-02")
        monkeypatch.setenv("IPC_OPCUA_URL", "opc.tcp://10.0.0.40:4840")
        monkeypatch.setenv("NATS_URL", "nats://broker:4222")
        monkeypatch.setenv("POLL_INTERVAL_MS", "200")

        config = load_config()

        assert config.ipc_name == "safety"
        assert config.site_id == "eu-west-02"
        assert config.opcua_url == "opc.tcp://10.0.0.40:4840"
        assert config.poll_interval_ms == 200

    @pytest.mark.asyncio
    async def test_command_handling(self, sample_bridge_config, mock_opcua_client):
        """Should write OPC UA on NATS command receive."""
        config = BridgeConfig(**sample_bridge_config)
        bridge = OPCUANATSBridge(config)

        # Mock OPC UA write
        node_mock = AsyncMock()
        node_mock.write_value = AsyncMock()
        mock_opcua_client.get_node.return_value = node_mock

        bridge.opcua.client = mock_opcua_client
        bridge.opcua.connected = True
        bridge.opcua._node_cache = {}

        # Simulate NATS command message
        msg = MagicMock()
        msg.subject = "aifactory.us-west-01.cooling.commands.CDU_01.SupplyTempSP"
        msg.data = json.dumps({"value": 37.0}).encode()
        msg.reply = None

        await bridge._on_command(msg)

        # Verify OPC UA write was called
        node_mock.write_value.assert_called_once_with(37.0)

    @pytest.mark.asyncio
    async def test_peer_data_stored(self):
        """Should store received peer data by IPC name."""
        config = BridgeConfig(ipc_name="cooling", site_id="test")
        bridge = OPCUANATSBridge(config)

        msg = MagicMock()
        msg.data = json.dumps({"ipc": "safety", "healthy": True, "t": 123}).encode()

        await bridge._on_peer_data(msg)

        assert "safety" in bridge._peer_data
        assert bridge._peer_data["safety"]["healthy"] is True
