import React from 'react';

interface Props {
  x: number;
  y: number;
  running: boolean;
  mode?: 'standby' | 'running' | 'testing' | 'fault';
  power_kw?: number;
  label?: string;
  onClick?: () => void;
}

/**
 * ISA Generator Symbol — Circle with G, coupled to engine block
 * Standard IEEE/ISA symbol for diesel/gas generator set
 */
export function Generator({ x, y, running, mode = 'standby', power_kw = 0, label, onClick }: Props) {
  const modeColors = { standby: '#666', running: '#4caf50', testing: '#ffc107', fault: '#f44336' };
  const color = modeColors[mode];

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Engine block (rectangle with fins) */}
      <rect x="-35" y="-16" width="28" height="32" fill="#1a1a1a" stroke="#795548" strokeWidth="2" rx="3" />
      {/* Engine fins */}
      <line x1="-33" y1="-8" x2="-27" y2="-8" stroke="#5d4037" strokeWidth="1.5" />
      <line x1="-33" y1="-2" x2="-27" y2="-2" stroke="#5d4037" strokeWidth="1.5" />
      <line x1="-33" y1="4" x2="-27" y2="4" stroke="#5d4037" strokeWidth="1.5" />
      <line x1="-33" y1="10" x2="-27" y2="10" stroke="#5d4037" strokeWidth="1.5" />
      {/* Exhaust stack */}
      <rect x="-32" y="-24" width="5" height="10" fill="#333" stroke="#555" strokeWidth="1" />
      {running && (
        <g opacity="0.6">
          <circle cx="-30" cy="-28" r="3" fill="#888" opacity="0.4">
            <animate attributeName="cy" values="-28;-40;-28" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" />
          </circle>
        </g>
      )}

      {/* Coupling shaft */}
      <line x1="-7" y1="0" x2="5" y2="0" stroke={color} strokeWidth="3" />

      {/* Generator circle (ISA standard) */}
      <circle cx="22" cy="0" r="18" fill="#0d1117" stroke={color} strokeWidth="2.5" />
      
      {/* G letter inside */}
      <text x="22" y="5" fill={color} fontSize="14" textAnchor="middle" fontWeight="bold">G</text>

      {/* Rotation indicator when running */}
      {running && (
        <circle cx="22" cy="0" r="21" fill="none" stroke={color} strokeWidth="1" strokeDasharray="4 6" opacity="0.5">
          <animateTransform attributeName="transform" type="rotate" from="0 22 0" to="360 22 0" dur="1.5s" repeatCount="indefinite" />
        </circle>
      )}

      {/* Output terminal */}
      <line x1="40" y1="0" x2="50" y2="0" stroke={color} strokeWidth="2" />
      <circle cx="52" cy="0" r="3" fill={color} />

      {/* Mode/Status text */}
      <rect x="-10" y="22" width="64" height="14" fill="#0a0a0f" stroke={color} strokeWidth="1" rx="2" />
      <text x="22" y="32" fill={color} fontSize="8" textAnchor="middle" fontWeight="bold">
        {mode.toUpperCase()}
      </text>

      {/* Power output (when running) */}
      {running && power_kw > 0 && (
        <text x="22" y="48" fill="#fff" fontSize="9" textAnchor="middle" fontFamily="monospace">{power_kw} kW</text>
      )}

      {/* Label */}
      {label && <text x="22" y="-26" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
    </g>
  );
}
