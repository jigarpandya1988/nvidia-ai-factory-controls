import React from 'react';
import { useProcessStore } from '../../stores/useProcessStore';
import { MetricCard } from '../common/MetricCard';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid } from 'recharts';

interface Props { rackId: number; }

export function RackDetail({ rackId }: Props) {
  const data = useProcessStore(s => s.current);
  const history = useProcessStore(s => s.history);
  const rackTemp = data ? data.gpu_max_temp + (rackId - 2.5) * 3 : 0;
  const rackPower = data ? data.gpu_power_kw / 4 : 0;  // Per-rack

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Junction Temp" value={rackTemp} unit="°C" 
          status={rackTemp > 90 ? 'critical' : rackTemp > 80 ? 'warn' : 'ok'} />
        <MetricCard label="Power Draw" value={rackPower} unit="kW" />
        <MetricCard label="Inlet Coolant" value={data?.supply_temp ?? 0} unit="°C" />
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-gray-500 mb-1">Hardware</div>
          <div>Platform: NVIDIA GB200 NVL72</div>
          <div>GPUs: 72 × GB200</div>
          <div>TDP: 140 kW max</div>
          <div>Cooling: Direct Liquid (DLC)</div>
        </div>
        <div className="bg-surface-3 rounded p-3 border border-surface-4">
          <div className="text-gray-500 mb-1">Thermal</div>
          <div>Throttle Temp: 95°C</div>
          <div>Coolant Flow: {data ? (data.flow_rate / 4).toFixed(0) : '--'} LPM</div>
          <div>Headroom: {(95 - rackTemp).toFixed(1)}°C</div>
          <div>Outlet Temp: {data ? (data.supply_temp + data.delta_t).toFixed(1) : '--'}°C</div>
        </div>
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-[10px] text-gray-500 uppercase mb-2">GPU Temperature Trend (30s)</div>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={history.slice(-300)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1a24" />
            <XAxis dataKey="time_s" hide />
            <YAxis stroke="#444" fontSize={9} domain={[40, 100]} />
            <Line type="monotone" dataKey="gpu_max_temp" stroke="#f44336" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
