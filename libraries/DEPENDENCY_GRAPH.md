# Library Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PROJECTS (per-IPC)                           │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ IPC-01      │ │ IPC-02      │ │ IPC-03      │ │ IPC-04      │ │
│  │ Power       │ │ Cooling     │ │ Environment │ │ Safety      │ │
│  │             │ │             │ │             │ │             │ │
│  │ PRG_Power   │ │ PRG_Cooling │ │ PRG_Enviro  │ │ PRG_Safety  │ │
│  │ PRG_Comm    │ │ PRG_Comm    │ │ PRG_Comm    │ │ PRG_Comm    │ │
│  │ GVLs        │ │ GVLs        │ │ GVLs        │ │             │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         │               │               │               │         │
└─────────┼───────────────┼───────────────┼───────────────┼─────────┘
          │               │               │               │
          ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DOMAIN LIBRARIES                              │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ AIFactory│  │ AIFactory│  │  AIFactory   │  │  AIFactory   │  │
│  │ _Power   │  │ _Cooling │  │ _Environment │  │  _Safety     │  │
│  │          │  │          │  │              │  │  (SIL 2)     │  │
│  │ FB_Power │  │ FB_CDU   │  │ FB_Environ   │  │ FB_EPO       │  │
│  │ Distrib. │  │ FB_Chill │  │ Zone         │  │ FB_Fire      │  │
│  │          │  │ FB_Tower │  │              │  │ FB_Leak      │  │
│  │          │  │ FB_Super │  │              │  │              │  │
│  └─────┬────┘  └────┬─────┘  └──────┬───────┘  └──────┬───────┘  │
│        │            │               │               │             │
└────────┼────────────┼───────────────┼───────────────┼─────────────┘
         │            │               │               │
         └────────────┼───────────────┼───────────────┘
                      │               │
                      ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE LIBRARIES                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AIFactory_Communication                          │   │
│  │                                                              │   │
│  │  FB_DataCollector | FB_Publisher_* | FB_Subscriber_*         │   │
│  │  FB_PeerExchange_OPCUA | FB_PeerExchange_UDP                │   │
│  │  I_DataPublisher | I_DataSubscriber | I_PeerExchange         │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       BASE LIBRARY (no dependencies)                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AIFactory_Common                                 │   │
│  │                                                              │   │
│  │  FB_Base | FB_PID | FB_SensorValidator | FB_AlarmManager    │   │
│  │  FB_RampGenerator | FB_Watchdog | FB_EdgeDetector           │   │
│  │  I_Controllable | I_SafetyMonitored                         │   │
│  │  E_Lifecycle | E_AlarmSeverity | E_CommStatus | E_SafetyState│   │
│  │  ST_SensorInput | ST_AlarmRecord                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Dependency Rules

1. **Common** depends on nothing (pure base layer)
2. **Communication** depends on Common only
3. **Domain libraries** (Cooling, Power, Environment, Safety) depend on Common only
4. **Projects** can reference any combination of libraries
5. No circular dependencies allowed
6. Domain libraries do NOT depend on each other (decoupled)

## Scalability

Adding a new AI Factory site:
1. Create new `projects/Site-02_IPC-XX/` folder
2. Reference the same libraries
3. Customize GVLs (IP addresses, I/O mapping, setpoints)
4. Deploy — all library FBs are shared/reused

Adding a new subsystem (e.g., battery storage):
1. Create `libraries/AIFactory_Battery/`
2. Add FBs, DUTs following same patterns
3. Depends on: AIFactory_Common
4. Any project that needs it: add library reference
