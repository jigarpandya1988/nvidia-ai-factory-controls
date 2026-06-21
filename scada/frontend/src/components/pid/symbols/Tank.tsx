import React from 'react';

interface Props {
  x: number;
  y: number;
  level?: number;       // 0-100% fill
  temperature?: number; // °C displayed
  label?: string;
  width?: number;
  height?: number;
  onClick?: () => void;
}

/**
 * Tank/Vessel Symbol — Rectangle with level indicator
 * Used for CDU heat exchanger body, buffer tanks
 */
export function Tank({ x, y, level = 50, temperature, label, width = 60, height = 80, onClick }: Props) {
  const fillHeight = (level / 100) * (height - 8);
  const tempColor = temperature && temperature > 45 ? '#f44336' : temperature && temperature > 35 ? '#ff9800' : '#2196f3';

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Tank body */}
      <rect x={-width/2} y={-height/2} width={width} height={height} 
        fill="#0a0a0f" stroke="#546e7a" strokeWidth="2" rx="4" />
      
      {/* Liquid level fill */}
      <rect x={-width/2 + 3} y={height/2 - fillHeight - 3} width={width - 6} height={fillHeight}
        fill={tempColor} opacity="0.3" rx="2" />
      
      {/* Level marks */}
      {[25,50,75].map(pct => (
        <line key={pct} x1={-width/2 + 2} y1={height/2 - (pct/100) * height}
          x2={-width/2 + 8} y2={height/2 - (pct/100) * height} stroke="#444" strokeWidth="1" />
      ))}
      
      {/* Temperature display */}
      {temperature !== undefined && (
        <text x="0" y="5" fill={tempColor} fontSize="11" textAnchor="middle" fontFamily="monospace" fontWeight="bold">
          {temperature.toFixed(1)}°C
        </text>
      )}
      
      {/* Label */}
      {label && (
        <text x="0" y={-height/2 - 8} fill="#76b900" fontSize="9" textAnchor="middle" fontWeight="bold">{label}</text>
      )}
    </g>
  );
}
