import React from 'react';

interface Props {
  x: number;
  y: number;
  closed: boolean;
  label?: string;
  rating?: string;
  onClick?: () => void;
}

/**
 * ISA Circuit Breaker Symbol — Line with angle break
 * Closed = connected line, Open = angled line (disconnect)
 */
export function Breaker({ x, y, closed, label, rating, onClick }: Props) {
  const color = closed ? '#4caf50' : '#f44336';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Fixed contacts */}
      <circle cx="-12" cy="0" r="3" fill={color} />
      <circle cx="12" cy="0" r="3" fill={color} />
      
      {/* Moving contact */}
      {closed ? (
        <line x1="-12" y1="0" x2="12" y2="0" stroke={color} strokeWidth="2.5" />
      ) : (
        <line x1="-12" y1="0" x2="8" y2="-10" stroke={color} strokeWidth="2.5" />
      )}
      
      {/* Status indicator */}
      <rect x="-8" y="6" width="16" height="10" fill="#0a0a0f" stroke={color} strokeWidth="1" rx="2" />
      <text x="0" y="14" fill={color} fontSize="7" textAnchor="middle">{closed ? 'ON' : 'OFF'}</text>
      
      {/* Label */}
      {label && <text x="0" y="-12" fill="#999" fontSize="7" textAnchor="middle">{label}</text>}
      {rating && <text x="0" y="26" fill="#666" fontSize="6" textAnchor="middle">{rating}</text>}
    </g>
  );
}
