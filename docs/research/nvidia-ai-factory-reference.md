# NVIDIA AI Factory — Research Notes

## Sources & Key Findings

### 1. NVIDIA AI Factory White Paper (Official)

**Source**: [NVIDIA AI Factory Overview](https://docs.nvidia.com/ai-enterprise/planning-resource/ai-factory-white-paper/latest/ai-factory-overview.html)

#### What is an AI Factory?

An AI Factory is a new type of data center designed specifically for processing and refining data into AI models and tokens. NVIDIA describes it as a facility that "takes in raw data and produces intelligence" — analogous to how traditional factories take in raw materials and produce goods.

Key characteristics:
- Purpose-built for AI training and inference workloads
- Requires fundamentally different infrastructure vs. traditional cloud/enterprise DC
- Designed around GPU-dense compute (NVIDIA DGX/HGX platforms)
- Requires specialized power, cooling, and networking

#### Reference Architecture Components

1. **Compute**: NVIDIA DGX SuperPOD with GB200 NVL72 (72 GPUs per rack)
2. **Networking**: NVIDIA Spectrum-X Ethernet or InfiniBand NDR (400 Gbps)
3. **Storage**: High-performance parallel file systems (NVIDIA BeeGFS, DDN, VAST)
4. **Software**: NVIDIA AI Enterprise, Base Command Manager
5. **Infrastructure**: Liquid cooling, 800VDC power, high-density racks

#### Power & Cooling Requirements

- **Per-rack power**: 120–140 kW (GB200 NVL72 configuration)
- **Cooling method**: Direct-to-chip liquid cooling (mandatory at these densities)
- **Coolant**: Propylene glycol/water mix, 35°C supply temperature
- **PUE target**: < 1.10 (vs. 1.3–1.5 for traditional air-cooled DC)
- **Power delivery**: 800VDC bus preferred for efficiency at scale

### 2. Ecosystem & Partners

**Source**: [NVIDIA AI Factory Ecosystem](https://docs.nvidia.com/ai-enterprise/planning-resource/ai-factory-white-paper/latest/ecosystem-architecture.html)

#### Infrastructure Partners (Controls-Relevant)

| Category | Partners |
|----------|----------|
| Cooling (CDU) | Vertiv, CoolIT, GRC, Motivair, Asetek |
| Power Distribution | Vertiv, Eaton, Schneider Electric, ABB |
| Rack/Enclosure | Vertiv, Rittal, nVent |
| BMS/DCIM | Schneider EcoStruxure, Siemens, Nlyte, Sunbird |
| Monitoring | Nagios, Zabbix, Datadog, custom DCCM |

#### Cooling Distribution Unit (CDU) Specifications

- **Capacity**: 350–1400 kW per CDU
- **Flow rate**: Up to 600 LPM
- **Supply temp**: 32–40°C (facility water to CDU)
- **Delta-T**: 10–15°C across rack
- **Redundancy**: N+1 CDU configuration
- **Control interface**: Modbus TCP / BACnet / OPC UA

### 3. Digital Twin Integration (NVIDIA Omniverse)

NVIDIA promotes using Omniverse to create digital twins of AI factories for:
- **Design validation** — Test layouts, airflow, cooling before construction
- **Operational optimization** — Real-time 3D visualization of facility state
- **Predictive maintenance** — AI-driven anomaly detection on sensor data
- **What-if scenarios** — Simulate failures, capacity changes

#### Data Flow: Physical → Digital Twin

```
Physical Sensors → CODESYS IPCs → OPC UA → Edge Gateway → 
  → USD Connector → Omniverse Nucleus → Digital Twin Visualization
```

The USD (Universal Scene Description) format is used to represent the facility in 3D. Sensor data is mapped to USD properties for real-time animation.

### 4. Operational Technology (OT) Requirements

Based on NVIDIA reference designs and industry standards for high-density DC:

#### Monitoring Points per Rack (120 kW liquid-cooled)

| Category | Points | Type |
|----------|--------|------|
| Power (per PDU) | 12 | AI (current), DI (status) |
| Coolant temperature | 4 | AI (PT1000/NTC) |
| Coolant flow | 2 | AI (pulse/4-20mA) |
| Coolant pressure | 4 | AI (4-20mA) |
| Leak detection | 2 | DI (zone cable) |
| Door/access | 2 | DI (contact) |
| GPU telemetry | 72 | Software (DCGM API) |
| **Total per rack** | **~98** | |

For a 1,000-rack facility: **~100,000 physical I/O points** + software telemetry

#### Control Outputs per Rack Row (typical)

| Category | Points | Type |
|----------|--------|------|
| CDU pump speed | 2 | AO (4-20mA / VFD) |
| CDU valve position | 4 | AO (4-20mA) |
| Isolation valve | 2 | DO (on/off) |
| Emergency shutoff | 1 | DO (fail-safe) |

### 5. NVIDIA Job Roles — AI Factory Operations

From NVIDIA careers (searched May 2026):

#### AI Factory Deployment Engineer
- Deploy and commission AI factory infrastructure
- Work with cooling, power, and network systems
- Integrate GPU clusters with facility infrastructure
- Monitor and optimize PUE and cooling efficiency

#### Data Center Controls Engineer (inferred from industry)
- Design and implement BMS/EPMS control systems
- Program PLCs for cooling and power management
- Commission CDU control loops
- Integrate with DCIM platforms

#### Key Skills Referenced
- PLC programming (Siemens, Schneider, CODESYS)
- SCADA/HMI development
- OPC UA, Modbus, BACnet protocols
- Liquid cooling systems
- High-voltage DC power distribution
- Python/scripting for automation
- Cloud platforms (Azure IoT, AWS IoT)

### 6. Power Architecture Details

#### 800VDC Distribution (Emerging Standard)

```
Utility Feed (13.8 kV) → Step-down Transformer → 
  → Active Rectifier (AC→DC) → 800VDC Bus →
    → Point-of-Load Converters (48VDC to GPU) 
```

Benefits:
- 2–3% efficiency gain over AC distribution
- Fewer conversion stages
- Smaller conductors (higher voltage = lower current)
- Direct battery integration (no inverter needed)

#### Traditional 480VAC (Still Common)

```
Utility Feed → ATS → UPS → PDU (480V→208V) → Rack PDU → Server PSU
```

### 7. Safety Systems Requirements

| System | Standard | Response Time |
|--------|----------|---------------|
| Emergency Power Off (EPO) | NFPA 70 | < 100 ms |
| Fire Detection/Suppression | NFPA 75/76 | < 10 s (detection) |
| Leak Detection | Custom | < 1 s (detection) |
| Gas Detection (refrigerant) | EN 378 | < 30 s |
| Seismic Shutdown | IBC/ASCE 7 | < 500 ms |
| Thermal Runaway | UL 9540A | < 5 s |

### 8. Industry Trends (2025–2026)

1. **Convergence of IT and OT** — GPU telemetry feeding into PLC control decisions
2. **AI-driven controls** — ML models for predictive cooling setpoint optimization
3. **Modular/prefab** — Factory-built, pre-commissioned cooling and power modules
4. **Sustainability** — Waste heat recovery, free cooling optimization
5. **Autonomous operations** — Reducing human intervention through AI + digital twin
6. **Edge AI for controls** — Running inference models on the control layer itself

---

## Implications for This Project

1. **CODESYS is well-positioned** — Open platform, Linux-native, OPC UA built-in
2. **Scale demands distributed architecture** — No single PLC can handle 100K+ I/O
3. **Cloud connectivity is mandatory** — For DCIM, digital twin, fleet management
4. **Safety is critical** — Liquid cooling + high voltage = significant hazard potential
5. **GPU telemetry integration** — Must bridge IT (REST/gRPC) and OT (OPC UA/Modbus)
6. **Predictive control** — Opportunity to run ML inference on edge for optimization
