/** Plant data types — shared between backend and frontend */

export interface ProcessData {
  time_s: number;
  gpu_max_temp: number;
  gpu_power_kw: number;
  supply_temp: number;
  return_temp: number;
  delta_t: number;
  flow_rate: number;
  cooling_kw: number;
  facility_water: number;
  pump_cmd: number;
  valve_cmd: number;
  pid_p: number;
  pid_i: number;
  pid_ff: number;
  sp_supply: number;
  sensor_valid: boolean;
  pump_running: boolean;
  leak: boolean;
}

export interface AlarmRecord {
  id: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  source: string;
  message: string;
  timestamp: number;
  active: boolean;
  acknowledged: boolean;
  value?: number;
  threshold?: number;
}

export interface SystemStatus {
  ipc_power: 'online' | 'offline' | 'fault';
  ipc_cooling: 'online' | 'offline' | 'fault';
  ipc_environment: 'online' | 'offline' | 'fault';
  ipc_safety: 'online' | 'offline' | 'fault';
  nats_broker: 'connected' | 'disconnected';
  aws_cloud: 'connected' | 'disconnected';
  safety_permit: boolean;
  epo_armed: boolean;
}

export interface OverviewKPIs {
  pue: number;
  total_power_kw: number;
  it_power_kw: number;
  cooling_power_kw: number;
  gpu_max_temp: number;
  gpu_avg_temp: number;
  supply_temp_avg: number;
  active_alarms: number;
  uptime_hours: number;
}
