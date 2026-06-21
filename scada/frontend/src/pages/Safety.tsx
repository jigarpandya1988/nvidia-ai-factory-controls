import React from 'react';
import { useProcessStore } from '../stores/useProcessStore';
import { MetricCard } from '../components/common/MetricCard';
import { EPOButton, FireDetector, LeakSensor, Valve, Pipe } from '../components/pid/symbols';

export function Safety() {
  const data = useProcessStore(s => s.current);

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Safety Systems — IPC-04 (SIL 2)</h1>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <MetricCard label="Safety Permit" value="GRANTED" status="ok" />
        <MetricCard label="EPO Status" value="ARMED" status="ok" />
        <MetricCard label="Fire Status" value="NORMAL" status="ok" />
        <MetricCard label="Leak Zones" value="0 / 16" status="ok" />
        <MetricCard label="Response Time" value="<100" unit="ms" status="ok" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* EPO Zone Diagram */}
        <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
          <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">EPO Zone Layout</h3>
          <div className="bg-surface-1 rounded border border-surface-4">
            <svg viewBox="0 0 500 320" className="w-full" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="sgrid" width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#111118" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="500" height="320" fill="url(#sgrid)" />

              {/* Facility outline */}
              <rect x="30" y="30" width="440" height="260" fill="none" stroke="#333" strokeWidth="1" strokeDasharray="4" rx="8" />
              <text x="250" y="22" fill="#555" fontSize="9" textAnchor="middle">AI FACTORY — FACILITY PLAN</text>

              {/* EPO Buttons (8 zones in 2 rows) */}
              {[0,1,2,3].map(i => (
                <EPOButton key={`top-${i}`} x={80+i*100} y={80} zone={i+1} tripped={false} label={['Row A','Row B','Row C','Row D'][i]} />
              ))}
              {[0,1,2,3].map(i => (
                <EPOButton key={`bot-${i}`} x={80+i*100} y={180} zone={i+5} tripped={false} label={['Cool A','Cool B','Elec','MASTER'][i]} />
              ))}

              {/* Zone boundaries */}
              <rect x="40" y="50" width="200" height="60" fill="none" stroke="#4caf50" strokeWidth="1" strokeDasharray="3" rx="4" opacity="0.4" />
              <rect x="260" y="50" width="200" height="60" fill="none" stroke="#4caf50" strokeWidth="1" strokeDasharray="3" rx="4" opacity="0.4" />
              <rect x="40" y="140" width="200" height="60" fill="none" stroke="#2196f3" strokeWidth="1" strokeDasharray="3" rx="4" opacity="0.4" />
              <rect x="260" y="140" width="200" height="60" fill="none" stroke="#ff9800" strokeWidth="1" strokeDasharray="3" rx="4" opacity="0.4" />

              {/* Hardwired connections to power contactors */}
              <text x="250" y="240" fill="#888" fontSize="8" textAnchor="middle">HARDWIRED TO POWER CONTACTORS</text>
              {[0,1,2,3,4,5,6,7].map(i => (
                <line key={`hw-${i}`} x1={80+i*50} y1={250} x2={80+i*50} y2={270} stroke="#f44336" strokeWidth="1" strokeDasharray="2" opacity="0.5" />
              ))}
              <line x1="80" y1="270" x2="430" y2="270" stroke="#f44336" strokeWidth="2" />
              <text x="250" y="285" fill="#f44336" fontSize="7" textAnchor="middle">SAFETY RELAY BUS (FAIL-SAFE: DE-ENERGIZED = TRIP)</text>

              {/* Dual channel indicator */}
              <rect x="350" y="240" width="80" height="35" fill="#0a0a0f" stroke="#333" rx="3" />
              <text x="390" y="255" fill="#4caf50" fontSize="7" textAnchor="middle">DUAL CHANNEL</text>
              <text x="390" y="268" fill="#4caf50" fontSize="8" textAnchor="middle">CH-A ● CH-B ●</text>
            </svg>
          </div>
        </div>

        {/* Fire + Leak Detection */}
        <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
          <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Fire & Leak Detection</h3>
          <div className="bg-surface-1 rounded border border-surface-4">
            <svg viewBox="0 0 500 320" className="w-full" xmlns="http://www.w3.org/2000/svg">
              <rect width="500" height="320" fill="url(#sgrid)" />

              {/* Fire detection section */}
              <text x="20" y="20" fill="#f44336" fontSize="9" fontWeight="bold">FIRE DETECTION</text>
              
              {/* VESDA zones */}
              <FireDetector x={80} y={60} type="vesda" state="normal" label="VESDA-1" />
              <FireDetector x={180} y={60} type="vesda" state="normal" label="VESDA-2" />
              <FireDetector x={280} y={60} type="vesda" state="normal" label="VESDA-3" />
              <FireDetector x={380} y={60} type="vesda" state="normal" label="VESDA-4" />

              {/* Spot detectors */}
              {[0,1,2,3,4,5,6,7].map(i => (
                <FireDetector key={i} x={60+i*55} y={120} type="spot" state="normal" label={`SD-${i+1}`} />
              ))}

              {/* Suppression system */}
              <rect x="150" y="150" width="200" height="40" fill="#1a1a1a" stroke="#9c27b0" strokeWidth="1.5" rx="4" />
              <text x="250" y="168" fill="#ce93d8" fontSize="9" textAnchor="middle">SUPPRESSION: Novec 1230</text>
              <text x="250" y="182" fill="#4caf50" fontSize="8" textAnchor="middle">● READY | Countdown: 30s</text>

              {/* Isolation valves */}
              <Valve x={120} y={175} position={0} type="globe" label="SV-01" />
              <Valve x={380} y={175} position={0} type="globe" label="SV-02" />

              {/* Leak detection section */}
              <text x="20" y="220" fill="#2196f3" fontSize="9" fontWeight="bold">LEAK DETECTION</text>
              
              {/* 16 leak zones in 2 rows */}
              {[0,1,2,3,4,5,6,7].map(i => (
                <LeakSensor key={`l1-${i}`} x={50+i*55} y={250} zone={i+1} active={Boolean(data?.leak && i === 0)} />
              ))}
              {[0,1,2,3,4,5,6,7].map(i => (
                <LeakSensor key={`l2-${i}`} x={50+i*55} y={295} zone={i+9} active={false} />
              ))}
            </svg>
          </div>
        </div>
      </div>

      {/* Safety Chain Status */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Safety Chain — Pessimistic Logic</h3>
        <div className="bg-surface-1 rounded p-3 border border-surface-4 text-xs font-mono text-center">
          <span className="text-green-400">EPO_OK</span>
          <span className="text-gray-600"> AND </span>
          <span className="text-green-400">FIRE_OK</span>
          <span className="text-gray-600"> AND </span>
          <span className="text-green-400">LEAK_OK</span>
          <span className="text-gray-600"> AND </span>
          <span className="text-green-400">SEISMIC_OK</span>
          <span className="text-gray-600"> → </span>
          <span className="text-nvidia font-bold">SAFETY_PERMIT = TRUE</span>
        </div>
        <div className="mt-2 text-[10px] text-gray-500 text-center">
          ANY condition FALSE → permit revoked → ALL subsystems enter safe-state
        </div>
      </div>
    </div>
  );
}
