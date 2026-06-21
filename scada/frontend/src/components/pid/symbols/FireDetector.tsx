import React from 'react';

interface Props {
  x: number;
  y: number;
  type: 'vesda' | 'spot' | 'suppression';
  state: 'normal' | 'alert' | 'alarm' | 'discharged';
  label?: string;
  onClick?: () => void;
}

/**
 * Fire Detection Symbol — ISA diamond with type indicator
 */
export function FireDetector({ x, y, type, state, label, onClick }: Props) {
  const colors = { normal: '#4caf50', alert: '#ffc107', alarm: '#f44336', discharged: '#9c27b0' };
  const color = colors[state];

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Diamond shape */}
      <polygon points="0,-14 14,0 0,14 -14,0" fill="#0d1117" stroke={color} strokeWidth="2" />
      
      {/* Type indicator */}
      {type === 'vesda' && <text x="0" y="4" fill={color} fontSize="7" textAnchor="middle">VSD</text>}
      {type === 'spot' && <text x="0" y="4" fill={color} fontSize="7" textAnchor="middle">SD</text>}
      {type === 'suppression' && <text x="0" y="4" fill={color} fontSize="7" textAnchor="middle">FS</text>}
      
      {/* Status */}
      <text x="0" y="24" fill={color} fontSize="7" textAnchor="middle">{state.toUpperCase()}</text>
      
      {/* Label */}
      {label && <text x="0" y="-20" fill="#999" fontSize="7" textAnchor="middle">{label}</text>}
      
      {/* Alarm pulse */}
      {state === 'alarm' && (
        <polygon points="0,-18 18,0 0,18 -18,0" fill="none" stroke={color} strokeWidth="1" opacity="0.5">
          <animate attributeName="opacity" values="0.5;0;0.5" dur="0.8s" repeatCount="indefinite" />
        </polygon>
      )}
    </g>
  );
}
