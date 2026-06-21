import React from 'react';

interface Props {
  status: 'ok' | 'warn' | 'fault' | 'offline';
  label: string;
}

const colors = {
  ok: 'bg-green-500 shadow-green-500/50',
  warn: 'bg-yellow-500 shadow-yellow-500/50',
  fault: 'bg-red-500 shadow-red-500/50',
  offline: 'bg-gray-600',
};

export function StatusDot({ status, label }: Props) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <div className={`w-2 h-2 rounded-full shadow-sm ${colors[status]}`} />
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );
}
