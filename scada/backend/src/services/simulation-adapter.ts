/**
 * Simulation Data Adapter
 * Reads simulation_output.json and replays it in real-time via WebSocket.
 * In production, this would be replaced by NATS subscription.
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { ProcessData } from '../types/plant';

export class SimulationAdapter {
  private data: ProcessData[] = [];
  private currentFrame = 0;
  private playing = true;
  private speed = 1;
  private listeners: Set<(data: ProcessData) => void> = new Set();
  private interval: NodeJS.Timeout | null = null;

  constructor() {
    this.loadData();
  }

  private loadData() {
    try {
      const path = resolve(__dirname, '../../../../simulation_output.json');
      const raw = readFileSync(path, 'utf-8');
      this.data = JSON.parse(raw);
      console.log(`[SimAdapter] Loaded ${this.data.length} data points`);
    } catch (e) {
      console.warn('[SimAdapter] No simulation data found, generating demo');
      this.data = this.generateDemo();
    }
  }

  private generateDemo(): ProcessData[] {
    const data: ProcessData[] = [];
    for (let i = 0; i < 1800; i++) {
      const t = i * 0.1;
      const load = t < 10 ? 0.1 : t < 30 ? 0.1 + 0.9 * (t - 10) / 20 : 1.0;
      data.push({
        time_s: t,
        gpu_max_temp: 45 + load * 48,
        gpu_power_kw: 50 + load * 230,
        supply_temp: 35 + load * 5,
        return_temp: 40 + load * 8,
        delta_t: 5 + load * 3,
        flow_rate: 200 + load * 200,
        cooling_kw: load * 280,
        facility_water: 18 + load * 2,
        pump_cmd: 30 + load * 60,
        valve_cmd: 30 + load * 50,
        pid_p: load * 5,
        pid_i: load * 10,
        pid_ff: load * 20,
        sp_supply: 35,
        sensor_valid: true,
        pump_running: true,
        leak: false,
      });
    }
    return data;
  }

  start() {
    if (this.interval) return;
    this.interval = setInterval(() => {
      if (!this.playing || this.data.length === 0) return;
      const frame = this.data[this.currentFrame];
      this.listeners.forEach(cb => cb(frame));
      this.currentFrame = (this.currentFrame + 1) % this.data.length;
    }, 100 / this.speed); // 10 FPS base rate
  }

  stop() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  subscribe(callback: (data: ProcessData) => void) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  setSpeed(speed: number) {
    this.speed = Math.max(1, Math.min(20, speed));
    // Restart interval with new timing
    if (this.interval) {
      this.stop();
      this.start();
    }
  }
  setPlaying(playing: boolean) { this.playing = playing; }
  seek(frame: number) { this.currentFrame = Math.max(0, Math.min(this.data.length - 1, frame)); }
  getFrameCount() { return this.data.length; }
  getCurrentFrame() { return this.currentFrame; }
  getCurrentData(): ProcessData | null { return this.data[this.currentFrame] ?? null; }
}
