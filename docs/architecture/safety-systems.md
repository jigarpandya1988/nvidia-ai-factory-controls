# IPC-04: Safety Systems

## Overview

IPC-04 is the safety-rated controller responsible for all life-safety and equipment-protection functions. It operates independently of the other IPCs and maintains safe-state capability even if all other systems fail. Designed to SIL 2 (IEC 61508) for critical functions.

## Hardware Platform

- **Controller**: Beckhoff CX5240 + EL6900 TwinSAFE Logic
- **Safety I/O**: Beckhoff EL1904 (safe DI), EL2904 (safe DO)
- **OS**: Debian Linux with PREEMPT_RT kernel
- **Runtime**: CODESYS V3.5 SP20 + CODESYS Safety (SIL 2)
- **Redundancy**: Dual-channel inputs, monitored outputs

## Safety Functions

### 1. Emergency Power Off (EPO)
- **SIL Level**: SIL 2
- **Response Time**: < 100 ms from activation to de-energization
- **Triggers**: Manual pushbutton, automatic (fire, seismic, catastrophic leak)
- **Scope**: Zone-based EPO (per row, per room, facility-wide)
- **Reset**: Manual reset only, requires physical key + authorization

### 2. Fire Detection & Suppression
- **Detection**: VESDA (Very Early Smoke Detection Apparatus) + spot detectors
- **Suppression**: Clean agent (Novec 1230 or FM-200) for IT spaces
- **Pre-action**: Sprinkler for non-IT areas
- **Sequence**: Detect → Alarm → Countdown (30s) → Discharge
- **Abort**: Manual abort button during countdown

### 3. Liquid Leak Detection
- **Sensors**: Sensing cable under all raised floor / pipe runs
- **Zones**: Per-rack, per-row, per-CDU
- **Response**: 
  - Minor leak: Alarm + isolate affected zone
  - Major leak: EPO affected zone + isolate + drain

### 4. Gas Detection
- **Refrigerant**: R-134a / R-410A leak detection (if chiller present)
- **Oxygen depletion**: In enclosed spaces with clean agent suppression
- **Hydrogen**: Battery room monitoring (if lead-acid UPS)
- **Response**: Ventilation activation, area evacuation alarm

### 5. Seismic Protection
- **Sensors**: Triaxial accelerometers
- **Threshold**: 0.1g warning, 0.3g shutdown
- **Response**: Controlled shutdown of cooling pumps, isolation valves close
- **Purpose**: Prevent pipe rupture and flooding during seismic event

### 6. Access Control Integration
- **Zones**: Restricted areas (electrical rooms, battery rooms)
- **Interlock**: Certain maintenance operations require access confirmation
- **Logging**: All access events logged with timestamp and badge ID

## Safety Logic Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IPC-04 Safety Controller                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           CODESYS Safety Runtime (SIL 2)              │   │
│  │                                                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │   │
│  │  │  EPO    │  │  Fire   │  │  Leak   │  │ Seismic│ │   │
│  │  │ Logic   │  │ Logic   │  │ Logic   │  │ Logic  │ │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └───┬────┘ │   │
│  │       │            │            │            │       │   │
│  │  ┌────┴────────────┴────────────┴────────────┴────┐  │   │
│  │  │         SAFE STATE MANAGER                      │  │   │
│  │  │                                                 │  │   │
│  │  │  Determines safe state for each zone:           │  │   │
│  │  │  • Power: De-energize (EPO relay)              │  │   │
│  │  │  • Cooling: Pumps off, valves closed           │  │   │
│  │  │  • Ventilation: Dampers closed (fire)          │  │   │
│  │  │  • Access: Doors unlocked (evacuation)         │  │   │
│  │  └────────────────────┬────────────────────────────┘  │   │
│  │                       │                               │   │
│  └───────────────────────┼───────────────────────────────┘   │
│                          │                                    │
│  ┌───────────────────────┼───────────────────────────────┐   │
│  │     Standard Runtime (non-safety)                      │   │
│  │                       │                                │   │
│  │  • Alarm management & logging                         │   │
│  │  • OPC UA server (status to other IPCs)               │   │
│  │  • HMI interface                                      │   │
│  │  • Event historian                                    │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## I/O List

### Safe Digital Inputs (Category 3 / SIL 2)
| Signal | Count | Wiring | Description |
|--------|-------|--------|-------------|
| EPO Pushbutton | 8 | Dual-channel NC | Emergency stops |
| Fire Detector (VESDA) | 12 | Dual-channel | Smoke detection |
| Spot Smoke Detector | 24 | Conventional loop | Area detection |
| Leak Sensor Zone | 32 | Resistive cable | Liquid detection |
| Gas Detector | 8 | 4-20mA + relay | Refrigerant/O2 |
| Seismic Sensor | 4 | Dual-channel | Accelerometer |
| Door Contact (safety) | 16 | Dual-channel NC | Restricted areas |
| Suppression Discharged | 4 | Pressure switch | Agent released |
| Manual Abort Button | 4 | NC contact | Suppression abort |

### Safe Digital Outputs (Monitored, SIL 2)
| Signal | Count | Description |
|--------|-------|-------------|
| EPO Contactor (zone) | 8 | Power disconnect |
| Suppression Release | 4 | Agent discharge valve |
| Damper Close | 8 | Fire dampers |
| Isolation Valve | 16 | Coolant isolation |
| Evacuation Alarm | 4 | Audible/visual |
| Door Unlock (evac) | 16 | Mag-lock release |
| Pump Trip | 8 | Cooling pump safety stop |
| Ventilation Start | 4 | Gas purge fans |

### Standard I/O (Non-Safety, Monitoring Only)
| Signal | Count | Type | Description |
|--------|-------|------|-------------|
| Zone Temperature | 24 | AI (PT100) | Fire risk areas |
| Humidity | 12 | AI (4-20mA) | Condensation risk |
| Water Level | 8 | AI (4-20mA) | Sump/drain monitoring |
| Status Indicators | 32 | DO | Panel lights |

## Safety Response Matrix

| Event | Zone Scope | Power | Cooling | HVAC | Access | Notification |
|-------|-----------|-------|---------|------|--------|-------------|
| EPO (manual) | Affected zone | OFF | OFF | OFF | UNLOCK | Critical alarm |
| Fire (VESDA alert) | Room | ON | ON | CLOSE dampers | UNLOCK | High alarm |
| Fire (confirmed) | Room | OFF (30s delay) | OFF | CLOSE | UNLOCK | Critical + FD |
| Leak (minor) | Rack row | ON | ISOLATE zone | ON | Normal | High alarm |
| Leak (major) | Room | OFF | OFF + DRAIN | ON | UNLOCK | Critical alarm |
| Seismic (>0.3g) | Facility | ON (UPS) | OFF pumps | OFF | UNLOCK | Critical alarm |
| Gas (high) | Room | ON | ON | PURGE | RESTRICT | High alarm |
| O2 depletion | Room | ON | ON | PURGE | RESTRICT | Critical alarm |

## Hardwired Safety Connections

Critical safety signals are hardwired in addition to digital communication:

```
IPC-04 Safe DO ──── [EPO Relay] ──── IPC-01 (Power trip)
IPC-04 Safe DO ──── [Pump Trip] ──── IPC-02 (Cooling stop)
IPC-04 Safe DO ──── [Damper Close] ── HVAC system

These hardwired connections ensure safety even if:
  • Network communication fails
  • Any IPC crashes or reboots
  • Software has bugs
```

## Compliance & Standards

| Standard | Scope | Requirement |
|----------|-------|-------------|
| IEC 61508 | Functional safety | SIL 2 for EPO, fire, leak |
| IEC 62061 | Machine safety | Safety function design |
| NFPA 70 | Electrical code | EPO requirements |
| NFPA 75 | IT equipment protection | Fire suppression |
| NFPA 76 | Telecom facilities | Fire protection |
| EN 378 | Refrigeration safety | Gas detection |
| IEC 62443 | Cybersecurity | Safety system isolation |

## Testing & Maintenance

### Periodic Testing Schedule
| Test | Frequency | Method |
|------|-----------|--------|
| EPO functional test | Monthly | Simulated activation (test mode) |
| Fire detection test | Quarterly | Smoke generator |
| Leak detection test | Quarterly | Controlled water application |
| Suppression inspection | Semi-annual | Visual + weight check |
| Full system test | Annual | Complete scenario simulation |
| SIL verification | 5 years | Full proof test per IEC 61508 |

### Diagnostic Coverage
- Input monitoring: Cross-channel comparison, wire-break detection
- Output monitoring: Read-back verification, pulse testing
- Logic: Watchdog timer, program flow monitoring
- Communication: Heartbeat between safety and standard runtime

## Task Configuration

```
Task: Safety_Fast          Priority: 0    Cycle: 2 ms
  - EPO logic execution
  - Input cross-checking
  - Output monitoring
  - Watchdog service

Task: Safety_Normal        Priority: 2    Cycle: 20 ms
  - Fire sequence logic
  - Leak response logic
  - Seismic evaluation
  - Gas detection logic

Task: Safety_Diagnostic    Priority: 5    Cycle: 1000 ms
  - Sensor validation
  - Self-test execution
  - Event logging
  - OPC UA status publish
```
