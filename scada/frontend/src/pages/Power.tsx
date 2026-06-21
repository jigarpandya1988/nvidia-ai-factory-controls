import React from 'react';
import { useProcessStore } from '../stores/useProcessStore';
import { MetricCard } from '../components/common/MetricCard';
import { StatusDot } from '../components/common/StatusDot';
import { Breaker, Transformer, UPS, Sensor, Pipe, Motor, Generator } from '../components/pid/symbols';

export function Power() {
  const data = useProcessStore(s => s.current);
  const itPower = data?.gpu_power_kw ?? 0;
  const totalPower = itPower * 1.08;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Power Distribution — IPC-01</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard label="PUE" value={1.08} status="ok" />
        <MetricCard label="Total Facility" value={totalPower} unit="kW" />
        <MetricCard label="IT Equipment" value={itPower} unit="kW" />
        <MetricCard label="Grid Frequency" value={60.0} unit="Hz" status="ok" />
        <MetricCard label="Bus Voltage" value={800} unit="VDC" status="ok" />
        <MetricCard label="Phase Imbalance" value={0.4} unit="%" status="ok" />
      </div>

      {/* Single Line Diagram with ISA Symbols */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Single Line Diagram</h3>
        <div className="bg-surface-1 rounded border border-surface-4 overflow-hidden">
          <svg viewBox="0 0 900 380" className="w-full" xmlns="http://www.w3.org/2000/svg">
            {/* Background grid */}
            <defs>
              <pattern id="pgrid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#111118" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="900" height="380" fill="url(#pgrid)" />

            {/* ─── UTILITY FEED ─── */}
            <rect x="20" y="60" width="80" height="35" fill="#1b5e20" stroke="#4caf50" strokeWidth="1.5" rx="4" />
            <text x="60" y="75" fill="#4caf50" fontSize="8" textAnchor="middle">UTILITY</text>
            <text x="60" y="87" fill="#4caf50" fontSize="9" textAnchor="middle" fontWeight="bold">13.8 kV</text>
            <Pipe x1={100} y1={77} x2={140} y2={77} type="facility" flowing={true} />

            {/* Main Breaker */}
            <Breaker x={160} y={77} closed={true} label="CB-MAIN" rating="2000A" />

            {/* Transformer */}
            <Pipe x1={180} y1={77} x2={220} y2={77} type="facility" flowing={true} />
            <Transformer x={250} y={77} label="XFMR-01" primaryV="13.8kV" secondaryV="480V" />

            {/* Secondary Breaker */}
            <Pipe x1={280} y1={77} x2={310} y2={77} type="facility" flowing={true} />
            <Breaker x={330} y={77} closed={true} label="CB-SEC" rating="4000A" />

            {/* ATS (Automatic Transfer Switch) */}
            <Pipe x1={350} y1={77} x2={390} y2={77} type="facility" flowing={true} />
            <rect x="390" y="60" width="60" height="35" fill="#1a237e" stroke="#3f51b5" strokeWidth="1.5" rx="4" />
            <text x="420" y="75" fill="#7986cb" fontSize="8" textAnchor="middle">ATS</text>
            <text x="420" y="87" fill="#4caf50" fontSize="7" textAnchor="middle">SRC-A ●</text>

            {/* UPS */}
            <Pipe x1={450} y1={77} x2={490} y2={77} type="facility" flowing={true} />
            <UPS x={530} y={77} mode="online" batteryPct={100} label="UPS-01" />

            {/* Rectifier to 800VDC */}
            <Pipe x1={565} y1={77} x2={610} y2={77} type="facility" flowing={true} />
            <rect x="610" y="60" width="50" height="35" fill="#1a1a1a" stroke="#ff9800" strokeWidth="1.5" rx="4" />
            <text x="635" y="75" fill="#ff9800" fontSize="7" textAnchor="middle">RECT</text>
            <text x="635" y="87" fill="#ff9800" fontSize="8" textAnchor="middle" fontWeight="bold">AC→DC</text>

            {/* ─── 800VDC BUS ─── */}
            <line x1="660" y1="77" x2="880" y2="77" stroke="#ff9800" strokeWidth="5" />
            <line x1="660" y1="77" x2="880" y2="77" stroke="#ffb74d" strokeWidth="2" opacity="0.4" />
            <text x="770" y="68" fill="#ff9800" fontSize="9" textAnchor="middle" fontWeight="bold">800 VDC BUS</text>
            <Sensor x={770} y={100} type="PT" value={800} unit="V" tag="VT-001" />

            {/* ─── PDU Feeder Breakers ─── */}
            {[0,1,2,3].map(i => (
              <g key={i}>
                <line x1={700+i*50} y1={77} x2={700+i*50} y2={140} stroke="#ff9800" strokeWidth="2" />
                <Breaker x={700+i*50} y={155} closed={true} label={`CB-${i+1}`} rating="400A" />
                
                {/* PDU */}
                <line x1={700+i*50} y1={170} x2={700+i*50} y2={200} stroke="#ff9800" strokeWidth="2" />
                <rect x={700+i*50-20} y={200} width="40" height="50" fill="#1a1a1a" stroke="#546e7a" strokeWidth="1.5" rx="3" />
                <text x={700+i*50} y={218} fill="#90a4ae" fontSize="7" textAnchor="middle">PDU-{String(i+1).padStart(2,'0')}</text>
                <text x={700+i*50} y={232} fill="#fff" fontSize="9" textAnchor="middle" fontFamily="monospace">{(itPower/4).toFixed(0)}</text>
                <text x={700+i*50} y={242} fill="#888" fontSize="7" textAnchor="middle">kW</text>

                {/* Load bar */}
                <rect x={700+i*50-15} y={250} width="30" height="4" fill="#333" rx="2" />
                <rect x={700+i*50-15} y={250} width={itPower > 0 ? 22 : 0} height="4" fill="#4caf50" rx="2" />
              </g>
            ))}

            {/* ─── GENERATOR (Standby) ─── */}
            <Generator x={100} y={180} running={false} mode="standby" power_kw={0} label="GEN-01" />
            {/* Dashed connection to ATS */}
            <line x1="152" y1="180" x2="390" y2="77" stroke="#795548" strokeWidth="1" strokeDasharray="4 4" />

            {/* ─── ENERGY METER ─── */}
            <Sensor x={450} y={140} type="PT" value={totalPower} unit="kW" tag="EM-001" />

            {/* ─── Phase Voltages ─── */}
            <g transform="translate(40,280)">
              <rect x="0" y="0" width="200" height="60" fill="#0a0a0f" stroke="#333" rx="4" />
              <text x="100" y="15" fill="#888" fontSize="8" textAnchor="middle">PHASE VOLTAGES</text>
              {['L1','L2','L3'].map((ph,i) => (
                <g key={ph}>
                  <text x={20+i*70} y="35" fill="#666" fontSize="8" textAnchor="middle">{ph}</text>
                  <text x={20+i*70} y="50" fill="#4caf50" fontSize="11" textAnchor="middle" fontFamily="monospace">{479+Math.round(Math.random()*2)}V</text>
                </g>
              ))}
            </g>

            {/* ─── PUE Gauge ─── */}
            <g transform="translate(300,280)">
              <rect x="0" y="0" width="100" height="60" fill="#0a0a0f" stroke="#333" rx="4" />
              <text x="50" y="15" fill="#888" fontSize="8" textAnchor="middle">PUE</text>
              <text x="50" y="45" fill="#76b900" fontSize="22" textAnchor="middle" fontFamily="monospace" fontWeight="bold">1.08</text>
            </g>
          </svg>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Energy Today" value={(totalPower * 12 / 1000)} unit="MWh" />
        <MetricCard label="UPS Runtime" value={15} unit="min" />
        <MetricCard label="Generator" value="Standby" status="ok" />
      </div>
    </div>
  );
}
