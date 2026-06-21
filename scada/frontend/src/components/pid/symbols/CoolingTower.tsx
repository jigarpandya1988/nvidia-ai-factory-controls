import React from 'react';

interface Props {
  x: number;
  y: number;
  fanRunning: boolean;
  waterTemp?: number;
  label?: string;
  onClick?: () => void;
}

/**
 * Cooling Tower Symbol — Trapezoid with fan on top
 */
export function CoolingTowerSymbol({ x, y, fanRunning, waterTemp, label, onClick }: Props) {
  const color = fanRunning ? '#4caf50' : '#666';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Tower body (trapezoid) */}
      <polygon points="-20,30 -14,-10 14,-10 20,30" fill="#1a1a1a" stroke="#546e7a" strokeWidth="2" />
      
      {/* Fill lines (packing) */}
      <line x1="-12" y1="5" x2="12" y2="5" stroke="#37474f" strokeWidth="1" />
      <line x1="-14" y1="15" x2="14" y2="15" stroke="#37474f" strokeWidth="1" />
      <line x1="-16" y1="25" x2="16" y2="25" stroke="#37474f" strokeWidth="1" />
      
      {/* Fan on top */}
      <circle cx="0" cy="-16" r="10" fill="#0a0a0f" stroke={color} strokeWidth="1.5" />
      {/* Fan blades */}
      <g>
        <line x1="-7" y1="-16" x2="7" y2="-16" stroke={color} strokeWidth="2" />
        <line x1="0" y1="-23" x2="0" y2="-9" stroke={color} strokeWidth="2" />
        {fanRunning && (
          <animateTransform attributeName="transform" type="rotate" from="0 0 -16" to="360 0 -16" dur="1s" repeatCount="indefinite" />
        )}
      </g>
      
      {/* Water temp */}
      {waterTemp !== undefined && (
        <text x="0" y="44" fill="#2196f3" fontSize="9" textAnchor="middle" fontFamily="monospace">{waterTemp.toFixed(0)}°C</text>
      )}
      
      {/* Label */}
      {label && <text x="0" y="-32" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
    </g>
  );
}
