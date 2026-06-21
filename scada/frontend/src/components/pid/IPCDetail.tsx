import React from 'react';
import { useProcessStore } from '../../stores/useProcessStore';
import { StatusDot } from '../common/StatusDot';

interface Props { ipc: string; }

const ipcInfo: Record<string, { name: string; role: string; hw: string; ip: string; cycle: string; tasks: string[]; tags: number }> = {
  'power': { name: 'IPC-01 Power Distribution', role: 'Power monitoring, PUE, UPS, ATS', hw: 'Beckhoff CX5140', ip: '192.168.100.10', cycle: '10 ms', tasks: ['Control_Task (10ms)', 'Communication_Task (100ms)'], tags: 120 },
  'cooling': { name: 'IPC-02 Cooling Control', role: 'CDU PID, pump/valve, GPU feedforward', hw: 'Beckhoff CX5240', ip: '192.168.100.20', cycle: '5 ms', tasks: ['Control_Task (5ms)', 'Communication_Task (100ms)'], tags: 250 },
  'environment': { name: 'IPC-03 Environment Monitor', role: 'Temperature, humidity, dew point', hw: 'WAGO PFC200', ip: '192.168.100.30', cycle: '100 ms', tasks: ['Monitor_Task (100ms)', 'Communication_Task (500ms)'], tags: 80 },
  'safety': { name: 'IPC-04 Safety Systems', role: 'EPO, fire, leak detection (SIL 2)', hw: 'Beckhoff CX5240 + TwinSAFE', ip: '192.168.100.40', cycle: '2 ms', tasks: ['Safety_Task (2ms)', 'Communication_Task (100ms)'], tags: 160 },
};

export function IPCDetail({ ipc }: Props) {
  const data = useProcessStore(s => s.current);
  const info = ipcInfo[ipc] || ipcInfo['cooling'];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface-3 rounded p-3 border border-surface-4 text-xs">
          <div className="text-gray-500 mb-2">Hardware</div>
          <div><span className="text-gray-500">Platform:</span> {info.hw}</div>
          <div><span className="text-gray-500">OS:</span> Debian Linux (PREEMPT_RT)</div>
          <div><span className="text-gray-500">Runtime:</span> CODESYS V3.5 SP20</div>
          <div><span className="text-gray-500">IP Address:</span> <span className="text-nvidia font-mono">{info.ip}</span></div>
          <div><span className="text-gray-500">OPC UA:</span> opc.tcp://{info.ip}:4840</div>
        </div>
        <div className="bg-surface-3 rounded p-3 border border-surface-4 text-xs">
          <div className="text-gray-500 mb-2">Configuration</div>
          <div><span className="text-gray-500">Role:</span> {info.role}</div>
          <div><span className="text-gray-500">Fastest Cycle:</span> {info.cycle}</div>
          <div><span className="text-gray-500">Published Tags:</span> {info.tags}</div>
          <div><span className="text-gray-500">NATS Bridge:</span> bridge-{ipc}</div>
        </div>
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4 text-xs">
        <div className="text-gray-500 mb-2">Task Configuration</div>
        {info.tasks.map((t, i) => (
          <div key={i} className="flex justify-between py-0.5">
            <span>{t}</span>
            <span className="text-green-400">Running</span>
          </div>
        ))}
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-xs text-gray-500 mb-2">Health</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <StatusDot status="ok" label="Heartbeat: Active" />
          <StatusDot status="ok" label="OPC UA: Connected" />
          <StatusDot status="ok" label="NATS Bridge: Connected" />
          <StatusDot status="ok" label="Watchdog: OK" />
          <StatusDot status="ok" label={`CPU: ${12 + Math.random() * 8 | 0}%`} />
          <StatusDot status="ok" label={`RAM: ${45 + Math.random() * 10 | 0}%`} />
        </div>
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4 text-xs">
        <div className="text-gray-500 mb-2">Peer Exchange (NATS)</div>
        <div className="flex gap-3">
          {['power','cooling','environment','safety'].filter(p => p !== ipc).map(peer => (
            <div key={peer} className="px-2 py-1 bg-surface-1 rounded border border-surface-4">
              <div className="text-[9px] text-gray-500">{peer}</div>
              <div className="text-green-400 text-[10px]">● alive ~2ms</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
