import React from 'react';

interface Props {
  x1: number; y1: number;
  x2: number; y2: number;
  type?: 'supply' | 'return' | 'drain' | 'facility';
  flowing?: boolean;
  flowDirection?: 'forward' | 'reverse';
  onClick?: () => void;
}

const pipeColors = {
  supply: '#1565c0',
  return: '#c62828',
  drain: '#666',
  facility: '#2e7d32',
};

/**
 * Animated Pipe — shows flow direction with dashed animation
 */
export function Pipe({ x1, y1, x2, y2, type = 'supply', flowing = true, flowDirection = 'forward', onClick }: Props) {
  const color = pipeColors[type];
  const id = `pipe-${x1}-${y1}-${x2}-${y2}`;

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick}>
      {/* Pipe body */}
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="5" strokeLinecap="round" />
      {/* Inner line (highlight) */}
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="2" opacity="0.6" strokeLinecap="round" />
      
      {/* Flow animation (dashed overlay) */}
      {flowing && (
        <line x1={x1} y1={y1} x2={x2} y2={y2} 
          stroke="#fff" strokeWidth="2" opacity="0.15"
          strokeDasharray="6 12" strokeLinecap="round">
          <animate 
            attributeName="stroke-dashoffset" 
            from={flowDirection === 'forward' ? '0' : '18'} 
            to={flowDirection === 'forward' ? '18' : '0'} 
            dur="1s" 
            repeatCount="indefinite" 
          />
        </line>
      )}
      
      {/* Flow arrow at midpoint */}
      {flowing && (() => {
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        const dir = flowDirection === 'reverse' ? angle + 180 : angle;
        return (
          <polygon 
            points="-5,-3 5,0 -5,3" 
            fill={color} 
            transform={`translate(${mx},${my}) rotate(${dir})`}
            opacity="0.8"
          />
        );
      })()}
    </g>
  );
}
