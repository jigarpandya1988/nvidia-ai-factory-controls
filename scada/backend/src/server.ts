/**
 * SCADA Backend Server
 * ====================
 * - WebSocket: real-time process data push to frontend
 * - REST API: alarms, configuration, historical queries
 * - Connects to NATS broker (or simulation adapter for demo)
 */

import Fastify from 'fastify';
import websocket from '@fastify/websocket';
import cors from '@fastify/cors';
import { SimulationAdapter } from './services/simulation-adapter';
import { AlarmRecord, SystemStatus, OverviewKPIs } from './types/plant';

const app = Fastify({ logger: true });
const sim = new SimulationAdapter();

// Active WebSocket clients
const wsClients = new Set<any>();

async function main() {
  await app.register(cors, { origin: true });
  await app.register(websocket);

  // ─── WebSocket: Real-time process data ──────────────────────────
  app.get('/ws', { websocket: true }, (socket, req) => {
    wsClients.add(socket);
    console.log(`[WS] Client connected (${wsClients.size} total)`);

    socket.on('message', (msg: Buffer) => {
      try {
        const cmd = JSON.parse(msg.toString());
        if (cmd.type === 'play') sim.setPlaying(true);
        if (cmd.type === 'pause') sim.setPlaying(false);
        if (cmd.type === 'speed') sim.setSpeed(cmd.value);
        if (cmd.type === 'seek') sim.seek(cmd.frame);
      } catch {}
    });

    socket.on('close', () => {
      wsClients.delete(socket);
      console.log(`[WS] Client disconnected (${wsClients.size} total)`);
    });
  });

  // ─── REST: System Status ────────────────────────────────────────
  app.get('/api/status', async () => {
    const status: SystemStatus = {
      ipc_power: 'online',
      ipc_cooling: 'online',
      ipc_environment: 'online',
      ipc_safety: 'online',
      nats_broker: 'connected',
      aws_cloud: 'connected',
      safety_permit: true,
      epo_armed: true,
    };
    return status;
  });

  // ─── REST: Overview KPIs ────────────────────────────────────────
  app.get('/api/overview', async () => {
    const d = sim.getCurrentData();
    const kpis: OverviewKPIs = {
      pue: 1.08,
      total_power_kw: d ? d.gpu_power_kw * 1.08 : 0,
      it_power_kw: d ? d.gpu_power_kw : 0,
      cooling_power_kw: d ? d.cooling_kw * 0.02 : 0,
      gpu_max_temp: d ? d.gpu_max_temp : 0,
      gpu_avg_temp: d ? d.gpu_max_temp - 5 : 0,
      supply_temp_avg: d ? d.supply_temp : 0,
      active_alarms: d && d.gpu_max_temp > 85 ? 1 : 0,
      uptime_hours: Math.floor(Date.now() / 3600000) % 8760,
    };
    return kpis;
  });

  // ─── REST: Alarms ───────────────────────────────────────────────
  app.get('/api/alarms', async () => {
    const alarms: AlarmRecord[] = [
      { id: 'ALM-001', severity: 'high', source: 'CDU-01', message: 'Supply temp above setpoint',
        timestamp: Date.now() - 30000, active: true, acknowledged: false, value: 41.2, threshold: 40.0 },
      { id: 'ALM-002', severity: 'medium', source: 'IPC-03', message: 'Zone B humidity high',
        timestamp: Date.now() - 120000, active: false, acknowledged: true },
    ];
    return alarms;
  });

  // ─── REST: Simulation control ───────────────────────────────────
  app.get('/api/sim/info', async () => ({
    frames: sim.getFrameCount(),
    current: sim.getCurrentFrame(),
  }));

  // ─── Start simulation broadcast ─────────────────────────────────
  sim.subscribe((data) => {
    const msg = JSON.stringify({ type: 'process_data', data });
    wsClients.forEach(ws => {
      try { ws.send(msg); } catch {}
    });
  });
  sim.start();

  // ─── Listen ─────────────────────────────────────────────────────
  await app.listen({ port: 4000, host: '0.0.0.0' });
  console.log('🏭 SCADA Backend running on http://localhost:4000');
  console.log('   WebSocket: ws://localhost:4000/ws');
  console.log('   REST API:  http://localhost:4000/api/*');
}

main().catch(console.error);
