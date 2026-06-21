# SCADA Application — AI Factory Control & Monitoring

## Architecture

```
Browser (React) ←─ WebSocket ─→ Backend (Fastify) ←─ NATS / Simulation
    :3001                          :4000
```

## Quick Start

```bash
# Terminal 1: Start backend
cd scada/backend
npm install
npm run dev

# Terminal 2: Start frontend
cd scada/frontend
npm install
npm run dev

# Open: http://localhost:3001
```

## Pages

| Page | Description |
|------|-------------|
| Overview | Facility KPIs, P&ID diagram, system status |
| Cooling | Detailed CDU control, PID tuning, GPU temps |
| Power | Single-line diagram, PUE, UPS, ATS status |
| Safety | EPO zone map, fire detection, leak locations |
| Environment | Temperature/humidity heatmap per zone |
| Alarms | Active/history, acknowledge, severity filter |
| Trends | Real-time time-series charts (Recharts) |

## Tech Stack

- **Frontend**: React 18, TypeScript, TailwindCSS, Recharts, Zustand, Vite
- **Backend**: Fastify, TypeScript, WebSocket, NATS client
- **Real-time**: WebSocket push (10 Hz process data updates)
- **State**: Zustand store with 30-second rolling history
