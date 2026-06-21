import React from 'react';

interface Props {
  x: number;
  y: number;
  position: number;   // 0-100% open
  type?: 'globe' | 'butterfly' | '3way';
  label?: string;
  onClick?: () => void;
}

/**
 * ISA Valve Symbol — Two triangles pointing at each other (globe valve)
 * Position shown as fill level and numeric value
 * 3-way valve has three ports
 */
export function Valve({ x, y, position, type = 'globe', label, onClick }: Props) {
  const openColor = position > 5 ? '#ff9800' : '#666';
  const fillOpacity = position / 100;

  if (type === '3way') {
    return (
      <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
        {/* 3-way body */}
        <polygon points="-12,-10 0,0 -12,10" fill="none" stroke={openColor} strokeWidth="2" />
        <polygon points="12,-10 0,0 12,10" fill="none" stroke={openColor} strokeWidth="2" />
        <line x1="0" y1="0" x2="0" y2="14" stroke={openColor} strokeWidth="2" />
        {/* Fill indicator */}
        <rect x="-4" y="-4" width="8" height="8" fill={openColor} opacity={fillOpacity} rx="1" />
        {/* Actuator (motor on top) */}
        <rect x="-6" y="-22" width="12" height="10" fill="#333" stroke={openColor} strokeWidth="1" rx="2" />
        <line x1="0" y1="-12" x2="0" y2="-10" stroke={openColor} strokeWidth="1.5" />
        {/* Value */}
        <text x="0" y="28" fill={openColor} fontSize="9" textAnchor="middle" fontFamily="monospace">{position.toFixed(0)}%</text>
        {label && <text x="0" y="-28" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
      </g>
    );
  }

  return (
    <g className={onClick ? 'cursor-pointer' : ''} onClick={onClick} transform={`translate(${x},${y})`}>
      {/* Globe valve body — two triangles */}
      <polygon points="-14,-10 0,0 -14,10" fill={openColor} fillOpacity={fillOpacity} stroke={openColor} strokeWidth="2" />
      <polygon points="14,-10 0,0 14,10" fill={openColor} fillOpacity={fillOpacity} stroke={openColor} strokeWidth="2" />
      {/* Stem */}
      <line x1="0" y1="0" x2="0" y2="-14" stroke={openColor} strokeWidth="2" />
      {/* Handwheel / actuator */}
      <circle cx="0" cy="-18" r="5" fill="none" stroke={openColor} strokeWidth="1.5" />
      <line x1="-3" y1="-18" x2="3" y2="-18" stroke={openColor} strokeWidth="1" />
      {/* Value */}
      <text x="0" y="18" fill={openColor} fontSize="9" textAnchor="middle" fontFamily="monospace">{position.toFixed(0)}%</text>
      {label && <text x="0" y="-28" fill="#999" fontSize="8" textAnchor="middle">{label}</text>}
    </g>
  );
}
