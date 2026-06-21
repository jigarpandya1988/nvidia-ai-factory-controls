# NVIDIA AI Factory Controls — Project Context

## Overview
Distributed industrial control system for NVIDIA AI Factory data centers using CODESYS V3.5 on Linux IPCs. Manages power distribution, liquid cooling, environmental monitoring, and safety systems with cloud connectivity via NATS + AWS.

## Architecture
- **4 IPCs** (Power, Cooling, Environment, Safety) each running CODESYS
- **NATS broker** on edge server — all IPCs connect via OPC UA bridges
- **AWS cloud** (IoT Core, Timestream, S3) via NATS leaf node
- **Peer-to-peer** between IPCs via NATS subjects (~3ms latency)

## Key Technical Decisions
- **PLC Runtime**: CODESYS V3.5 SP20+ on Linux (PREEMPT_RT kernel)
- **Programming Language**: IEC 61131-3 Structured Text (primary)
- **IPC Communication**: OPC UA (built-in CODESYS server)
- **Message Broker**: NATS + JetStream (replaces MQTT/EMQX)
- **Cloud**: AWS (IoT Core, Timestream, S3, Lambda, CloudWatch)
- **IaC**: AWS CDK (TypeScript)
- **Edge Platform**: Docker on Ubuntu 22.04 LTS
- **Visualization**: Grafana + CODESYS WebVisu
- **Safety**: SIL 2 per IEC 61508 for critical functions
- **Unit Testing**: CODESYS CUnit + pytest + Jest

## Project Layout
```
libraries/          ← 6 reusable CODESYS libraries
projects/           ← 4 per-IPC deployment projects
src/edge-gateway/   ← NATS broker + OPC UA bridges (Python/Docker)
deploy/aws-cdk/     ← Cloud infrastructure (TypeScript)
deploy/docker/      ← Docker Compose files
deploy/ansible/     ← IPC provisioning
tests/              ← codesys/ + python/ + typescript/
docs/               ← Architecture documentation
```

## File Extensions (CODESYS object types)
- `.fb` — Function Block
- `.method` — Method (ClassName.MethodName.method)
- `.prop` — Property
- `.interface` — Interface
- `.struct` — Structure (DUT)
- `.enum` — Enumeration (DUT)
- `.gvl` — Global Variable List
- `.pou` — Program

## File Structure (mirrors CODESYS IDE)
Every file uses Declaration/Implementation sections:
```
(* HEADER *)

(* ═══ DECLARATION ═══ *)
FUNCTION_BLOCK / METHOD / PROPERTY ...
VAR ... END_VAR

(* ═══ IMPLEMENTATION ═══ *)
// logic
```

## Naming Conventions
- Function blocks: `FB_` prefix
- Enumerations: `E_` prefix
- Structures: `ST_` prefix
- Interfaces: `I_` prefix
- Global Variable Lists: `GVL_` prefix
- Private/internal vars: `_` prefix
- Constants: `C_` prefix
- Edge triggers: `_rtrig` (rising), `_ftrig` (falling)

## OOP Architecture
- All FBs EXTEND `FB_Base` (lifecycle, watchdog, fault latching)
- Override virtual methods: `M_Initialize`, `M_Execute`, `M_SafeState`, `M_Diagnose`
- Use `I_Controllable` for polymorphic subsystem management
- Use `I_SafetyMonitored` for safety chain participation
- Composition over inheritance for complex FBs

## Safety Principles
- Safety checks run BEFORE base class lifecycle (unconditional)
- Fail-safe = de-energized (loss of signal = safe state)
- Fault latching: requires explicit operator reset (no auto-recovery)
- Dual-channel inputs with discrepancy monitoring
- Pessimistic logic: any doubt → trip

## Edge Triggers (R_TRIG / F_TRIG)
- Use `R_TRIG` for: reset inputs, pump start counting, alarm raised events
- Use `F_TRIG` for: enable removal detection, pump stop events
- Use `FB_EdgeDetector` when you need both rising and falling
- NEVER use manual `IF x AND NOT x_prev` — always use standard FBs

## Data Flow
- CODESYS → OPC UA server (built-in) → OPC UA bridge (Python) → NATS → AWS
- Peer-to-peer: NATS subjects route between IPC bridges (no custom UDP)
- Commands: AWS IoT Core → NATS leaf → bridge → OPC UA write → CODESYS

## Race Condition Prevention
- One FB instance per task — NEVER share across tasks
- Cross-task data: atomic struct copy via `GVL_CrossTask`
- OPC UA bridges handle all cross-IPC communication externally
- NATS handles message ordering and delivery guarantees (JetStream)

## Build & Deploy
- **Library-based architecture**: 6 independent CODESYS libraries
- **CI/CD**: GitHub Actions → CodePipeline → IoT Jobs (fleet deploy)
- **Testing**: pytest (18) + Jest (19) + CODESYS CUnit (35) = 72 tests
- **IPC provisioning**: Ansible playbooks
- **Cloud infra**: `npx cdk deploy --all --context siteId=us-west-01`
