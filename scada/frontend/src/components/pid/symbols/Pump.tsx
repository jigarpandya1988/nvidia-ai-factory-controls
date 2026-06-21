import React from 'react';

interface Props {
  x: number;
  y: number;
  running: boolean;
  speed?: number;      // 0-100%
  fault?: boolean;
  label?: string;
  onClick?: () => void;
}

/**
 * ISA Pump Symbol — Circle with triangle (flow direction indicator)
 * Colors: Green = running, Red = fault, Gray = stopped
 * Animated: rotating indicator when running
 */
export function Pump({ x, y, running, speed = 0, fault = false, label, onClick }: Props) {
  const color = fault ? '#f44336' : running ? '#4caf50' : '#666';
  const fillColor = fault ? '#f44336' : running ? '#1b5e20' : '#1a1a1a';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Pump body (circle) */}
      <circle cx="0" cy="0" r="18" fill={fillColor} stroke={color} strokeWidth="2.5" />
      
      {/* Flow triangle inside */}
      <polygon points="-8,-6 8,0 -8,6" fill={color} opacity="0.8">
        {running && (
          <animateTransform 
            attributeName="transform" type="rotate"
            from="0 0 0" to="360 0 0" 
            dur={`${Math.max(0.5, 3 - speed/50)}s`} 
            repeatCount="indefinite" 
          />
        )}
      </polygon>
      
      {/* Speed text */}
      <text x="0" y="30" fill={color} fontSize="9" textAnchor="middle" fontFamily="monospace">
        {speed.toFixed(0)}%
      </text>
      
      {/* Label */}
      {label && (
        <text x="0" y="-24" fill="#999" fontSize="8" textAnchor="middle">{label}</text>
      )}
      
      {/* Status indicator dot */}
      <circle cx="14" cy="-14" r="3" fill={color}>
        {running && <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite" />}
      </circle>
      
      {/* Fault X */}
      {fault && (
        <g stroke="#f44336" strokeWidth="2">
          <line x1="-6" y1="-6" x2="6" y2="6" />
          <line x1="6" y1="-6" x2="-6" y2="6" />
        </g>
      )}
    </g>
  );
}
