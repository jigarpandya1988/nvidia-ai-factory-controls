import React from 'react';
import { useProcessStore } from '../stores/useProcessStore';
import { MetricCard } from '../components/common/MetricCard';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Pump, Valve, Motor, Tank, Sensor, Pipe, HeatExchanger } from '../components/pid/symbols';

export function Cooling() {
  const data = useProcessStore(s => s.current);
  const history = useProcessStore(s => s.history);
  const gpuStatus = !data ? 'ok' : data.gpu_max_temp > 90 ? 'critical' : data.gpu_max_temp > 80 ? 'warn' : 'ok';

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Cooling System — CDU Control</h1>

      {/* CDU Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
        <MetricCard label="Supply Temp" value={data?.supply_temp ?? 0} unit="°C" status={Math.abs((data?.supply_temp ?? 35) - 35) > 3 ? 'warn' : 'ok'} />
        <MetricCard label="Return Temp" value={data?.return_temp ?? 0} unit="°C" />
        <MetricCard label="Delta-T" value={data?.delta_t ?? 0} unit="°C" status={(data?.delta_t ?? 0) > 15 ? 'warn' : 'ok'} />
        <MetricCard label="Flow Rate" value={data?.flow_rate ?? 0} unit="LPM" />
        <MetricCard label="Pump Speed" value={data?.pump_cmd ?? 0} unit="%" />
        <MetricCard label="Valve Pos" value={data?.valve_cmd ?? 0} unit="%" />
        <MetricCard label="Cooling" value={data?.cooling_kw ?? 0} unit="kW" />
        <MetricCard label="GPU Max" value={data?.gpu_max_temp ?? 0} unit="°C" status={gpuStatus} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* CDU P&ID Detail */}
        <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
          <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">CDU-01 Process Diagram</h3>
          <svg viewBox="0 0 600 380" className="w-full" xmlns="http://www.w3.org/2000/svg">
            {/* Background grid */}
            <defs>
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1a1a24" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="600" height="380" fill="url(#grid)" />

            {/* Heat Exchanger */}
            <HeatExchanger x={300} y={80} capacity_kw={data?.cooling_kw ?? 0} label="HX-01" />

            {/* Pump + Motor */}
            <Pump x={120} y={220} running={data?.pump_running ?? false} speed={data?.pump_cmd ?? 0} label="P-01" />
            <Motor x={120} y={280} running={data?.pump_running ?? false} power={(data?.pump_cmd ?? 0) * 0.15} label="M-01" />
            <line x1="120" y1="234" x2="120" y2="266" stroke="#4caf50" strokeWidth="1.5" />

            {/* 3-Way Valve */}
            <Valve x={450} y={220} position={data?.valve_cmd ?? 0} type="3way" label="CV-01" />

            {/* Sensors */}
            <Sensor x={200} y={130} type="TT" value={data?.supply_temp ?? 0} unit="°C" tag="TT-101" valid={data?.sensor_valid} />
            <Sensor x={420} y={130} type="TT" value={data?.return_temp ?? 0} unit="°C" tag="TT-102" />
            <Sensor x={200} y={260} type="FT" value={data?.flow_rate ?? 0} unit="L" tag="FT-101" />
            <Sensor x={350} y={310} type="PT" value={3.2} unit="bar" tag="PT-101" />

            {/* Pipes with flow animation */}
            <Pipe x1={138} y1={220} x2={280} y2={80} type="supply" flowing={data?.pump_running} />
            <Pipe x1={322} y1={80} x2={450} y2={205} type="return" flowing={data?.pump_running} />
            <Pipe x1={450} y1={235} x2={450} y2={340} type="return" flowing={data?.pump_running} />
            <Pipe x1={450} y1={340} x2={120} y2={340} type="supply" flowing={data?.pump_running} />
            <Pipe x1={120} y1={340} x2={120} y2={238} type="supply" flowing={data?.pump_running} />

            {/* Facility Water (to HX top) */}
            <Pipe x1={300} y1={20} x2={300} y2={58} type="facility" flowing={true} />
            <text x="300" y="14" fill="#2e7d32" fontSize="8" textAnchor="middle">FACILITY WATER {data?.facility_water.toFixed(0) ?? '--'}°C</text>

            {/* GPU Rack Load (from right) */}
            <rect x="510" y="190" width="70" height="60" fill="#1a1a1a" stroke="#ff9800" strokeWidth="1.5" rx="4" />
            <text x="545" y="210" fill="#ff9800" fontSize="8" textAnchor="middle">GPU RACKS</text>
            <text x="545" y="228" fill="#fff" fontSize="11" textAnchor="middle" fontFamily="monospace">{data?.gpu_power_kw.toFixed(0) ?? '--'} kW</text>
            <text x="545" y="243" fill="#f44336" fontSize="9" textAnchor="middle">{data?.gpu_max_temp.toFixed(0) ?? '--'}°C</text>
            <Pipe x1={480} y1={220} x2={510} y2={220} type="return" flowing={data?.pump_running} />

            {/* Delta-T callout */}
            <rect x="240" y="170" width="60" height="22" fill="#0a0a0f" stroke="#444" rx="3" />
            <text x="270" y="184" fill="#00bcd4" fontSize="9" textAnchor="middle">ΔT {data?.delta_t.toFixed(1) ?? '--'}°C</text>
          </svg>
        </div>

        {/* Temperature Trend */}
        <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
          <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Temperature Trend (30s)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={history.slice(-300)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a24" />
              <XAxis dataKey="time_s" stroke="#555" fontSize={9} tickFormatter={v => `${v.toFixed(0)}s`} />
              <YAxis stroke="#555" fontSize={9} domain={[20, 100]} />
              <Tooltip contentStyle={{ background: '#12121a', border: '1px solid #333', fontSize: 11 }} />
              <Line type="monotone" dataKey="gpu_max_temp" stroke="#f44336" name="GPU" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="supply_temp" stroke="#2196f3" name="Supply" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="return_temp" stroke="#ff9800" name="Return" dot={false} />
              <Line type="monotone" dataKey="sp_supply" stroke="#2196f3" name="SP" dot={false} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* PID Tuning Info */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">PID Controller Status</h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          <MetricCard label="P-Term" value={data?.pid_p ?? 0} />
          <MetricCard label="I-Term" value={data?.pid_i ?? 0} />
          <MetricCard label="Feedforward" value={data?.pid_ff ?? 0} unit="%" />
          <MetricCard label="Setpoint" value={data?.sp_supply ?? 35} unit="°C" />
          <MetricCard label="Error" value={data ? (data.supply_temp - data.sp_supply) : 0} unit="°C" />
          <MetricCard label="Output" value={data?.pump_cmd ?? 0} unit="%" />
        </div>
      </div>
    </div>
  );
}
