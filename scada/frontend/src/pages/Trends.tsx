import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useProcessStore } from '../stores/useProcessStore';

export function Trends() {
  const history = useProcessStore(s => s.history);

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Process Trends</h1>

      {/* Temperature Chart */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Temperature Trends</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis dataKey="time_s" stroke="#666" fontSize={10} tickFormatter={v => `${v.toFixed(0)}s`} />
            <YAxis stroke="#666" fontSize={10} domain={[20, 100]} />
            <Tooltip contentStyle={{ background: '#1a1a24', border: '1px solid #333' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="gpu_max_temp" stroke="#f44336" name="GPU Max" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="supply_temp" stroke="#2196f3" name="Supply" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="return_temp" stroke="#ff9800" name="Return" dot={false} />
            <Line type="monotone" dataKey="sp_supply" stroke="#2196f3" name="Setpoint" dot={false} strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Controller Output Chart */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Controller Outputs</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis dataKey="time_s" stroke="#666" fontSize={10} tickFormatter={v => `${v.toFixed(0)}s`} />
            <YAxis stroke="#666" fontSize={10} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: '#1a1a24', border: '1px solid #333' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="pump_cmd" stroke="#76b900" name="Pump %" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="valve_cmd" stroke="#ff6600" name="Valve %" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="pid_ff" stroke="#9c27b0" name="Feedforward" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Power Chart */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Power & Cooling</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis dataKey="time_s" stroke="#666" fontSize={10} tickFormatter={v => `${v.toFixed(0)}s`} />
            <YAxis stroke="#666" fontSize={10} />
            <Tooltip contentStyle={{ background: '#1a1a24', border: '1px solid #333' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="gpu_power_kw" stroke="#ffc107" name="GPU Power kW" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="cooling_kw" stroke="#00bcd4" name="Cooling kW" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="flow_rate" stroke="#4caf50" name="Flow LPM" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
