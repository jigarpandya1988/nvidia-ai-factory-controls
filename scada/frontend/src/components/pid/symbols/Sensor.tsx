import React from 'react';

interface Props {
  x: number;
  y: number;
  type: 'TT' | 'PT' | 'FT' | 'LT';  // Temp, Pressure, Flow, Level transmitter
  value: number;
  unit: string;
  tag?: string;
  valid?: boolean;
  onClick?: () => void;
}

/**
 * ISA Instrument Symbol — Circle with function letters
 * TT = Temperature Transmitter, PT = Pressure, FT = Flow, LT = Level
 */
export function Sensor({ x, y, type, value, unit, tag, valid = true, onClick }: Props) {
  const borderColor = !valid ? '#f44336' : '#90a4ae';
  const valueColor = !valid ? '#f44336' : '#fff';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Instrument bubble */}
      <circle cx="0" cy="0" r="14" fill="#0d1117" stroke={borderColor} strokeWidth="1.5" />
      {/* Horizontal line (field-mounted indicator) */}
      <line x1="-14" y1="0" x2="-20" y2="0" stroke={borderColor} strokeWidth="1" />
      
      {/* Function letters */}
      <text x="0" y="-2" fill={borderColor} fontSize="8" textAnchor="middle">{type}</text>
      
      {/* Value display below */}
      <rect x="-22" y="16" width="44" height="14" fill="#0a0a0f" stroke="#333" rx="2" />
      <text x="0" y="26" fill={valueColor} fontSize="9" textAnchor="middle" fontFamily="monospace">
        {value.toFixed(1)}{unit}
      </text>
      
      {/* Tag name */}
      {tag && <text x="0" y="40" fill="#666" fontSize="7" textAnchor="middle">{tag}</text>}
      
      {/* Invalid indicator */}
      {!valid && (
        <g>
          <line x1="-10" y1="-10" x2="10" y2="10" stroke="#f44336" strokeWidth="1.5" />
          <text x="18" y="-8" fill="#f44336" fontSize="7">BAD</text>
        </g>
      )}
    </g>
  );
}
