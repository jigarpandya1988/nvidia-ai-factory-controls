# Cloud Connectivity Architecture

## Overview

The cloud connectivity layer bridges the operational technology (OT) control network with enterprise IT systems, DCIM platforms, and NVIDIA's digital twin infrastructure. It provides secure, reliable telemetry export and remote command capability while maintaining strict network segmentation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUD PLATFORMS                              │
│                                                                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │  Azure IoT   │  │ NVIDIA Omniverse │  │   DCIM Platform  │   │
│  │    Hub       │  │  (Digital Twin)  │  │  (Nlyte/Sunbird) │   │
│  └──────┬───────┘  └────────┬────────┘  └────────┬─────────┘   │
│         │                   │                     │              │
│         │    MQTT/AMQP      │    USD/REST         │   REST API   │
│         │    TLS 1.3        │    TLS 1.3          │   TLS 1.3    │
└─────────┼───────────────────┼─────────────────────┼──────────────┘
          │                   │                     │
┌─────────┼───────────────────┼─────────────────────┼──────────────┐
│         │          DMZ / EDGE GATEWAY              │              │
│         │                                         │              │
│  ┌──────┴───────────────────┴─────────────────────┴──────────┐  │
│  │                    EDGE SERVER                              │  │
│  │              (Ubuntu 22.04 + Docker)                        │  │
│  │                                                            │  │
│  │  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │  MQTT Broker   │  │  OPC UA      │  │  Sparkplug   │  │  │
│  │  │  (EMQX)       │  │  Aggregator  │  │  B Engine    │  │  │
│  │  └───────┬────────┘  └──────┬───────┘  └──────┬───────┘  │  │
│  │          │                  │                  │           │  │
│  │  ┌───────┴──────────────────┴──────────────────┴───────┐  │  │
│  │  │              Data Pipeline                           │  │  │
│  │  │  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │  │  │
│  │  │  │InfluxDB  │  │ Telegraf  │  │ Node-RED /      │  │  │  │
│  │  │  │(TSDB)    │  │(collector)│  │ Custom Python   │  │  │  │
│  │  │  └──────────┘  └───────────┘  └─────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                    OPC UA (encrypted)                             │
│                              │                                    │
└──────────────────────────────┼────────────────────────────────────┘
                               │
┌──────────────────────────────┼────────────────────────────────────┐
│                    CONTROL NETWORK (isolated VLAN)                 │
│                              │                                    │
│     IPC-01 ──── IPC-02 ──── IPC-03 ──── IPC-04                  │
│     (Power)     (Cooling)   (Environ)   (Safety)                 │
└───────────────────────────────────────────────────────────────────┘
```

## MQTT / Sparkplug B Design

### Topic Namespace

```
spBv1.0/AIFactory/
├── {site_id}/
│   ├── NBIRTH/{node_id}          # Node birth certificate
│   ├── NDEATH/{node_id}          # Node death (LWT)
│   ├── NDATA/{node_id}           # Node-level data
│   ├── NCMD/{node_id}            # Node-level commands
│   ├── DBIRTH/{node_id}/{device} # Device birth
│   ├── DDEATH/{node_id}/{device} # Device death
│   ├── DDATA/{node_id}/{device}  # Device data (telemetry)
│   └── DCMD/{node_id}/{device}   # Device commands
```

### Node/Device Mapping

| Sparkplug Node | Sparkplug Device | Physical |
|----------------|-----------------|----------|
| EdgeGateway_01 | IPC_Power | IPC-01 |
| EdgeGateway_01 | IPC_Cooling | IPC-02 |
| EdgeGateway_01 | IPC_Environment | IPC-03 |
| EdgeGateway_01 | IPC_Safety | IPC-04 |
| EdgeGateway_01 | CDU_01 ... CDU_08 | CDU units |
| EdgeGateway_01 | PDU_01 ... PDU_48 | PDU units |

### Metric Definitions (Sparkplug B)

```json
{
  "timestamp": 1717000000000,
  "metrics": [
    {
      "name": "Cooling/CDU_01/SupplyTemp",
      "alias": 1001,
      "timestamp": 1717000000000,
      "dataType": "Float",
      "value": 34.8,
      "properties": {
        "engUnit": {"type": "String", "value": "°C"},
        "engLow": {"type": "Float", "value": 20.0},
        "engHigh": {"type": "Float", "value": 50.0}
      }
    },
    {
      "name": "Power/Total_IT_Load_kW",
      "alias": 2001,
      "timestamp": 1717000000000,
      "dataType": "Float",
      "value": 8542.3
    },
    {
      "name": "Power/PUE",
      "alias": 2010,
      "timestamp": 1717000000000,
      "dataType": "Float",
      "value": 1.08
    }
  ]
}
```

## OPC UA Information Model

### Namespace Structure

```
Root
├── Objects
│   ├── AIFactory
│   │   ├── Site_US_West_01
│   │   │   ├── PowerSystem
│   │   │   │   ├── Utility_Feed_A
│   │   │   │   ├── Utility_Feed_B
│   │   │   │   ├── UPS_01 ... UPS_04
│   │   │   │   ├── PDU_01 ... PDU_48
│   │   │   │   └── Metrics (PUE, TotalPower, etc.)
│   │   │   ├── CoolingSystem
│   │   │   │   ├── CDU_01 ... CDU_08
│   │   │   │   ├── CoolingTower_01 ... CT_04
│   │   │   │   ├── PumpGroup_01 ... PG_04
│   │   │   │   └── Metrics (DeltaT, FlowTotal, etc.)
│   │   │   ├── Environment
│   │   │   │   ├── Zone_01 ... Zone_12
│   │   │   │   └── Metrics (AvgTemp, Humidity, etc.)
│   │   │   └── Safety
│   │   │       ├── EPO_System
│   │   │       ├── FireDetection
│   │   │       ├── LeakDetection
│   │   │       └── SystemStatus
```

## NVIDIA Omniverse Integration

### Digital Twin Data Flow

```
CODESYS IPC → OPC UA → Edge Gateway → USD Connector → Omniverse Nucleus
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │  USD Stage    │
                                    │               │
                                    │ /World/       │
                                    │   /Facility/  │
                                    │     /Row_01/  │
                                    │       /Rack_01│
                                    │         .temp │
                                    │         .power│
                                    │         .flow │
                                    └───────────────┘
```

### USD Property Mapping

| OPC UA Node | USD Prim Path | USD Property |
|-------------|---------------|--------------|
| CDU_01.SupplyTemp | /Facility/Cooling/CDU_01 | custom:supplyTemp |
| CDU_01.PumpSpeed | /Facility/Cooling/CDU_01/Pump | custom:speedPercent |
| Rack_01.Power | /Facility/Row_01/Rack_01 | custom:powerKW |
| Rack_01.InletTemp | /Facility/Row_01/Rack_01 | custom:inletTemp |

### Omniverse Kit Extension (Python)

```python
# Simplified USD connector for CODESYS OPC UA → Omniverse
import asyncio
from asyncua import Client
import omni.usd

class CoolingTwinConnector:
    def __init__(self, opcua_url: str, usd_stage_path: str):
        self.opcua_url = opcua_url
        self.stage = omni.usd.get_context().get_stage()
    
    async def sync_loop(self):
        async with Client(url=self.opcua_url) as client:
            while True:
                # Read CDU data from OPC UA
                supply_temp = await client.get_node("ns=4;s=CDU_01.SupplyTemp").read_value()
                pump_speed = await client.get_node("ns=4;s=CDU_01.PumpSpeed").read_value()
                
                # Update USD properties
                prim = self.stage.GetPrimAtPath("/Facility/Cooling/CDU_01")
                prim.GetAttribute("custom:supplyTemp").Set(supply_temp)
                prim.GetAttribute("custom:pumpSpeed").Set(pump_speed)
                
                await asyncio.sleep(1.0)  # 1 Hz update rate for visualization
```

## Security Architecture

### Network Zones (IEC 62443)

```
Zone 0: Field Network (EtherCAT, isolated)
  │
  ├── Conduit: IPC internal bus only
  │
Zone 1: Control Network (VLAN 100)
  │ IPCs communicate via OPC UA (encrypted, certificate-based)
  │
  ├── Conduit: Firewall (allow OPC UA 4840, deny all else)
  │
Zone 2: DMZ / Edge (VLAN 200)
  │ Edge gateway, MQTT broker, historian
  │
  ├── Conduit: Firewall (allow MQTT 8883 outbound only)
  │
Zone 3: Enterprise / Cloud
    DCIM, Omniverse, monitoring dashboards
```

### Authentication & Encryption

| Connection | Auth Method | Encryption |
|------------|-------------|-----------|
| OPC UA (IPC↔Edge) | X.509 certificates | AES-256 |
| MQTT (Edge↔Cloud) | Client certificates + token | TLS 1.3 |
| Omniverse | OAuth 2.0 + API key | TLS 1.3 |
| DCIM API | API key + mTLS | TLS 1.3 |

## Data Rates & Retention

| Data Type | Frequency | Volume (1000 racks) | Retention |
|-----------|-----------|---------------------|-----------|
| Control telemetry | 1 Hz | ~500 KB/s | 90 days (local) |
| Alarms/Events | On-change | ~10 KB/s | 7 years |
| Energy metering | 15 min | ~1 KB/s | 10 years |
| GPU telemetry | 10 Hz | ~5 MB/s | 30 days |
| Digital twin sync | 1 Hz | ~200 KB/s | Real-time only |

## Edge Gateway Docker Composition

```yaml
# docker-compose.yml for Edge Gateway
version: '3.8'
services:
  mqtt-broker:
    image: emqx/emqx:5.5
    ports:
      - "1883:1883"    # Internal MQTT
      - "8883:8883"    # MQTT over TLS (cloud)
      - "8083:8083"    # WebSocket
    volumes:
      - ./config/emqx:/opt/emqx/etc
      - ./certs:/opt/emqx/certs

  opcua-aggregator:
    build: ./opcua-aggregator
    ports:
      - "4840:4840"
    environment:
      - IPC_POWER_URL=opc.tcp://ipc-power:4840
      - IPC_COOLING_URL=opc.tcp://ipc-cooling:4840
      - IPC_ENVIRON_URL=opc.tcp://ipc-environ:4840
      - IPC_SAFETY_URL=opc.tcp://ipc-safety:4840

  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2

  telegraf:
    image: telegraf:1.30
    volumes:
      - ./config/telegraf:/etc/telegraf
    depends_on:
      - mqtt-broker
      - influxdb

  grafana:
    image: grafana/grafana:10.3
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana:/etc/grafana
      - grafana-data:/var/lib/grafana

  sparkplug-bridge:
    build: ./sparkplug-bridge
    depends_on:
      - mqtt-broker
      - opcua-aggregator
    environment:
      - CLOUD_MQTT_BROKER=mqtts://your-iot-hub.azure-devices.net:8883
      - SITE_ID=us-west-01

volumes:
  influxdb-data:
  grafana-data:
```

## Failover & Resilience

1. **Store-and-forward**: Edge gateway buffers telemetry during cloud outages (up to 72 hours)
2. **Local autonomy**: All control functions operate independently of cloud connectivity
3. **Redundant edge**: Active/standby edge gateway pair with shared storage
4. **Certificate rotation**: Automated cert renewal via ACME/EST protocol
5. **Watchdog**: Cloud connectivity watchdog triggers local alarm if disconnected > 5 min
