import React from 'react';
import { useProcessStore } from '../stores/useProcessStore';
import { MetricCard } from '../components/common/MetricCard';
import { Sensor } from '../components/pid/symbols';

export function Environment() {
  const data = useProcessStore(s => s.current);
  const hallTemp = data ? 22 + data.gpu_max_temp * 0.05 : 22;
  const humidity = 45;
  const dewPoint = 12.3;
  const condensationMargin = hallTemp - dewPoint;

  const zones = [
    { name: 'Hall A - Row 1', temp: hallTemp - 1, hum: 44 },
    { name: 'Hall A - Row 2', temp: hallTemp + 0.5, hum: 46 },
    { name: 'Hall B - Row 1', temp: hallTemp + 1, hum: 43 },
    { name: 'Hall B - Row 2', temp: hallTemp - 0.5, hum: 47 },
  ];

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Environmental Monitoring — IPC-03</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard label="Avg Temperature" value={hallTemp} unit="°C" status={hallTemp > 27 ? 'warn' : 'ok'} />
        <MetricCard label="Avg Humidity" value={humidity} unit="%RH" status="ok" />
        <MetricCard label="Dew Point" value={dewPoint} unit="°C" />
        <MetricCard label="Condensation Margin" value={condensationMargin} unit="°C" status={condensationMargin < 5 ? 'warn' : 'ok'} />
        <MetricCard label="Particle Class" value="ISO 8" status="ok" />
        <MetricCard label="Air Pressure" value={1013} unit="hPa" />
      </div>

      {/* Zone P&ID with ISA sensors */}
      <div className="bg-surface-2 rounded-lg p-4 border border-surface-4">
        <h3 className="text-xs text-nvidia uppercase tracking-wider mb-3">Data Hall Sensor Layout</h3>
        <div className="bg-surface-1 rounded border border-surface-4">
          <svg viewBox="0 0 800 360" className="w-full" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="egrid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#111118" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="800" height="360" fill="url(#egrid)" />

            {/* Hall outline */}
            <rect x="40" y="30" width="720" height="300" fill="none" stroke="#333" strokeWidth="1.5" rx="6" />
            <text x="400" y="22" fill="#555" fontSize="9" textAnchor="middle">DATA HALL — FLOOR PLAN</text>

            {/* Zone boundaries */}
            <rect x="50" y="40" width="340" height="130" fill="#4caf50" fillOpacity="0.03" stroke="#4caf50" strokeWidth="1" strokeDasharray="4" rx="4" />
            <text x="220" y="55" fill="#4caf50" fontSize="9" textAnchor="middle">HALL A</text>
            <rect x="410" y="40" width="340" height="130" fill="#2196f3" fillOpacity="0.03" stroke="#2196f3" strokeWidth="1" strokeDasharray="4" rx="4" />
            <text x="580" y="55" fill="#2196f3" fontSize="9" textAnchor="middle">HALL B</text>

            {/* GPU Racks (small rectangles) */}
            {[0,1,2,3,4,5,6,7].map(i => (
              <g key={`rackA-${i}`}>
                <rect x={70+i*38} y={70} width="25" height="40" fill="#222" stroke="#444" strokeWidth="1" rx="2" />
                <rect x={70+i*38} y={120} width="25" height="40" fill="#222" stroke="#444" strokeWidth="1" rx="2" />
              </g>
            ))}
            {[0,1,2,3,4,5,6,7].map(i => (
              <g key={`rackB-${i}`}>
                <rect x={430+i*38} y={70} width="25" height="40" fill="#222" stroke="#444" strokeWidth="1" rx="2" />
                <rect x={430+i*38} y={120} width="25" height="40" fill="#222" stroke="#444" strokeWidth="1" rx="2" />
              </g>
            ))}

            {/* Temperature Sensors (ISA TT symbols) */}
            <Sensor x={130} y={100} type="TT" value={zones[0].temp} unit="°C" tag="TT-301" valid={true} />
            <Sensor x={300} y={100} type="TT" value={zones[1].temp} unit="°C" tag="TT-302" valid={true} />
            <Sensor x={500} y={100} type="TT" value={zones[2].temp} unit="°C" tag="TT-303" valid={true} />
            <Sensor x={670} y={100} type="TT" value={zones[3].temp} unit="°C" tag="TT-304" valid={true} />

            {/* Humidity Sensors (using PT symbol adapted) */}
            <Sensor x={130} y={150} type="LT" value={zones[0].hum} unit="%" tag="HT-301" valid={true} />
            <Sensor x={300} y={150} type="LT" value={zones[1].hum} unit="%" tag="HT-302" valid={true} />
            <Sensor x={500} y={150} type="LT" value={zones[2].hum} unit="%" tag="HT-303" valid={true} />
            <Sensor x={670} y={150} type="LT" value={zones[3].hum} unit="%" tag="HT-304" valid={true} />

            {/* Dew Point Calculation Box */}
            <rect x="250" y="200" width="300" height="50" fill="#0a0a0f" stroke="#00bcd4" strokeWidth="1.5" rx="4" />
            <text x="400" y="218" fill="#00bcd4" fontSize="9" textAnchor="middle">DEW POINT CALCULATION (Magnus-Tetens)</text>
            <text x="300" y="238" fill="#fff" fontSize="10" textAnchor="middle" fontFamily="monospace">Td = {dewPoint.toFixed(1)}°C</text>
            <text x="500" y="238" fill="#4caf50" fontSize="10" textAnchor="middle" fontFamily="monospace">Margin = {condensationMargin.toFixed(1)}°C</text>

            {/* ASHRAE Limits Box */}
            <rect x="50" y="270" width="700" height="50" fill="#0a0a0f" stroke="#333" rx="4" />
            <text x="400" y="288" fill="#76b900" fontSize="9" textAnchor="middle">ASHRAE TC 9.9 RECOMMENDED ENVELOPE</text>
            <text x="200" y="308" fill="#888" fontSize="8" textAnchor="middle">Temperature: 18-27°C</text>
            <text x="400" y="308" fill="#888" fontSize="8" textAnchor="middle">Humidity: 20-80% RH</text>
            <text x="600" y="308" fill="#888" fontSize="8" textAnchor="middle">Dew Point: ≤15°C</text>
            
            {/* Status indicators */}
            <circle cx="120" cy="305" r="4" fill={hallTemp <= 27 ? '#4caf50' : '#ff9800'} />
            <circle cx="320" cy="305" r="4" fill={humidity <= 80 && humidity >= 20 ? '#4caf50' : '#ff9800'} />
            <circle cx="520" cy="305" r="4" fill={dewPoint <= 15 ? '#4caf50' : '#ff9800'} />
          </svg>
        </div>
      </div>

      {/* Zone Detail Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {zones.map((zone, i) => {
          const tempNorm = Math.max(0, Math.min(1, (zone.temp - 18) / (32 - 18)));
          const state = zone.temp > 27 ? 'warn' : 'ok';
          return (
            <div key={i} className={`bg-surface-2 rounded-lg p-3 border ${state === 'warn' ? 'border-yellow-500/50' : 'border-surface-4'}`}>
              <div className="text-[10px] text-gray-500 uppercase">{zone.name}</div>
              <div className="flex items-end justify-between mt-2">
                <div>
                  <div className="text-xl font-mono font-bold">{zone.temp.toFixed(1)}°C</div>
                  <div className="text-xs text-gray-500">{zone.hum}% RH</div>
                </div>
                <div className="w-3 h-12 bg-surface-1 rounded-full overflow-hidden border border-surface-4">
                  <div className="w-full rounded-full transition-all" style={{ 
                    height: `${tempNorm * 100}%`, marginTop: `${(1-tempNorm)*100}%`,
                    background: `linear-gradient(to top, #4caf50, ${tempNorm > 0.7 ? '#f44336' : '#ffc107'})` 
                  }} />
                </div>
              </div>
              <div className={`text-[10px] mt-1 ${state === 'ok' ? 'text-green-400' : 'text-yellow-400'}`}>
                ● {state === 'ok' ? 'Normal' : 'Warning'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
