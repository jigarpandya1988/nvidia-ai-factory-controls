import React from 'react';

interface Props {
  x: number;
  y: number;
  capacity_kw?: number;
  label?: string;
  onClick?: () => void;
}

/**
 * ISA Heat Exchanger Symbol — Circle with crossing lines
 * Standard P&ID symbol for shell-and-tube or plate heat exchangers
 */
export function HeatExchanger({ x, y, capacity_kw = 0, label, onClick }: Props) {
  const active = capacity_kw > 10;
  const color = active ? '#00bcd4' : '#555';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* HX circle body */}
      <circle cx="0" cy="0" r="22" fill="#0d1117" stroke={color} strokeWidth="2.5" />
      
      {/* Crossing flow lines (indicates counter-flow) */}
      <line x1="-15" y1="10" x2="15" y2="-10" stroke={color} strokeWidth="2" />
      <line x1="-15" y1="-10" x2="15" y2="10" stroke={color} strokeWidth="2" />
      
      {/* Capacity text */}
      <text x="0" y="35" fill={color} fontSize="9" textAnchor="middle" fontFamily="monospace">
        {capacity_kw.toFixed(0)} kW
      </text>
      
      {/* Label */}
      {label && <text x="0" y="-30" fill="#76b900" fontSize="9" textAnchor="middle" fontWeight="bold">{label}</text>}
      
      {/* Active glow */}
      {active && (
        <circle cx="0" cy="0" r="24" fill="none" stroke={color} strokeWidth="1" opacity="0.3">
          <animate attributeName="opacity" values="0.3;0.1;0.3" dur="3s" repeatCount="indefinite" />
        </circle>
      )}
    </g>
  );
}
