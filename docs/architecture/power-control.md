# IPC-01: Power Distribution Control

## Overview

IPC-01 manages the electrical power distribution system for the AI factory, from utility feed through to rack-level delivery. It handles load balancing, power quality monitoring, UPS management, and energy metering.

## Hardware Platform

- **Controller**: Beckhoff CX5140 (Intel Atom x5, quad-core, 4GB RAM)
- **OS**: Debian Linux with PREEMPT_RT kernel
- **Runtime**: CODESYS V3.5 SP20
- **I/O**: EtherCAT terminals (Beckhoff EL series)

## Functional Scope

### 1. Utility Feed Monitoring
- Grid voltage/frequency monitoring (3-phase)
- Power factor measurement
- Harmonic distortion analysis (THD)
- Automatic Transfer Switch (ATS) status and control

### 2. UPS Management
- Battery state-of-charge monitoring
- Load percentage tracking
- Bypass status management
- Runtime estimation
- Scheduled battery tests

### 3. 800VDC Bus Control
- Bus voltage regulation monitoring
- Rectifier status and load sharing
- Bus fault detection and isolation
- Battery direct-connect management

### 4. PDU Management
- Per-circuit breaker status
- Branch circuit current monitoring
- Load balancing across phases
- Thermal monitoring of busbars
- Remote circuit control (where equipped)

### 5. Energy Metering
- Real-time power consumption (kW)
- Energy accumulation (kWh)
- PUE calculation (IT load vs. total facility)
- Demand response readiness
- Carbon intensity tracking

## I/O List (Typical for 10 MW Block)

### Analog Inputs (AI)
| Signal | Count | Range | Description |
|--------|-------|-------|-------------|
| Grid Voltage (L1/L2/L3) | 6 | 0-600VAC | Utility feed monitoring |
| Grid Current (L1/L2/L3) | 6 | 0-5A CT | Utility feed current |
| Bus Voltage (800VDC) | 4 | 0-1000VDC | DC bus sections |
| PDU Current | 48 | 0-5A CT | Per-circuit monitoring |
| Temperature (busbar) | 24 | PT100 | Thermal monitoring |
| UPS Battery Voltage | 4 | 0-10V scaled | Battery health |
| Power Meter (Modbus) | 12 | Modbus TCP | Energy meters |

### Digital Inputs (DI)
| Signal | Count | Description |
|--------|-------|-------------|
| Circuit Breaker Status | 96 | Open/Closed feedback |
| ATS Position | 4 | Source A/B indication |
| UPS Status (alarm) | 8 | Fault/Warning/OK |
| Door Interlock | 12 | Switchgear access |
| Ground Fault | 8 | GFI trip indication |

### Digital Outputs (DO)
| Signal | Count | Description |
|--------|-------|-------------|
| ATS Transfer Command | 4 | Source selection |
| Circuit Breaker Trip | 16 | Remote trip (safety) |
| UPS Test Command | 4 | Battery test initiate |
| Alarm Relay | 8 | External alarm outputs |

### Analog Outputs (AO)
| Signal | Count | Range | Description |
|--------|-------|-------|-------------|
| Rectifier Setpoint | 4 | 4-20mA | DC bus voltage control |
| Load Shed Level | 4 | 4-20mA | Demand response |

## Control Strategies

### Load Balancing Algorithm
```
// Pseudocode - Structured Text
IF Phase_A_Load > (Average_Load * 1.15) THEN
    // Phase A overloaded by >15%
    Trigger_Rebalance_Advisory();
END_IF

// PUE Calculation (real-time)
PUE := Total_Facility_Power / IT_Equipment_Power;
```

### Power Quality Monitoring
- Voltage sag/swell detection (±10% threshold)
- Frequency deviation (±0.5 Hz)
- THD monitoring (< 5% target per IEEE 519)
- Transient recording (triggered capture)

### Demand Response
- Shed non-critical loads on utility signal
- Ramp GPU workloads down gracefully (via API to orchestrator)
- Battery pre-charge before peak periods
- Automatic recovery sequencing

## Communication Interfaces

| Interface | Protocol | Purpose |
|-----------|----------|---------|
| Energy Meters | Modbus TCP | Power/energy readings |
| UPS Systems | Modbus TCP / SNMP | UPS status & control |
| ATS Controllers | Modbus RTU | Transfer switch control |
| Rectifiers | CANopen / Modbus | DC bus control |
| IPC-02 (Cooling) | OPC UA | Power-to-cooling coordination |
| IPC-04 (Safety) | OPC UA + Hardwired | EPO integration |
| Edge Gateway | OPC UA | Cloud telemetry |

## Alarm Configuration

| Alarm | Priority | Action |
|-------|----------|--------|
| Utility Power Loss | Critical | Start generator, notify |
| UPS on Battery | High | Start timer, prepare shed |
| Bus Overvoltage (>850V) | Critical | Trip rectifier |
| Phase Imbalance >20% | Medium | Advisory, log |
| PUE > 1.15 | Low | Optimization advisory |
| Ground Fault | Critical | Isolate, EPO if needed |

## Task Configuration

```
Task: Power_Control_Fast    Priority: 1    Cycle: 10 ms
  - Voltage/current sampling
  - Fault detection
  - Protection logic

Task: Power_Control_Slow    Priority: 3    Cycle: 100 ms
  - PUE calculation
  - Load balancing
  - Energy accumulation

Task: Power_Communication   Priority: 5    Cycle: 500 ms
  - Modbus polling (meters, UPS)
  - OPC UA server update
  - Alarm processing
```
