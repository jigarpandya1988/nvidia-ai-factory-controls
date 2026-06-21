# System Architecture Overview

## NVIDIA AI Factory Controls — Distributed IPC Architecture

### 1. Introduction

The NVIDIA AI Factory represents a new class of data center purpose-built for AI workload processing. Unlike traditional data centers operating at 5–15 kW per rack, AI factories push **120–140 kW per rack** with NVIDIA GB200 NVL72 systems, requiring fundamentally different approaches to power delivery, thermal management, and operational control.

This document defines the control system architecture for managing these facilities using industrial-grade CODESYS PLCs on Linux IPCs, providing deterministic real-time control with enterprise cloud connectivity.

### 2. Design Principles

1. **Deterministic Control** — Critical loops (cooling, power, safety) execute in hard real-time on dedicated IPCs
2. **Defense in Depth** — Multiple independent safety layers, no single point of failure
3. **Scalable Architecture** — Add IPCs and I/O modules as facility grows
4. **Open Standards** — OPC UA, MQTT Sparkplug B, BACnet, Modbus — no vendor lock-in
5. **Digital Twin Ready** — All data exposed for NVIDIA Omniverse integration
6. **Cybersecurity by Design** — IEC 62443 zones and conduits, zero-trust networking

### 3. System Topology

```
                    ┌─────────────────────────────┐
                    │      CLOUD SERVICES          │
                    │  (Azure/AWS/NVIDIA DGX Cloud) │
                    └──────────────┬──────────────┘
                                   │ TLS 1.3 / MQTT
                    ┌──────────────┴──────────────┐
                    │       EDGE GATEWAY           │
                    │   (Ubuntu 22.04 + Docker)    │
                    │                              │
                    │  ┌─────────┐ ┌───────────┐  │
                    │  │MQTT Brkr│ │OPC UA Aggr│  │
                    │  └────┬────┘ └─────┬─────┘  │
                    │       │            │         │
                    │  ┌────┴────────────┴─────┐  │
                    │  │   Data Historian       │  │
                    │  │   (InfluxDB/TSDB)      │  │
                    │  └───────────────────────┘  │
                    └──────────────┬──────────────┘
                                   │ OPC UA / EtherCAT
                    ┌──────────────┼──────────────┐
          ┌─────────┤    CONTROL NETWORK (VLAN)   ├─────────┐
          │         └──────────────┬──────────────┘         │
          │                        │                        │
    ┌─────┴─────┐          ┌──────┴──────┐          ┌──────┴──────┐
    │  IPC-01   │          │   IPC-02    │          │   IPC-03    │
    │  POWER    │          │   COOLING   │          │   ENVIRON   │
    │           │          │             │          │             │
    │ Tasks:    │          │ Tasks:      │          │ Tasks:      │
    │ • PDU ctrl│          │ • CDU loops │          │ • Temp map  │
    │ • UPS mgmt│          │ • Pump VFDs │          │ • Humidity  │
    │ • Load bal│          │ • Valve ctrl│          │ • Airflow   │
    │ • Metering│          │ • Setpoints │          │ • Particul. │
    └─────┬─────┘          └──────┬──────┘          └──────┬──────┘
          │                        │                        │
    ┌─────┴─────┐          ┌──────┴──────┐          ┌──────┴──────┐
    │ Field I/O │          │  Field I/O  │          │  Field I/O  │
    │ EtherCAT  │          │  EtherCAT   │          │  Modbus TCP │
    │ Modules   │          │  Modules    │          │  BACnet/IP  │
    └───────────┘          └─────────────┘          └─────────────┘

                    ┌──────────────────────────────┐
                    │         IPC-04 SAFETY         │
                    │   (SIL2 / IEC 61508)         │
                    │                              │
                    │  • Emergency Power Off (EPO) │
                    │  • Fire suppression          │
                    │  • Leak detection            │
                    │  • Gas detection             │
                    │  • Seismic shutdown          │
                    │  • Safe-state management     │
                    └──────────────────────────────┘
```

### 4. IPC Specifications

| IPC | Function | Hardware | OS | Cycle Time | I/O Protocol |
|-----|----------|----------|-----|-----------|--------------|
| IPC-01 | Power Distribution | Beckhoff CX5140 | Linux RT | 10 ms | EtherCAT |
| IPC-02 | Cooling Control | Beckhoff CX5240 | Linux RT | 5 ms | EtherCAT |
| IPC-03 | Environment Monitor | WAGO PFC200 | Linux | 100 ms | Modbus TCP |
| IPC-04 | Safety Systems | Beckhoff CX5240 + TwinSAFE | Linux RT | 2 ms | FSoE/EtherCAT |

### 5. Communication Architecture

#### 5.1 Inter-IPC Communication (OPC UA)

All IPCs expose OPC UA servers (built into CODESYS runtime). The edge gateway runs an OPC UA aggregating server that provides a unified namespace.

```
IPC-01 (opc.tcp://ipc-power:4840)     ─┐
IPC-02 (opc.tcp://ipc-cooling:4840)    ─┼─→ OPC UA Aggregator → Cloud
IPC-03 (opc.tcp://ipc-environ:4840)    ─┤
IPC-04 (opc.tcp://ipc-safety:4840)     ─┘
```

#### 5.2 Cloud Connectivity (MQTT Sparkplug B)

```
Topic Structure:
  spBv1.0/AIFactory/{site_id}/DDATA/{ipc_name}
  spBv1.0/AIFactory/{site_id}/DCMD/{ipc_name}
  spBv1.0/AIFactory/{site_id}/NBIRTH/{ipc_name}
```

#### 5.3 Field Bus Networks

| Network | Purpose | Speed | Topology |
|---------|---------|-------|----------|
| EtherCAT | Real-time I/O | 100 Mbps | Line/Ring |
| Modbus TCP | Legacy sensors | 100 Mbps | Star |
| BACnet/IP | HVAC integration | 100 Mbps | Star |
| PROFINET | Drive control | 1 Gbps | Star |

### 6. Software Architecture (per IPC)

Each CODESYS IPC runs the following task configuration:

```
┌─────────────────────────────────────────┐
│           CODESYS Runtime (Linux)        │
├─────────────────────────────────────────┤
│  Task: Safety_Task      (Priority 0, 2ms)│  ← IPC-04 only
│  Task: Control_Task     (Priority 1, 5ms)│  ← Main control loop
│  Task: Communication_Task (Priority 5, 100ms)│  ← OPC UA publish
│  Task: Diagnostic_Task  (Priority 10, 1s) │  ← Health monitoring
├─────────────────────────────────────────┤
│  Libraries:                              │
│  • CAA_Memory, CAA_File                  │
│  • SysCom, SysSocket                    │
│  • IoStandard, IoConfig                 │
│  • SM3_Basic (motion, if needed)        │
│  • CmpOPCUAServer                       │
│  • Alarm Management                     │
├─────────────────────────────────────────┤
│  Linux OS (PREEMPT_RT kernel)           │
│  • Docker (edge services)               │
│  • Systemd service management           │
│  • NTP/PTP time synchronization         │
└─────────────────────────────────────────┘
```

### 7. Key Control Loops

#### 7.1 Cooling Control (IPC-02)

```
Setpoint: GPU Junction Temp ≤ 83°C
          Coolant Supply Temp = 35°C ± 2°C

Sensors → PID Controller → VFD Pump Speed + Valve Position
  │                              │
  └── Feedforward from GPU Power ─┘ (predictive adjustment)
```

#### 7.2 Power Management (IPC-01)

```
Grid Feed → ATS → UPS → 800VDC Bus → PDU → Rack
                                        │
                    Load Balancing ←─────┘
                    Peak Shaving
                    Power Quality Monitoring
```

### 8. NVIDIA-Specific Integration Points

| Integration | Protocol | Purpose |
|-------------|----------|---------|
| GPU Telemetry (DCGM) | REST/gRPC | GPU temp, power, utilization |
| NVSwitch Fabric | SNMP/REST | Network health monitoring |
| BMC/IPMI | IPMI/Redfish | Server hardware health |
| NVIDIA Air | API | Network simulation |
| Omniverse | USD/REST | Digital twin sync |
| Base Command | API | Workload orchestration awareness |

### 9. Scalability Model

```
Small:   1 MW facility  →  4 IPCs,  ~2,000 I/O points
Medium:  10 MW facility →  12 IPCs, ~8,000 I/O points
Large:   100 MW facility → 40+ IPCs, ~30,000 I/O points
```

Each IPC handles up to 1,000 I/O points. IPCs are added in functional groups as the facility scales.

### 10. Next Steps

1. Detailed I/O list per IPC (see `docs/architecture/io-lists/`)
2. Control narrative per subsystem (see `docs/architecture/control-narratives/`)
3. Network design with VLAN segmentation (see `config/network/`)
4. Safety analysis (SIL assessment) for IPC-04
5. CODESYS library development plan
