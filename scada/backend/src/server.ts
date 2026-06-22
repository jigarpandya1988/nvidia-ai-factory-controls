/**
 * SCADA Backend Server
 * ====================
 * - WebSocket: real-time process data push to frontend
 * - REST API: alarms, configuration, historical queries
 * - Connects to NATS broker (with simulation fallback for demo)
 */

import Fastify from 'fastify';
import websocket from '@fastify/websocket';
import cors from '@fastify/cors';
import { connect, NatsConnection, Subscription } from 'nats';
import { SimulationAdapter } from './services/simulation-adapter';
import { AlarmRecord, SystemStatus, OverviewKPIs } from './types/plant';
import { registerAuth, requireAuth } from './auth/middleware';

const app = Fastify({ logger: true });
const NATS_URL = process.env.NATS_URL || 'nats://localhost:4222';
const PORT = Number(process.env.PORT || '4000');
const USE_SIM_FALLBACK = process.env.SCADA_SIM_FALLBACK !== 'false';

// Active WebSocket clients
const wsClients = new Set<any>();
let sim: SimulationAdapter | null = null;
let natsConn: NatsConnection | null = null;
const natsSubs: Subscription[] = [];

let latestData = {
  time_s: 0,
  gpu_max_temp: 0,
  gpu_power_kw: 0,
  supply_temp: 0,
  return_temp: 0,
  delta_t: 0,
  flow_rate: 0,
  cooling_kw: 0,
  facility_water: 0,
  pump_cmd: 0,
  valve_cmd: 0,
  pid_p: 0,
  pid_i: 0,
  pid_ff: 0,
  sp_supply: 35,
  sensor_valid: true,
  pump_running: false,
  leak: false,
};

const latestStatus: SystemStatus = {
  ipc_power: 'offline',
  ipc_cooling: 'offline',
  ipc_environment: 'offline',
  ipc_safety: 'offline',
  nats_broker: 'disconnected',
  aws_cloud: 'disconnected',
  safety_permit: true,
  epo_armed: true,
};

const alarmStore: AlarmRecord[] = [];

function toNumber(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const parsed = Number(v);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function pushProcessData() {
  const msg = JSON.stringify({ type: 'process_data', data: latestData });
  wsClients.forEach(ws => {
    try { ws.send(msg); } catch {}
  });
}

function upsertAlarm(next: AlarmRecord) {
  const idx = alarmStore.findIndex(a => a.id === next.id);
  if (idx >= 0) alarmStore[idx] = next;
  else alarmStore.unshift(next);
  if (alarmStore.length > 200) alarmStore.length = 200;
}

function updateFromSimulation(data: any) {
  latestData = {
    ...latestData,
    time_s: toNumber(data.sim_time_s) ?? latestData.time_s,
    gpu_max_temp: toNumber(data.gpu_max_temp) ?? latestData.gpu_max_temp,
    gpu_power_kw: toNumber(data.gpu_total_power_kw) ?? latestData.gpu_power_kw,
    supply_temp: toNumber(data.supply_temp) ?? latestData.supply_temp,
    return_temp: toNumber(data.return_temp) ?? latestData.return_temp,
    delta_t: toNumber(data.delta_t) ?? latestData.delta_t,
    flow_rate: toNumber(data.flow_rate) ?? latestData.flow_rate,
    cooling_kw: toNumber(data.cooling_capacity_kw) ?? latestData.cooling_kw,
    facility_water: toNumber(data.facility_water_temp) ?? latestData.facility_water,
    pump_cmd: toNumber(data.pump_speed) ?? latestData.pump_cmd,
    valve_cmd: toNumber(data.valve_position) ?? latestData.valve_cmd,
    sensor_valid: data.supply_temp !== -999.0 && data.return_temp !== -999.0 && data.flow_rate !== -999.0,
    pump_running: !!data.pump_running,
    leak: !!data.leak_detected,
  };
  pushProcessData();
}

function updateFromBridgeTag(tag: string, value: unknown) {
  const numeric = toNumber(value);
  switch (tag) {
    case 'CDU_01.SupplyTemp':
      if (numeric !== null) latestData.supply_temp = numeric;
      break;
    case 'CDU_01.ReturnTemp':
      if (numeric !== null) latestData.return_temp = numeric;
      break;
    case 'CDU_01.DeltaT':
      if (numeric !== null) latestData.delta_t = numeric;
      break;
    case 'CDU_01.FlowRate':
      if (numeric !== null) latestData.flow_rate = numeric;
      break;
    case 'CDU_01.PumpSpeed':
      if (numeric !== null) latestData.pump_cmd = numeric;
      break;
    case 'CDU_01.ValvePos':
      if (numeric !== null) latestData.valve_cmd = numeric;
      break;
    case 'CDU_01.Capacity_kW':
      if (numeric !== null) latestData.cooling_kw = numeric;
      break;
    case 'GPU.MaxTemp':
      if (numeric !== null) latestData.gpu_max_temp = numeric;
      break;
    case 'GPU.TotalPower_kW':
      if (numeric !== null) latestData.gpu_power_kw = numeric;
      break;
    case 'CDU_01.Alm_Leak':
      latestData.leak = !!value;
      break;
    default:
      break;
  }
  latestData.time_s = Date.now() / 1000;
  latestData.sensor_valid = true;
  latestData.pump_running = latestData.pump_cmd > 0;
  pushProcessData();
}

async function connectNats() {
  natsConn = await connect({
    servers: NATS_URL,
    name: 'scada-backend',
    maxReconnectAttempts: -1,
    reconnectTimeWait: 1000,
  });
  latestStatus.nats_broker = 'connected';

  const telemetrySim = natsConn.subscribe('aifactory.*.*.sim.telemetry.>');
  const telemetryBridge = natsConn.subscribe('aifactory.*.*.telemetry.>');
  const alarms = natsConn.subscribe('aifactory.*.*.alarms.>');
  const status = natsConn.subscribe('aifactory.*.*.status');
  natsSubs.push(telemetrySim, telemetryBridge, alarms, status);

  void (async () => {
    for await (const msg of telemetrySim) {
      try {
        updateFromSimulation(JSON.parse(msg.data.toString()));
      } catch {}
    }
  })();

  void (async () => {
    for await (const msg of telemetryBridge) {
      try {
        const payload = JSON.parse(msg.data.toString());
        const tag = msg.subject.split('.').slice(4).join('.');
        if (typeof payload === 'object' && payload && 'v' in payload) {
          updateFromBridgeTag(tag, (payload as { v: unknown }).v);
        }
      } catch {}
    }
  })();

  void (async () => {
    for await (const msg of alarms) {
      try {
        const payload = JSON.parse(msg.data.toString()) as Partial<AlarmRecord> & { t?: number };
        const severity = (payload.severity || 'medium') as AlarmRecord['severity'];
        const record: AlarmRecord = {
          id: payload.id || `${msg.subject}-${Date.now()}`,
          severity,
          source: payload.source || msg.subject.split('.')[2] || 'unknown',
          message: payload.message || 'Alarm',
          timestamp: payload.timestamp || payload.t || Date.now(),
          active: payload.active ?? true,
          acknowledged: payload.acknowledged ?? false,
          value: payload.value,
          threshold: payload.threshold,
        };
        upsertAlarm(record);
      } catch {}
    }
  })();

  void (async () => {
    for await (const msg of status) {
      try {
        const subjectParts = msg.subject.split('.');
        const ipc = subjectParts[2];
        const payload = JSON.parse(msg.data.toString()) as { healthy?: boolean };
        const state = payload.healthy === false ? 'fault' : 'online';
        if (ipc === 'power') latestStatus.ipc_power = state;
        if (ipc === 'cooling') latestStatus.ipc_cooling = state;
        if (ipc === 'environment') latestStatus.ipc_environment = state;
        if (ipc === 'safety') latestStatus.ipc_safety = state;
      } catch {}
    }
  })();
}

async function main() {
  await app.register(cors, { origin: true });
  await app.register(websocket);
  await registerAuth(app);

  try {
    await connectNats();
    app.log.info(`Connected to NATS: ${NATS_URL}`);
  } catch (error) {
    latestStatus.nats_broker = 'disconnected';
    if (!USE_SIM_FALLBACK) throw error;
    app.log.warn('NATS unavailable, falling back to simulation adapter');
    sim = new SimulationAdapter();
    sim.subscribe((data) => {
      latestData = data;
      pushProcessData();
    });
    sim.start();
  }

  // ─── WebSocket: Real-time process data ──────────────────────────
  app.get('/ws', { websocket: true, preValidation: requireAuth }, (socket, req) => {
    wsClients.add(socket);
    console.log(`[WS] Client connected (${wsClients.size} total)`);

    socket.on('message', (msg: Buffer) => {
      if (!sim) return;
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
  app.get('/api/status', { preHandler: requireAuth }, async () => latestStatus);

  // ─── REST: Overview KPIs ────────────────────────────────────────
  app.get('/api/overview', { preHandler: requireAuth }, async () => {
    const d = latestData;
    const kpis: OverviewKPIs = {
      pue: 1.08,
      total_power_kw: d.gpu_power_kw * 1.08,
      it_power_kw: d.gpu_power_kw,
      cooling_power_kw: d.cooling_kw * 0.02,
      gpu_max_temp: d.gpu_max_temp,
      gpu_avg_temp: Math.max(0, d.gpu_max_temp - 5),
      supply_temp_avg: d.supply_temp,
      active_alarms: alarmStore.filter(a => a.active).length,
      uptime_hours: Math.floor(Date.now() / 3600000) % 8760,
    };
    return kpis;
  });

  // ─── REST: Alarms ───────────────────────────────────────────────
  app.get('/api/alarms', { preHandler: requireAuth }, async () => alarmStore);

  // ─── REST: Simulation control ───────────────────────────────────
  app.get('/api/sim/info', { preHandler: requireAuth }, async () => ({
    enabled: !!sim,
    frames: sim?.getFrameCount() || 0,
    current: sim?.getCurrentFrame() || 0,
  }));

  // ─── Listen ─────────────────────────────────────────────────────
  app.addHook('onClose', async () => {
    sim?.stop();
    for (const sub of natsSubs) sub.unsubscribe();
    if (natsConn) await natsConn.close();
  });

  await app.listen({ port: PORT, host: '0.0.0.0' });
  console.log(`SCADA Backend running on http://localhost:${PORT}`);
  console.log(`WebSocket: ws://localhost:${PORT}/ws`);
  console.log(`REST API:  http://localhost:${PORT}/api/*`);
}

main().catch(console.error);
