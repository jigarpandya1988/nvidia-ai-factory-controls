import React from 'react';

interface Props {
  x: number;
  y: number;
  running: boolean;
  power?: number;      // kW
  fault?: boolean;
  label?: string;
  onClick?: () => void;
}

/**
 * ISA Motor Symbol — Circle with M inside
 * Green border = running, Red = fault, Gray = stopped
 */
export function Motor({ x, y, running, power = 0, fault = false, label, onClick }: Props) {
  const color = fault ? '#f44336' : running ? '#4caf50' : '#666';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Motor circle */}
      <circle cx="0" cy="0" r="14" fill="#1a1a1a" stroke={color} strokeWidth="2.5" />
      {/* M label */}
      <text x="0" y="5" fill={color} fontSize="12" textAnchor="middle" fontWeight="bold">M</text>
      {/* Rotation indicator */}
      {running && (
        <circle cx="0" cy="0" r="17" fill="none" stroke={color} strokeWidth="1" strokeDasharray="3 8" opacity="0.5">
          <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      {/* Power text */}
      <text x="0" y="24" fill="#888" fontSize="8" textAnchor="middle">{power.toFixed(0)} kW</text>
      {label && <text x="0" y="-20" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
    </g>
  );
}
