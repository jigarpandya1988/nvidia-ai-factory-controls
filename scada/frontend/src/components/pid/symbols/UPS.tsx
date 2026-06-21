import React from 'react';

interface Props {
  x: number;
  y: number;
  mode: 'online' | 'battery' | 'bypass' | 'fault';
  batteryPct?: number;
  label?: string;
  onClick?: () => void;
}

/**
 * UPS Symbol — Rectangle with battery + inverter indication
 */
export function UPS({ x, y, mode, batteryPct = 100, label, onClick }: Props) {
  const modeColor = mode === 'online' ? '#4caf50' : mode === 'battery' ? '#ff9800' : mode === 'fault' ? '#f44336' : '#9e9e9e';
  const modeText = mode === 'online' ? 'ONLINE' : mode === 'battery' ? 'BATTERY' : mode === 'fault' ? 'FAULT' : 'BYPASS';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* UPS body */}
      <rect x="-30" y="-20" width="60" height="40" fill="#1a1a2a" stroke={modeColor} strokeWidth="2" rx="4" />
      
      {/* AC sine wave (input) */}
      <path d="M-25,-5 C-22,-12 -18,2 -15,-5" fill="none" stroke={modeColor} strokeWidth="1.5" />
      
      {/* Battery icon */}
      <rect x="-5" y="-8" width="16" height="10" fill="none" stroke={modeColor} strokeWidth="1.5" rx="1" />
      <rect x="11" y="-5" width="2" height="4" fill={modeColor} />
      {/* Battery fill */}
      <rect x="-3" y="-6" width={12 * batteryPct / 100} height="6" fill={modeColor} opacity="0.5" />
      
      {/* DC output indicator */}
      <text x="20" y="-2" fill={modeColor} fontSize="7">DC</text>
      <line x1="17" y1="2" x2="25" y2="2" stroke={modeColor} strokeWidth="1" />
      <line x1="17" y1="4" x2="25" y2="4" stroke={modeColor} strokeWidth="1" strokeDasharray="2" />
      
      {/* Mode text */}
      <text x="0" y="12" fill={modeColor} fontSize="7" textAnchor="middle" fontWeight="bold">{modeText}</text>
      
      {/* Battery percentage */}
      <text x="0" y="32" fill="#888" fontSize="8" textAnchor="middle">{batteryPct}%</text>
      
      {/* Label */}
      {label && <text x="0" y="-26" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
      
      {/* Pulsing on battery */}
      {mode === 'battery' && (
        <rect x="-32" y="-22" width="64" height="44" fill="none" stroke="#ff9800" strokeWidth="1" rx="5" opacity="0.5">
          <animate attributeName="opacity" values="0.5;0.1;0.5" dur="1.5s" repeatCount="indefinite" />
        </rect>
      )}
    </g>
  );
}
