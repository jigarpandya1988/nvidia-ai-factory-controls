# Network Topology — NVIDIA AI Factory Controls

## VLAN Segmentation

| VLAN ID | Name | Subnet | Purpose |
|---------|------|--------|---------|
| 100 | Control | 192.168.100.0/24 | IPC-to-IPC, OPC UA |
| 110 | EtherCAT | (Layer 2 only) | Real-time field I/O |
| 200 | Edge/DMZ | 192.168.200.0/24 | Edge gateway services |
| 300 | Management | 192.168.300.0/24 | SSH, CODESYS IDE access |
| 400 | IT/Cloud | 10.0.0.0/16 | Cloud connectivity (outbound only) |

## IP Address Allocation

### VLAN 100 — Control Network

| IP Address | Device | Role |
|------------|--------|------|
| 192.168.100.1 | Switch/Router | Gateway |
| 192.168.100.10 | IPC-01 | Power Control |
| 192.168.100.11 | IPC-01 (redundant) | Power Control (backup NIC) |
| 192.168.100.20 | IPC-02 | Cooling Control |
| 192.168.100.21 | IPC-02 (redundant) | Cooling Control (backup NIC) |
| 192.168.100.30 | IPC-03 | Environment Monitor |
| 192.168.100.40 | IPC-04 | Safety Systems |
| 192.168.100.41 | IPC-04 (redundant) | Safety (backup NIC) |
| 192.168.100.50-59 | Modbus devices | Energy meters, UPS |
| 192.168.100.60-69 | BACnet devices | HVAC controllers |
| 192.168.100.100 | Edge Gateway (primary) | OPC UA aggregator |
| 192.168.100.101 | Edge Gateway (standby) | Failover |

### VLAN 200 — Edge/DMZ

| IP Address | Device | Service |
|------------|--------|---------|
| 192.168.200.10 | Edge Server | MQTT Broker (EMQX) |
| 192.168.200.11 | Edge Server | InfluxDB |
| 192.168.200.12 | Edge Server | Grafana |
| 192.168.200.13 | Edge Server | Sparkplug Bridge |

## Firewall Rules

### Control → Edge (VLAN 100 → 200)

| Source | Destination | Port | Protocol | Action |
|--------|-------------|------|----------|--------|
| 192.168.100.0/24 | 192.168.200.10 | 4840 | TCP | ALLOW (OPC UA) |
| 192.168.100.0/24 | 192.168.200.10 | 1883 | TCP | ALLOW (MQTT internal) |
| Any | Any | Any | Any | DENY |

### Edge → Cloud (VLAN 200 → Internet)

| Source | Destination | Port | Protocol | Action |
|--------|-------------|------|----------|--------|
| 192.168.200.13 | *.azure-devices.net | 8883 | TCP | ALLOW (MQTTS) |
| 192.168.200.13 | *.amazonaws.com | 8883 | TCP | ALLOW (MQTTS) |
| 192.168.200.12 | *.grafana.net | 443 | TCP | ALLOW (Grafana Cloud) |
| Any | Any | Any | Any | DENY |

### Cloud → Edge (Inbound) — BLOCKED

No inbound connections from cloud to edge. All communication is initiated outbound.

## Physical Topology

```
                        ┌─────────────────┐
                        │  Core Switch    │
                        │  (L3, managed)  │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────┴──────┐  ┌───────┴───────┐  ┌──────┴─────────┐
    │ Control Switch │  │  Edge Switch  │  │  Mgmt Switch   │
    │  VLAN 100/110  │  │   VLAN 200    │  │   VLAN 300     │
    │  (managed, RT) │  │   (managed)   │  │   (managed)    │
    └───┬───┬───┬────┘  └───────┬───────┘  └────────────────┘
        │   │   │               │
   IPC-01  IPC-02  ...    Edge Server
```

## EtherCAT Topology (per IPC)

```
IPC-01 (EtherCAT Master)
  │
  ├── EK1100 (Bus Coupler) — Switchgear Room A
  │   ├── EL3064 (4x AI, 0-10V) — Voltage monitoring
  │   ├── EL3064 (4x AI, 0-10V) — Current monitoring
  │   ├── EL1809 (16x DI) — Breaker status
  │   ├── EL2809 (16x DO) — Breaker control
  │   └── EL6695 (PTP Sync) — Time synchronization
  │
  └── EK1100 (Bus Coupler) — Switchgear Room B
      ├── EL3064 (4x AI) — UPS monitoring
      ├── EL1809 (16x DI) — Status inputs
      └── EL4004 (4x AO) — Setpoint outputs
```
