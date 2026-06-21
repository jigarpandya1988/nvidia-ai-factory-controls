import React from 'react';

interface Props {
  x: number;
  y: number;
  label?: string;
  primaryV?: string;
  secondaryV?: string;
  onClick?: () => void;
}

/**
 * ISA Transformer Symbol — Two coupled coils (circles with connection)
 */
export function Transformer({ x, y, label, primaryV = '13.8kV', secondaryV = '480V', onClick }: Props) {
  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Primary coil */}
      <circle cx="-8" cy="0" r="14" fill="none" stroke="#ffc107" strokeWidth="2" />
      {/* Secondary coil */}
      <circle cx="8" cy="0" r="14" fill="none" stroke="#ffc107" strokeWidth="2" />
      
      {/* Voltage labels */}
      <text x="-8" y="4" fill="#ffc107" fontSize="7" textAnchor="middle">{primaryV}</text>
      <text x="8" y="4" fill="#ffc107" fontSize="7" textAnchor="middle">{secondaryV}</text>
      
      {/* Label */}
      {label && <text x="0" y="-20" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
    </g>
  );
}
