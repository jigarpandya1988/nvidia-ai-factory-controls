# IPC-02: Liquid Cooling Control

## Overview

IPC-02 manages the direct liquid cooling (DLC) system — the most critical subsystem in an NVIDIA AI Factory. At 120–140 kW per rack, air cooling is physically impossible; liquid cooling is mandatory. This IPC controls CDU (Coolant Distribution Unit) loops, pump speeds, valve positions, and temperature setpoints to maintain GPU junction temperatures within safe operating limits.

## Hardware Platform

- **Controller**: Beckhoff CX5240 (Intel Core i3, dual-core, 8GB RAM)
- **OS**: Debian Linux with PREEMPT_RT kernel
- **Runtime**: CODESYS V3.5 SP20
- **I/O**: EtherCAT terminals (Beckhoff EL series)
- **Special**: Redundant controller option for N+1 availability

## Functional Scope

### 1. CDU (Coolant Distribution Unit) Control
- Primary/secondary loop temperature control
- Pump speed modulation (VFD control)
- 3-way mixing valve control
- Heat exchanger effectiveness monitoring
- CDU redundancy management (N+1 switchover)

### 2. Rack-Level Cooling
- Per-rack coolant flow regulation
- Supply/return temperature monitoring
- Differential pressure control
- Quick-disconnect leak monitoring
- Rear-door heat exchanger control (hybrid systems)

### 3. Facility Water Loop
- Cooling tower/dry cooler fan control
- Free cooling optimization (economizer mode)
- Water treatment system monitoring
- Make-up water control
- Glycol concentration monitoring

### 4. Thermal Management Intelligence
- GPU power-based feedforward control
- Predictive setpoint adjustment
- Thermal inertia compensation
- Seasonal optimization
- Waste heat recovery coordination

## Control Loop Design

### Primary CDU Loop (PID + Feedforward)

```
                    ┌─────────────────────────────────────┐
                    │         CDU Control Loop             │
                    │                                     │
  GPU Power ──────►│ Feedforward ──┐                     │
  (from DCGM)      │               ▼                     │
                    │         ┌──────────┐                │
  T_supply_SP ────►│ SP ────►│   PID    │───► Pump VFD   │
                    │         │Controller│     Speed (Hz)  │
  T_supply_PV ────►│ PV ────►│          │                │
  (PT1000)         │         └──────────┘                │
                    │                                     │
                    │         ┌──────────┐                │
  T_return_SP ────►│ SP ────►│   PID    │───► 3-Way Valve│
                    │         │Controller│     Position(%) │
  T_return_PV ────►│ PV ────►│          │                │
  (PT1000)         │         └──────────┘                │
                    └─────────────────────────────────────┘
```

### PID Parameters (Typical CDU Loop)

| Parameter | Pump Speed | Valve Position |
|-----------|-----------|----------------|
| Kp | 2.5 | 1.8 |
| Ti | 30 s | 45 s |
| Td | 0 s | 5 s |
| Output Min | 20% (min flow) | 0% (full bypass) |
| Output Max | 100% | 100% (full process) |
| Deadband | ±0.5°C | ±1.0°C |
| Setpoint | 35°C supply | 45°C return |

### Feedforward Compensation

```structured-text
// When GPU power increases, proactively increase cooling
// before temperature actually rises (anticipatory control)

FF_Gain := 0.015;  // %pump per kW GPU power
FF_Output := (GPU_Total_Power_kW - GPU_Baseline_kW) * FF_Gain;

Pump_Speed_Command := PID_Output + FF_Output;
Pump_Speed_Command := LIMIT(20.0, Pump_Speed_Command, 100.0);
```

## I/O List (Per CDU Pair — typically 4 CDU pairs per 10 MW block)

### Analog Inputs (AI)
| Signal | Count | Sensor | Description |
|--------|-------|--------|-------------|
| Supply Temperature | 2 | PT1000 | CDU outlet to racks |
| Return Temperature | 2 | PT1000 | Rack return to CDU |
| Facility Water Supply | 2 | PT1000 | Building loop supply |
| Facility Water Return | 2 | PT1000 | Building loop return |
| Coolant Flow Rate | 2 | Electromagnetic | LPM measurement |
| Differential Pressure | 4 | 4-20mA | Across CDU, across rack row |
| Pump Motor Current | 2 | CT | Pump health monitoring |
| Glycol Concentration | 1 | Refractometer | Coolant quality |

### Digital Inputs (DI)
| Signal | Count | Description |
|--------|-------|-------------|
| Pump Running Feedback | 4 | Motor contactor aux |
| VFD Fault | 4 | Drive alarm |
| VFD Ready | 4 | Drive ready status |
| High Pressure Switch | 4 | Mechanical safety |
| Low Pressure Switch | 4 | Loss of flow |
| Leak Detection Zone | 16 | Sensing cable zones |
| Valve End Position | 8 | Open/Closed limit |
| CDU Local/Remote | 2 | Mode selector |

### Analog Outputs (AO)
| Signal | Count | Range | Description |
|--------|-------|-------|-------------|
| Pump VFD Speed Ref | 4 | 4-20mA | 0-100% speed |
| 3-Way Valve Position | 4 | 4-20mA | 0-100% position |
| Cooling Tower Fan | 2 | 4-20mA | Fan speed control |

### Digital Outputs (DO)
| Signal | Count | Description |
|--------|-------|-------------|
| Pump Start/Stop | 4 | Motor contactor |
| Isolation Valve | 8 | Row isolation |
| CDU Enable | 2 | System enable |
| Alarm Horn | 1 | Local audible alarm |

## Operating Modes

### 1. Normal Operation
- PID control active on all loops
- Feedforward from GPU telemetry
- Free cooling when ambient permits (T_ambient < 15°C)
- Automatic CDU switchover on fault

### 2. Economizer Mode (Free Cooling)
- Bypass CDU heat exchangers
- Direct facility water to racks (when cold enough)
- Significant energy savings (30-50% pump energy reduction)
- Automatic transition based on wet-bulb temperature

### 3. Emergency Mode
- Maximum pump speed on all CDUs
- All valves to full cooling position
- Triggered by: high GPU temp, leak detection, or IPC-04 command
- Coordinates with IPC-01 for power shed if cooling insufficient

### 4. Maintenance Mode
- Single CDU operation (N+1 → N)
- Reduced capacity operation
- Manual valve override capability
- Drain/fill sequence automation

## Integration with GPU Telemetry

```
NVIDIA DCGM (Data Center GPU Manager)
  │
  ├── GPU Junction Temperature (per GPU)
  ├── GPU Power Draw (per GPU)  
  ├── GPU Throttle Status
  └── Memory Temperature
  │
  ▼
Edge Gateway (REST → OPC UA translation)
  │
  ▼
IPC-02 CODESYS (OPC UA client reads)
  │
  ├── Aggregate: Total GPU Power per Row
  ├── Max GPU Temp per Row
  └── Thermal Headroom Calculation
```

## Alarm Configuration

| Alarm | Threshold | Priority | Action |
|-------|-----------|----------|--------|
| GPU Temp High | > 80°C | Critical | Max cooling, notify |
| GPU Temp Warning | > 75°C | High | Increase setpoint |
| Supply Temp High | > 40°C | High | Check CDU, increase pump |
| Supply Temp Low | < 20°C | Medium | Risk of condensation |
| Flow Rate Low | < 50% design | Critical | Check pump, open valves |
| Leak Detected | Any zone | Critical | Isolate zone, EPO if severe |
| Pump Fault | VFD trip | High | Switch to standby pump |
| Pressure High | > 6 bar | Critical | Reduce pump, check valves |
| Delta-T High | > 20°C | High | Flow restriction detected |

## Task Configuration

```
Task: Cooling_Fast         Priority: 1    Cycle: 5 ms
  - PID loop execution
  - Feedforward calculation
  - Safety interlocks (high temp, high pressure)

Task: Cooling_Normal       Priority: 3    Cycle: 50 ms
  - Mode management
  - CDU switchover logic
  - Economizer transitions

Task: Cooling_Slow         Priority: 5    Cycle: 1000 ms
  - GPU telemetry processing
  - Energy optimization
  - Trend logging
  - OPC UA server update

Task: Cooling_Diagnostic   Priority: 8    Cycle: 5000 ms
  - Pump health monitoring (vibration, current)
  - Valve stroke testing
  - Sensor validation (range, rate-of-change)
  - Predictive maintenance calculations
```

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Temperature Stability | ±1°C of setpoint | 5-minute rolling average |
| Response Time (step) | < 30 seconds to 90% | Step response test |
| GPU Temp Overshoot | < 3°C above setpoint | During load transients |
| Pump Energy | < 2% of IT load | Continuous metering |
| Free Cooling Hours | > 4,000 hrs/year | Annual accumulation |
| Availability | 99.999% | Annual uptime |
