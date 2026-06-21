import React, { useState } from 'react';
import { useProcessStore } from '../stores/useProcessStore';
import { MetricCard } from '../components/common/MetricCard';
import { StatusDot } from '../components/common/StatusDot';
import { DetailModal } from '../components/common/DetailModal';
import { RackDetail } from '../components/pid/RackDetail';
import { CDUDetail } from '../components/pid/CDUDetail';
import { PipeDetail } from '../components/pid/PipeDetail';
import { IPCDetail } from '../components/pid/IPCDetail';
import { InfraDetail } from '../components/pid/InfraDetail';

export function Overview() {
  const data = useProcessStore(s => s.current);
  const [modal, setModal] = useState<{type: string; id?: number} | null>(null);

  const gpuStatus = !data ? 'ok' : data.gpu_max_temp > 90 ? 'critical' : data.gpu_max_temp > 80 ? 'warn' : 'ok';
  const supplyStatus = !data ? 'ok' : Math.abs(data.supply_temp - 35) > 5 ? 'warn' : 'ok';

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Facility Overview</h1>
        <span className="text-xs text-gray-500">
          Sim Time: {data ? data.time_s.toFixed(1) : '--'}s
        </span>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard label="PUE" value={1.08} status="ok" />
        <MetricCard label="IT Power" value={data?.gpu_power_kw ?? 0} unit="kW" />
        <MetricCard label="Cooling" value={data?.cooling_kw ?? 0} unit="kW" />
        <MetricCard label="GPU Max" value={data?.gpu_max_temp ?? 0} unit="°C" status={gpuStatus} />
        <MetricCard label="Supply Temp" value={data?.supply_temp ?? 0} unit="°C" status={supplyStatus} />
        <MetricCard label="Flow Rate" value={data?.flow_rate ?? 0} unit="LPM" />
      </div>

      {/* Status + P&ID */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* System Status Panel — CLICKABLE ITEMS */}
        <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
          <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">System Status</h3>
          <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'ipc-power'})}><StatusDot status="ok" label="IPC-01 Power" /></div>
          <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'ipc-cooling'})}><StatusDot status="ok" label="IPC-02 Cooling" /></div>
          <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'ipc-environment'})}><StatusDot status="ok" label="IPC-03 Environment" /></div>
          <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'ipc-safety'})}><StatusDot status="ok" label="IPC-04 Safety" /></div>
          <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'nats'})}><StatusDot status="ok" label="NATS Broker" /></div>
          <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'aws'})}><StatusDot status="ok" label="AWS Cloud" /></div>
          <div className="mt-3 pt-3 border-t border-surface-4">
            <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'pump'})}><StatusDot status={data?.pump_running ? 'ok' : 'fault'} label="CDU Pump" /></div>
            <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'sensors'})}><StatusDot status={data?.sensor_valid ? 'ok' : 'fault'} label="Sensors" /></div>
            <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'leak'})}><StatusDot status={data?.leak ? 'fault' : 'ok'} label={data?.leak ? 'LEAK!' : 'No Leaks'} /></div>
            <div className="cursor-pointer hover:bg-surface-3 rounded px-1 -mx-1" onClick={() => setModal({type:'epo'})}><StatusDot status="ok" label="EPO Armed" /></div>
          </div>
        </div>

        {/* Simplified P&ID */}
        <div className="lg:col-span-3 bg-surface-2 rounded-lg p-4 border border-surface-4">
          <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Process Flow</h3>
          <div className="relative h-64 bg-surface-1 rounded border border-surface-4 overflow-hidden">
            {/* SVG P&ID Diagram */}
            <svg viewBox="0 0 800 300" className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
              {/* GPU Racks — CLICKABLE */}
              {[0,1,2,3].map(i => (
                <g key={i} className="cursor-pointer hover:opacity-80" onClick={() => setModal({type:'rack', id:i+1})}>
                  <rect x={80+i*120} y={20} width={60} height={100} fill="#222" stroke="#444" rx="4" />
                  <rect x={80+i*120} y={25} width={8} height={90}
                    fill={!data ? '#333' : data.gpu_max_temp > 85 ? '#f44' : data.gpu_max_temp > 70 ? '#fa0' : '#4c4'} />
                  <text x={110+i*120} y={140} fill="#888" fontSize="10" textAnchor="middle">
                    Rack {i+1}
                  </text>
                  <text x={110+i*120} y={155} fill="#aaa" fontSize="9" textAnchor="middle">
                    {data ? (data.gpu_max_temp + (i-1.5)*3).toFixed(0) : '--'}°C
                  </text>
                </g>
              ))}

              {/* Supply pipe (blue) — CLICKABLE */}
              <line x1="50" y1="200" x2="600" y2="200" stroke="#1565c0" strokeWidth="4" 
                className="cursor-pointer hover:stroke-[#42a5f5]" onClick={() => setModal({type:'pipe-supply'})} />
              <text x="40" y="195" fill="#1565c0" fontSize="9">SUPPLY</text>
              <text x="310" y="215" fill="#1976d2" fontSize="10">
                {data?.supply_temp.toFixed(1) ?? '--'}°C
              </text>

              {/* Return pipe (red) — CLICKABLE */}
              <line x1="50" y1="170" x2="600" y2="170" stroke="#c62828" strokeWidth="4"
                className="cursor-pointer hover:stroke-[#ef5350]" onClick={() => setModal({type:'pipe-return'})} />
              <text x="40" y="165" fill="#c62828" fontSize="9">RETURN</text>

              {/* Branch pipes */}
              {[0,1,2,3].map(i => (
                <g key={`pipe-${i}`}>
                  <line x1={110+i*120} y1={120} x2={110+i*120} y2={170} stroke="#c62828" strokeWidth="2" />
                  <line x1={110+i*120} y1={200} x2={110+i*120} y2={120} stroke="#1565c0" strokeWidth="2" strokeDasharray="4" />
                </g>
              ))}

              {/* CDU — CLICKABLE */}
              <g className="cursor-pointer hover:opacity-80" onClick={() => setModal({type:'cdu'})}>
              <rect x={620} y={160} width={120} height={70} fill="#1a3355" stroke="#2a5580" rx="6" />
              <text x={680} y={185} fill="#76b900" fontSize="11" textAnchor="middle" fontWeight="bold">CDU-01</text>
              {/* Pump symbol */}
              <circle cx={650} cy={210} r={12} fill="none" stroke="#76b900" strokeWidth="2" />
              <text x={650} y={214} fill="#76b900" fontSize="8" textAnchor="middle">P</text>
              <text x={650} y={245} fill="#999" fontSize="9" textAnchor="middle">{data?.pump_cmd.toFixed(0) ?? '--'}%</text>
              {/* Valve symbol */}
              <polygon points="700,200 710,210 700,220 690,210" fill="none" stroke="#ff6600" strokeWidth="2" />
              <text x={700} y={245} fill="#999" fontSize="9" textAnchor="middle">{data?.valve_cmd.toFixed(0) ?? '--'}%</text>
              </g>

              {/* Cooling Tower */}
              <rect x={650} y={260} width={80} height={30} fill="#3a3a3a" stroke="#555" rx="4" />
              <text x={690} y={280} fill="#888" fontSize="9" textAnchor="middle">CT-01 {data?.facility_water.toFixed(0) ?? '--'}°C</text>

              {/* Flow arrows */}
              <polygon points="590,200 600,196 600,204" fill="#1565c0" />
              <polygon points="60,170 50,166 50,174" fill="#c62828" />
            </svg>
          </div>
        </div>
      </div>

      {/* Controller Panel */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard label="Pump Speed" value={data?.pump_cmd ?? 0} unit="%" />
        <MetricCard label="Valve Position" value={data?.valve_cmd ?? 0} unit="%" />
        <MetricCard label="Feedforward" value={data?.pid_ff ?? 0} unit="%" />
        <MetricCard label="PID P-Term" value={data?.pid_p ?? 0} />
        <MetricCard label="PID I-Term" value={data?.pid_i ?? 0} />
      </div>

      {/* Detail Modals — open when clicking P&ID objects */}
      <DetailModal open={modal?.type === 'rack'} onClose={() => setModal(null)} title={`GPU Rack ${modal?.id ?? ''} — Detail`}>
        <RackDetail rackId={modal?.id ?? 1} />
      </DetailModal>
      <DetailModal open={modal?.type === 'cdu'} onClose={() => setModal(null)} title="CDU-01 — Coolant Distribution Unit">
        <CDUDetail />
      </DetailModal>
      <DetailModal open={modal?.type === 'pipe-supply'} onClose={() => setModal(null)} title="Supply Header — Cold Coolant">
        <PipeDetail type="supply" />
      </DetailModal>
      <DetailModal open={modal?.type === 'pipe-return'} onClose={() => setModal(null)} title="Return Header — Hot Coolant">
        <PipeDetail type="return" />
      </DetailModal>

      {/* IPC Detail Modals */}
      <DetailModal open={modal?.type === 'ipc-power'} onClose={() => setModal(null)} title="IPC-01 — Power Distribution Controller">
        <IPCDetail ipc="power" />
      </DetailModal>
      <DetailModal open={modal?.type === 'ipc-cooling'} onClose={() => setModal(null)} title="IPC-02 — Cooling Controller">
        <IPCDetail ipc="cooling" />
      </DetailModal>
      <DetailModal open={modal?.type === 'ipc-environment'} onClose={() => setModal(null)} title="IPC-03 — Environment Monitor">
        <IPCDetail ipc="environment" />
      </DetailModal>
      <DetailModal open={modal?.type === 'ipc-safety'} onClose={() => setModal(null)} title="IPC-04 — Safety Systems (SIL 2)">
        <IPCDetail ipc="safety" />
      </DetailModal>

      {/* Infrastructure Detail Modals */}
      <DetailModal open={modal?.type === 'nats'} onClose={() => setModal(null)} title="NATS Broker — Message Bus">
        <InfraDetail type="nats" />
      </DetailModal>
      <DetailModal open={modal?.type === 'aws'} onClose={() => setModal(null)} title="AWS Cloud — IoT Core + Timestream">
        <InfraDetail type="aws" />
      </DetailModal>
      <DetailModal open={modal?.type === 'pump'} onClose={() => setModal(null)} title="CDU-01 Primary Pump">
        <InfraDetail type="pump" />
      </DetailModal>
      <DetailModal open={modal?.type === 'sensors'} onClose={() => setModal(null)} title="Sensor Validation System">
        <InfraDetail type="sensors" />
      </DetailModal>
      <DetailModal open={modal?.type === 'leak'} onClose={() => setModal(null)} title="Leak Detection System">
        <InfraDetail type="leak" />
      </DetailModal>
      <DetailModal open={modal?.type === 'epo'} onClose={() => setModal(null)} title="Emergency Power Off (EPO)">
        <InfraDetail type="epo" />
      </DetailModal>
    </div>
  );
}
