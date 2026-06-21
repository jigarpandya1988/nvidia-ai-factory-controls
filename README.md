# NVIDIA AI Factory Controls

## Industrial Control System for AI Data Center Infrastructure

A comprehensive **CODESYS-based distributed control system** for managing NVIDIA AI Factory data centers — covering power distribution, liquid cooling, environmental monitoring, safety systems, and cloud connectivity.

Built on **multiple Linux IPCs** running CODESYS runtime with **OPC UA** for tag exposure, **NATS** for message brokering (peer-to-peer + cloud), and **AWS CDK** for cloud infrastructure.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          AWS CLOUD                                          │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ IoT Core   │  │ Timestream  │  │  S3 Archive  │  │ CloudWatch       │ │
│  │ (MQTT)     │  │ (hot/warm)  │  │  (cold/Parquet)│  │ (alarms/metrics)│ │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  └───────┬──────────┘ │
│        └─────────────────┴────────────────┴──────────────────┘            │
│                                    ▲                                       │
│                                    │ NATS Leaf Node (TLS)                  │
├────────────────────────────────────┼───────────────────────────────────────┤
│                          EDGE GATEWAY (Docker)                             │
│                                    │                                       │
│  ┌─────────────────────────────────┴───────────────────────────────────┐  │
│  │                     NATS Server + JetStream                          │  │
│  │         (single broker, all IPCs connect, store-and-forward)         │  │
│  └────┬──────────┬───────────┬──────────┬────────────────────────────┘  │
│       │          │           │          │                                 │
│  ┌────┴────┐┌────┴────┐┌────┴────┐┌────┴────┐  ┌────────────────────┐  │
│  │Bridge-01││Bridge-02││Bridge-03││Bridge-04│  │  AWS Forwarder    │  │
│  │OPC UA↔  ││OPC UA↔  ││OPC UA↔  ││OPC UA↔  │  │  NATS→IoT Core   │  │
│  │NATS     ││NATS     ││NATS     ││NATS     │  │  NATS→Timestream  │  │
│  └────┬────┘└────┬────┘└────┬────┘└────┬────┘  └────────────────────┘  │
│       │          │           │          │                                 │
├───────┼──────────┼───────────┼──────────┼─────────────────────────────────┤
│       │    CONTROL NETWORK (VLAN 100)   │                                 │
│       │          │           │          │                                 │
│  ┌────┴────┐┌────┴────┐┌────┴────┐┌────┴────┐                           │
│  │ IPC-01  ││ IPC-02  ││ IPC-03  ││ IPC-04  │                           │
│  │ Power   ││ Cooling ││ Environ ││ Safety  │                           │
│  │ CODESYS ││ CODESYS ││ CODESYS ││ CODESYS │                           │
│  │ OPC UA  ││ OPC UA  ││ OPC UA  ││ OPC UA  │                           │
│  └─────────┘└─────────┘└─────────┘└─────────┘                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| PLC Runtime | CODESYS V3.5 SP20+ on Linux | Open, multi-vendor IPC support |
| Inter-IPC Protocol | OPC UA (built into CODESYS) | Standard, encrypted, typed |
| Message Broker | NATS + JetStream | <1ms latency, built-in persistence, peer-to-peer |
| Cloud | AWS (IoT Core, Timestream, S3) | Pay-per-message, serverless, cost-optimized |
| IaC | AWS CDK (TypeScript) | Type-safe, testable, real programming language |
| Peer-to-Peer | NATS subjects via bridge | ~3ms IPC-to-IPC, no custom protocols |
| Safety Standard | IEC 61508 SIL 2 | Dual-channel inputs, fail-safe, fault latching |
| Code Structure | CODESYS libraries (6) | Reusable, versioned, scalable across sites |

---

## Project Structure

```
nvidia-ai-factory-controls/
├── libraries/                              ← Reusable CODESYS libraries
│   ├── AIFactory_Common/                   ← Base classes, PID, sensors, alarms
│   ├── AIFactory_Communication/            ← Data engine, publishers, subscribers
│   ├── AIFactory_Cooling/                  ← CDU, chiller, cooling tower
│   ├── AIFactory_Power/                    ← Power distribution, PUE, UPS
│   ├── AIFactory_Environment/              ← Zone monitoring, dew point
│   ├── AIFactory_Safety/                   ← EPO, fire, leak (SIL 2)
│   └── DEPENDENCY_GRAPH.md
│
├── projects/                               ← Per-IPC deployment projects
│   ├── IPC-01_Power/                       ← Imports: Common + Comm + Power
│   ├── IPC-02_Cooling/                     ← Imports: Common + Comm + Cooling
│   ├── IPC-03_Environment/                 ← Imports: Common + Comm + Environment
│   └── IPC-04_Safety/                      ← Imports: Common + Comm + Safety
│
├── src/edge-gateway/                       ← Edge services (Docker)
│   ├── nats-broker/                        ← NATS server config + JetStream streams
│   └── nats-bridge/                        ← OPC UA ↔ NATS bridges + AWS forwarder
│
├── deploy/
│   ├── aws-cdk/                            ← Cloud infrastructure (TypeScript CDK)
│   ├── docker/                             ← Docker Compose (edge + IPC agent)
│   └── ansible/                            ← IPC provisioning playbooks
│
├── tests/
│   ├── codesys/                            ← PLC unit tests (FB_TestSuite framework)
│   ├── python/                             ← Edge service tests (pytest)
│   └── typescript/                         ← CDK stack tests (Jest)
│
├── docs/                                   ← Architecture & design documentation
│   ├── architecture/                       ← System design, per-subsystem docs
│   ├── research/                           ← NVIDIA reference material
│   └── standards/                          ← IEC 61131-3, OPC UA, safety standards
│
├── config/                                 ← Alarm definitions, network topology
└── .github/workflows/ci.yml               ← CI/CD pipeline
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| PLC Runtime | CODESYS V3.5 SP20+ on Linux (ARM64 / x86_64) |
| IPC Hardware | Beckhoff CX series / WAGO PFC200 |
| Field Bus | EtherCAT (real-time I/O) |
| IPC Communication | OPC UA (IEC 62541) |
| Message Broker | NATS + JetStream |
| Edge Platform | Docker on Ubuntu 22.04 LTS |
| Cloud | AWS (IoT Core, Timestream, S3, Lambda, CloudWatch) |
| IaC | AWS CDK (TypeScript) |
| Visualization | Grafana + CODESYS WebVisu |
| CI/CD | GitHub Actions → CodePipeline → IoT Jobs (fleet deploy) |
| Unit Testing | CODESYS CUnit + pytest + Jest |

---

## Communication Architecture

### IPC-to-IPC (Peer-to-Peer via NATS, ~3ms)
```
IPC-04 CODESYS → OPC UA → Bridge-04 → NATS → Bridge-02 → OPC UA → IPC-02 CODESYS
```

### IPC-to-Cloud (Telemetry via NATS + AWS, 100ms-5s)
```
IPC-02 CODESYS → OPC UA → Bridge-02 → NATS → AWS Forwarder → IoT Core → Timestream
```

### Cloud-to-IPC (Commands via NATS, ~100ms)
```
Cloud SCADA → IoT Core → NATS Leaf → Bridge-02 → OPC UA write → IPC-02 CODESYS
```

---

## Getting Started

### Prerequisites
- CODESYS Development System V3.5 SP20+
- Docker & Docker Compose
- Node.js 20+ (for CDK)
- Python 3.12+ (for edge services)
- AWS CLI configured

### Quick Start
```bash
# 1. Install edge services
cd src/edge-gateway/nats-bridge
docker compose up -d

# 2. Deploy cloud infrastructure
cd deploy/aws-cdk
npm install
npx cdk deploy --all --context siteId=us-west-01

# 3. Run tests
python -m pytest tests/python/ -v          # Python: 18 tests
cd deploy/aws-cdk && npm test              # TypeScript: 19 tests
# CODESYS tests: run PRG_TestRunner in simulation mode
```

---

## Testing

| Suite | Command | Tests |
|-------|---------|-------|
| Python (edge) | `pytest tests/python/ -v` | 18 (NATS bridge, AWS forwarder) |
| TypeScript (CDK) | `cd deploy/aws-cdk && npm test` | 19 (all 4 cloud stacks) |
| CODESYS (PLC) | CODESYS Test Manager | 35 (PID, sensors, CDU, EPO, data) |
| **Total** | | **72 tests** |

---

## References

- [NVIDIA AI Factory White Paper](https://docs.nvidia.com/ai-enterprise/planning-resource/ai-factory-white-paper/latest/ai-factory-overview.html)
- [CODESYS Documentation](https://help.codesys.com/)
- [NATS Documentation](https://docs.nats.io/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [OPC UA Specification](https://opcfoundation.org/)
