import React from 'react';
import { useProcessStore } from '../../stores/useProcessStore';
import { MetricCard } from '../common/MetricCard';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

export function CDUDetail() {
  const data = useProcessStore(s => s.current);
  const history = useProcessStore(s => s.history);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Supply Temp" value={data?.supply_temp ?? 0} unit="°C" 
          status={Math.abs((data?.supply_temp ?? 35) - 35) > 3 ? 'warn' : 'ok'} />
        <MetricCard label="Return Temp" value={data?.return_temp ?? 0} unit="°C" />
        <MetricCard label="Flow Rate" value={data?.flow_rate ?? 0} unit="LPM" />
        <MetricCard label="Cooling Power" value={data?.cooling_kw ?? 0} unit="kW" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Pump</div>
          <div className="text-2xl font-mono font-bold text-nvidia">{data?.pump_cmd.toFixed(0) ?? '--'}%</div>
          <div className="text-xs text-gray-500 mt-1">
            Status: {data?.pump_running ? '● Running' : '○ Stopped'} | 
            VFD: OK | Hours: 1,247
          </div>
          <div className="mt-2 w-full h-2 bg-surface-1 rounded-full">
            <div className="h-full bg-nvidia rounded-full transition-all" style={{width: `${data?.pump_cmd ?? 0}%`}} />
          </div>
        </div>
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">3-Way Valve</div>
          <div className="text-2xl font-mono font-bold text-orange-400">{data?.valve_cmd.toFixed(0) ?? '--'}%</div>
          <div className="text-xs text-gray-500 mt-1">
            0% = Full Bypass | 100% = Full Process
          </div>
          <div className="mt-2 w-full h-2 bg-surface-1 rounded-full">
            <div className="h-full bg-orange-500 rounded-full transition-all" style={{width: `${data?.valve_cmd ?? 0}%`}} />
          </div>
        </div>
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-[10px] text-gray-500 uppercase mb-2">Control Loop Trend</div>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={history.slice(-300)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1a24" />
            <XAxis dataKey="time_s" hide />
            <YAxis stroke="#444" fontSize={9} domain={[0, 100]} />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <Line type="monotone" dataKey="pump_cmd" stroke="#76b900" name="Pump" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="valve_cmd" stroke="#ff6600" name="Valve" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-gray-500">PID Pump Loop</div>
          <div>Kp: 3.0 | Ti: 20s | Td: 0s</div>
          <div>SP: 35.0°C | PV: {data?.supply_temp.toFixed(1) ?? '--'}°C</div>
          <div>Output: {data?.pump_cmd.toFixed(1) ?? '--'}%</div>
        </div>
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-gray-500">PID Valve Loop</div>
          <div>Kp: 5.0 | Ti: 15s | Td: 2s</div>
          <div>SP: 35.0°C | PV: {data?.supply_temp.toFixed(1) ?? '--'}°C</div>
          <div>Output: {data?.valve_cmd.toFixed(1) ?? '--'}%</div>
        </div>
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-gray-500">Feedforward</div>
          <div>Gain: 0.08 %/kW</div>
          <div>GPU Power: {data?.gpu_power_kw.toFixed(0) ?? '--'} kW</div>
          <div>FF Output: {data?.pid_ff.toFixed(1) ?? '--'}%</div>
        </div>
      </div>
    </div>
  );
}
