import React, { useEffect, useState } from 'react';
import { AlarmRecord } from '../types';
import { useAuthStore } from '../stores/useAuthStore';

const severityColors = {
  critical: 'bg-red-500/20 border-red-500 text-red-300',
  high: 'bg-orange-500/20 border-orange-500 text-orange-300',
  medium: 'bg-yellow-500/20 border-yellow-500 text-yellow-300',
  low: 'bg-blue-500/20 border-blue-500 text-blue-300',
  info: 'bg-gray-500/20 border-gray-500 text-gray-300',
};

export function Alarms() {
  const [alarms, setAlarms] = useState<AlarmRecord[]>([]);
  const token = useAuthStore(s => s.token);

  useEffect(() => {
    if (!token) return;
    fetch(`http://${window.location.hostname}:4000/api/alarms`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(setAlarms)
      .catch(() => {});
  }, [token]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Alarm Management</h1>
        <div className="flex gap-2 text-xs">
          <span className="px-2 py-1 bg-red-500/20 rounded">Active: {alarms.filter(a => a.active).length}</span>
          <span className="px-2 py-1 bg-yellow-500/20 rounded">Unack: {alarms.filter(a => !a.acknowledged).length}</span>
        </div>
      </div>

      <div className="bg-surface-2 rounded-lg border border-surface-4 overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-surface-3">
            <tr>
              <th className="px-3 py-2 text-left text-gray-500">Severity</th>
              <th className="px-3 py-2 text-left text-gray-500">Source</th>
              <th className="px-3 py-2 text-left text-gray-500">Message</th>
              <th className="px-3 py-2 text-left text-gray-500">Time</th>
              <th className="px-3 py-2 text-left text-gray-500">Status</th>
              <th className="px-3 py-2 text-left text-gray-500">Action</th>
            </tr>
          </thead>
          <tbody>
            {alarms.map(alarm => (
              <tr key={alarm.id} className={`border-t border-surface-4 ${alarm.active ? '' : 'opacity-50'}`}>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase border ${severityColors[alarm.severity]}`}>
                    {alarm.severity}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono">{alarm.source}</td>
                <td className="px-3 py-2">{alarm.message}</td>
                <td className="px-3 py-2 text-gray-500">{new Date(alarm.timestamp).toLocaleTimeString()}</td>
                <td className="px-3 py-2">
                  {alarm.active ? <span className="text-red-400">● Active</span> : <span className="text-gray-500">○ Cleared</span>}
                </td>
                <td className="px-3 py-2">
                  {!alarm.acknowledged && (
                    <button className="px-2 py-0.5 bg-surface-4 rounded text-gray-300 hover:bg-nvidia/20 hover:text-nvidia">
                      ACK
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
