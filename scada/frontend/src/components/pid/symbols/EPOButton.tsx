import React from 'react';

interface Props {
  x: number;
  y: number;
  zone: number;
  tripped: boolean;
  label?: string;
  onClick?: () => void;
}

/**
 * EPO Pushbutton Symbol — Red mushroom-head button
 */
export function EPOButton({ x, y, zone, tripped, label, onClick }: Props) {
  const color = tripped ? '#f44336' : '#4caf50';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Button housing */}
      <rect x="-12" y="-8" width="24" height="16" fill="#1a1a1a" stroke="#666" strokeWidth="1.5" rx="3" />
      
      {/* Mushroom head */}
      <ellipse cx="0" cy="-8" rx="10" ry="6" fill={tripped ? '#d32f2f' : '#c62828'} stroke={color} strokeWidth="1.5" />
      
      {/* Zone number */}
      <text x="0" y="0" fill="#fff" fontSize="8" textAnchor="middle" fontWeight="bold">{zone}</text>
      
      {/* Status */}
      <text x="0" y="20" fill={color} fontSize="7" textAnchor="middle">
        {tripped ? 'TRIPPED' : 'ARMED'}
      </text>
      
      {/* Label */}
      {label && <text x="0" y="30" fill="#666" fontSize="6" textAnchor="middle">{label}</text>}
      
      {/* Tripped flash */}
      {tripped && (
        <ellipse cx="0" cy="-8" rx="13" ry="9" fill="none" stroke="#f44336" strokeWidth="1">
          <animate attributeName="opacity" values="1;0;1" dur="0.6s" repeatCount="indefinite" />
        </ellipse>
      )}
    </g>
  );
}
