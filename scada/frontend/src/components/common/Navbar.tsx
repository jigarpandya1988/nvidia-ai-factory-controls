import React from 'react';
import { NavLink } from 'react-router-dom';
import { useProcessStore } from '../../stores/useProcessStore';
import { useAuthStore } from '../../stores/useAuthStore';

const links = [
  { to: '/', label: 'Overview' },
  { to: '/cooling', label: 'Cooling' },
  { to: '/power', label: 'Power' },
  { to: '/safety', label: 'Safety' },
  { to: '/environment', label: 'Environment' },
  { to: '/alarms', label: 'Alarms' },
  { to: '/trends', label: 'Trends' },
];

export function Navbar() {
  const connected = useProcessStore(s => s.connected);
  const user = useAuthStore(s => s.user);
  const logout = useAuthStore(s => s.logout);

  return (
    <nav className="bg-surface-2 border-b border-surface-4 px-4 py-2 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-nvidia rounded-sm" />
          <span className="font-bold text-sm text-nvidia">AI FACTORY SCADA</span>
        </div>
        <div className="flex gap-1">
          {links.map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `px-3 py-1.5 text-xs rounded transition-colors ${
                  isActive ? 'bg-nvidia/20 text-nvidia' : 'text-gray-400 hover:text-white hover:bg-surface-3'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs">
        <div className={`flex items-center gap-1.5 ${connected ? 'text-green-400' : 'text-red-400'}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
          {connected ? 'LIVE' : 'DISCONNECTED'}
        </div>
        <span className="text-gray-600">|</span>
        <span className="text-gray-500">Site: US-WEST-01</span>
        {user && (
          <>
            <span className="text-gray-600">|</span>
            <span className="text-gray-300">{user.displayName}</span>
            <span className="text-gray-500 bg-surface-3 px-1.5 py-0.5 rounded">
              {user.role}
            </span>
            <button
              onClick={logout}
              className="text-gray-500 hover:text-red-400 transition-colors"
              title="Sign out"
            >
              ✕
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
