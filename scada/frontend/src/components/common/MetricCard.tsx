import React from 'react';

interface Props {
  label: string;
  value: string | number;
  unit?: string;
  status?: 'ok' | 'warn' | 'critical';
}

const statusColors = {
  ok: 'text-green-400',
  warn: 'text-yellow-400',
  critical: 'text-red-400',
};

export function MetricCard({ label, value, unit = '', status = 'ok' }: Props) {
  return (
    <div className="bg-surface-3 rounded-lg p-3 border border-surface-4">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-xl font-mono font-bold ${statusColors[status]}`}>
        {typeof value === 'number' ? value.toFixed(1) : value}
        <span className="text-sm text-gray-500 ml-1">{unit}</span>
      </div>
    </div>
  );
}
