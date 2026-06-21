import React from 'react';

interface Props {
  x: number;
  y: number;
  zone: number;
  active: boolean;
  onClick?: () => void;
}

/**
 * Leak Detection Sensor — Wavy line symbol (sensing cable)
 */
export function LeakSensor({ x, y, zone, active, onClick }: Props) {
  const color = active ? '#f44336' : '#4caf50';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Sensing cable (wavy line) */}
      <path d="M-12,0 C-8,-4 -4,4 0,0 C4,-4 8,4 12,0" fill="none" stroke={color} strokeWidth="2" />
      
      {/* Zone number */}
      <circle cx="0" cy="12" r="7" fill="#0a0a0f" stroke={color} strokeWidth="1.5" />
      <text x="0" y="15" fill={color} fontSize="7" textAnchor="middle">{zone}</text>
      
      {/* Leak droplet animation */}
      {active && (
        <g>
          <path d="M0,-8 C2,-12 -2,-12 0,-8 L2,-4 C2,-2 -2,-2 -2,-4 Z" fill="#2196f3" opacity="0.8">
            <animate attributeName="opacity" values="0.8;0.2;0.8" dur="0.5s" repeatCount="indefinite" />
          </path>
        </g>
      )}
    </g>
  );
}
