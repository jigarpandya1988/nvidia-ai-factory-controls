import React from 'react';
import { useProcessStore } from '../../stores/useProcessStore';
import { MetricCard } from '../common/MetricCard';

interface Props { type: 'supply' | 'return'; }

export function PipeDetail({ type }: Props) {
  const data = useProcessStore(s => s.current);
  const isSupply = type === 'supply';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Temperature" value={isSupply ? (data?.supply_temp ?? 0) : (data?.return_temp ?? 0)} unit="°C" 
          status={isSupply && Math.abs((data?.supply_temp ?? 35) - 35) > 5 ? 'warn' : 'ok'} />
        <MetricCard label="Flow Rate" value={data?.flow_rate ?? 0} unit="LPM" />
        <MetricCard label="Pressure" value={3.2} unit="bar" />
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4 text-xs">
        <div className="text-gray-500 mb-2">{isSupply ? 'Supply' : 'Return'} Header Specifications</div>
        <div className="grid grid-cols-2 gap-2">
          <div>Pipe Size: DN80 (3")</div>
          <div>Material: SS 316L</div>
          <div>Design Pressure: 10 bar</div>
          <div>Design Temp: -10 to 90°C</div>
          <div>Insulation: 25mm Armaflex</div>
          <div>Fluid: PG/Water 30%</div>
          <div>Max Velocity: 3 m/s</div>
          <div>Current Velocity: {data ? (data.flow_rate / 60 / 0.005 / 1000).toFixed(1) : '--'} m/s</div>
        </div>
      </div>

      <div className="bg-surface-3 rounded p-3 border border-surface-4 text-xs">
        <div className="text-gray-500 mb-2">Connected Equipment</div>
        <div className="space-y-1">
          <div className="flex justify-between"><span>→ Rack 1 branch</span><span className="text-green-400">OK</span></div>
          <div className="flex justify-between"><span>→ Rack 2 branch</span><span className="text-green-400">OK</span></div>
          <div className="flex justify-between"><span>→ Rack 3 branch</span><span className="text-green-400">OK</span></div>
          <div className="flex justify-between"><span>→ Rack 4 branch</span><span className="text-green-400">OK</span></div>
          <div className="flex justify-between"><span>→ CDU-01 {isSupply ? 'outlet' : 'inlet'}</span><span className="text-green-400">OK</span></div>
        </div>
      </div>
    </div>
  );
}
