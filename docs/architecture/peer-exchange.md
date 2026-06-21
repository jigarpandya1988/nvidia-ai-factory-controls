# Inter-IPC Peer-to-Peer Data Exchange

## Overview

All 4 IPCs communicate directly with each other in a **full mesh** topology for real-time coordination. This bypasses the edge gateway (which runs at 100ms) and provides deterministic sub-10ms data exchange.

## Topology

```
         ┌─────────────────────────────────────────┐
         │           CONTROL NETWORK (VLAN 100)     │
         │                                         │
         │   IPC-01 ◄═══════════════════► IPC-02   │
         │   (Power)    UDP + OPC UA      (Cooling) │
         │     ▲ ╲                         ╱ ▲     │
         │     │   ╲                     ╱   │     │
         │     │     ╲                 ╱     │     │
         │     │       ╲             ╱       │     │
         │     │         ╲         ╱         │     │
         │     ▼           ╲     ╱           ▼     │
         │   IPC-03 ◄═══════╳═══════► IPC-04       │
         │   (Environ)      Full       (Safety)     │
         │                  Mesh                    │
         └─────────────────────────────────────────┘
```

## Dual Transport (Redundancy)

| Transport | Latency | Use Case | Fail Mode |
|-----------|---------|----------|-----------|
| **UDP Multicast** | < 1ms | Safety permit, emergency stop | Fall back to OPC UA |
| **OPC UA Direct** | 5-10ms | Operational data, setpoints | Fall back to UDP |
| **Hardwired** | < 1ms | EPO relay (IPC-04 → power contactors) | Always works (electrical) |

If UDP fails → OPC UA still works (higher latency but functional).
If OPC UA fails → UDP still works.
If BOTH fail → hardwired safety signals are the last defense.

## Data Exchanged (ST_PeerData — 128 bytes)

```
┌────────────────────────────────────────────────────────┐
│ HEADER:     Sequence | Timestamp | Source IPC | State  │
├────────────────────────────────────────────────────────┤
│ SAFETY:     Permit | EStop | PowerShed | MaxCool       │  ← Read first!
├────────────────────────────────────────────────────────┤
│ VALUES:     PrimaryValue[1..4] (IPC-specific)          │
├────────────────────────────────────────────────────────┤
│ STATUS:     Healthy | HasAlarm | AtCapacity | Count    │
├────────────────────────────────────────────────────────┤
│ HEARTBEAT:  ScanCounter                                │
└────────────────────────────────────────────────────────┘
```

## Safety Principle: Pessimistic Evaluation

```
IF peer_alive AND peer.SafetyPermit = TRUE  → PERMIT
IF peer_alive AND peer.SafetyPermit = FALSE → NO PERMIT
IF peer_dead (timeout)                      → NO PERMIT (assume worst)
```

**Dead peer = revoked permit.** This is the fail-safe principle.

## Timing Budget

| Event | Max Latency | How |
|-------|-------------|-----|
| Safety permit change | < 10ms | UDP multicast + 2 scan cycles |
| Emergency stop propagation | < 10ms | UDP + hardwired (parallel) |
| Power shed request | < 50ms | OPC UA subscription |
| GPU thermal alert | < 100ms | OPC UA via edge gateway |

## Coordination Use Cases

### 1. Cooling Requests Power Shed
```
IPC-02 detects: GPU temp rising, CDUs at capacity, cannot cool more.
IPC-02 sets: stMyData.bRequestPowerShed := TRUE
IPC-01 reads: stPeer_Cooling.bRequestPowerShed = TRUE
IPC-01 action: Begin graceful workload reduction (via compute orchestrator)
```

### 2. Safety Revokes Permit
```
IPC-04 detects: Major leak in cooling zone
IPC-04 sets: stMyData.bSafetyPermit := FALSE
ALL IPCs read: stPeer_Safety.bSafetyPermit = FALSE
ALL IPCs action: Enter safe-state / emergency stop
```

### 3. Power Requests Maximum Cooling
```
IPC-01 detects: Grid instability, preparing for possible outage
IPC-01 sets: stMyData.bRequestMaxCool := TRUE  
IPC-02 reads: stPeer_Power.bRequestMaxCool = TRUE
IPC-02 action: Switch all CDUs to MAX_COOL mode (pre-cool before potential outage)
```

## Sequence Gap Detection

Each peer increments a sequence counter every cycle. Receivers track:
- Expected = last_received + 1
- If received > expected → gap detected → count missed packets
- Sustained gaps (> 10%) → alarm: network congestion or IPC overloaded
