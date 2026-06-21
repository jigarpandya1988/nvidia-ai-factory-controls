# 3D Visualization — AI Factory Cooling System

## Quick Start

```bash
# 1. Generate simulation data (if not already done)
cd nvidia-ai-factory-controls
python simulation/closed_loop.py --output visualization/simulation_output.json

# 2. Serve the visualization (any HTTP server works)
cd visualization
python -m http.server 8080

# 3. Open in browser
# http://localhost:8080
```

## What You'll See

- 3D view of GPU racks with color-coded temperature (green→red)
- CDU unit with spinning pump rotor (speed = pump speed)
- Rotating valve indicator (angle = valve position)
- Real-time metrics panel (GPU temp, supply/return, flow, PUE)
- Controller output panel (pump %, valve %, PID terms)
- Status indicators (pump, sensors, safety, leak)
- Timeline with playback controls (play, pause, 1x/5x speed, seek)

## Data Flow

```
closed_loop.py → simulation_output.json → index.html (Three.js)
```

The visualization replays the simulation data at 10 FPS (adjustable speed).
For real-time, connect to NATS via WebSocket instead of file playback.
